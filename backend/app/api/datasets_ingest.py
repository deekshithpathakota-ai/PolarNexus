"""Dataset ingestion API: analyse → (preview, validation, duplicates) → confirm with metadata → background registration."""
from __future__ import annotations

import secrets

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.security import can, require_permission
from app.core.config import settings
from app.core.database import get_db
from app.core.ratelimit import rate_limit
from app.ingestion import datasets as di
from app.ingestion.pipeline import safe_filename
from app.models import Dataset, DatasetUpload, Topic, User
from app.services import duplicates as dup
from app.services.audit import audit
from app.services.storage import get_storage

router = APIRouter(prefix="/api/datasets/ingest", tags=["dataset-ingestion"])


class ConfirmIn(BaseModel):
    title: str = Field(min_length=3, max_length=300)
    description: str = Field(default="", max_length=6000)
    region: str = Field(default="Global")
    license: str = Field(default="", max_length=64)
    source: str = Field(default="", max_length=255)
    source_url: str = Field(default="", max_length=500)
    doi: str = Field(default="", max_length=160)
    creator: str = Field(default="", max_length=255)
    year: int | None = Field(default=None, ge=1800, le=2100)
    keywords: list[str] = Field(default_factory=list, max_length=12)
    topics: list[str] = Field(default_factory=list, max_length=8)
    units: dict[str, str] = Field(default_factory=dict)
    descriptions: dict[str, str] = Field(default_factory=dict)
    visibility: str = Field(default="public", pattern="^(public|internal)$")
    drop_duplicates: bool = False
    acknowledge_errors: bool = False
    duplicate_action: str = Field(default="keep_both", pattern="^(keep_both|cancel)$")


def upload_out(u: DatasetUpload, db: Session | None = None) -> dict:
    out = {"token": u.token, "filename": u.filename, "format": u.file_format, "size_bytes": u.size_bytes,
           "status": u.status, "steps": u.steps or [], "error": u.error, "analysis": u.analysis,
           "created_at": u.created_at.isoformat() if u.created_at else None}
    if db is not None and u.dataset_id:
        d = db.get(Dataset, u.dataset_id)
        out["dataset"] = {"slug": d.slug, "title": d.title, "status": d.status, "url": f"/datasets/{d.slug}"} if d else None
    return out


def _get(db: Session, token: str, user: User) -> DatasetUpload:
    u = db.scalar(select(DatasetUpload).where(DatasetUpload.token == token))
    if not u or (u.created_by != user.id and not can(user, "manage_repository")):
        raise HTTPException(404, "Upload not found.")
    return u


@router.get("/options")
def options(db: Session = Depends(get_db)):
    return {"formats": ["CSV", "TSV", "JSON", "GeoJSON"], "planned_formats": ["NetCDF"],
            "max_mb": settings.MAX_DATASET_MB, "max_rows": settings.MAX_DATASET_ROWS, "regions": sorted(di.REGIONS),
            "topics": [{"slug": t.slug, "name": t.name} for t in db.scalars(select(Topic).order_by(Topic.name))]}


@router.post("/analyze", dependencies=[Depends(rate_limit("upload"))])
async def analyze(file: UploadFile = File(...), db: Session = Depends(get_db), user: User = Depends(require_permission("upload"))):
    name = safe_filename(file.filename or "dataset.csv")
    data = await file.read(settings.MAX_DATASET_MB * 1024 * 1024 + 1)
    try:
        analysis = di.analyze(name, data)
    except di.DatasetValidationError as exc:
        audit(db, user, "upload", "dataset", name[:64], f"Rejected: {exc}", status="failure")
        raise HTTPException(422, str(exc))
    content_hash = dup.sha256_bytes(data)
    analysis["duplicates"] = dup.check_dataset(db, content_hash=content_hash, title=analysis["suggested_title"],
                                               filename=name, columns=[c["name"] for c in analysis["schema"]])
    token = secrets.token_urlsafe(18)
    key = f"datasets/{token[:12]}-{name}"
    get_storage().save_bytes(key, data)
    u = DatasetUpload(token=token, filename=name, file_key=key, file_format=analysis["format"], size_bytes=len(data),
                      content_hash=content_hash, analysis=analysis, status="analyzed", created_by=user.id,
                      steps=di.initial_register_steps())
    db.add(u)
    db.commit()
    return upload_out(u)


@router.post("/{token}/confirm")
def confirm(token: str, body: ConfirmIn, background: BackgroundTasks, db: Session = Depends(get_db),
            user: User = Depends(require_permission("upload"))):
    u = _get(db, token, user)
    if u.status != "analyzed":
        raise HTTPException(409, f"This upload is already '{u.status}'.")
    if body.duplicate_action == "cancel":
        u.status = "cancelled"
        db.commit()
        return upload_out(u, db)
    a = u.analysis or {}
    if (a.get("summary") or {}).get("errors") and not body.acknowledge_errors:
        raise HTTPException(422, "Validation found errors. Review them and confirm to register the dataset anyway.")
    if body.region not in di.REGIONS:
        raise HTTPException(422, "Unknown region.")
    if body.topics:
        known = {t.slug for t in db.scalars(select(Topic).where(Topic.slug.in_(body.topics)))}
        if set(body.topics) - known:
            raise HTTPException(422, "Unknown topic.")
    meta = body.model_dump()
    meta["keywords"] = [k.strip()[:40] for k in body.keywords if k.strip()]
    u.status = "registering"
    db.commit()
    audit(db, user, "dataset_confirm", "dataset", u.filename[:64], f"Confirmed: {body.title}")
    background.add_task(di.register, u.id, meta, user.id)
    return upload_out(u, db)


@router.get("/{token}")
def status(token: str, db: Session = Depends(get_db), user: User = Depends(require_permission("upload"))):
    return upload_out(_get(db, token, user), db)


@router.post("/{token}/cancel")
def cancel(token: str, db: Session = Depends(get_db), user: User = Depends(require_permission("upload"))):
    u = _get(db, token, user)
    if u.status != "analyzed":
        raise HTTPException(409, f"This upload is already '{u.status}'.")
    u.status = "cancelled"
    db.commit()
    return upload_out(u, db)


@router.get("")
def my_uploads(db: Session = Depends(get_db), user: User = Depends(require_permission("upload"))):
    stmt = select(DatasetUpload).order_by(DatasetUpload.created_at.desc())
    if not can(user, "manage_repository"):
        stmt = stmt.where(DatasetUpload.created_by == user.id)
    rows = db.scalars(stmt.limit(30)).all()
    out = []
    for u in rows:
        o = upload_out(u, db)
        o.pop("analysis", None)
        out.append(o)
    return {"results": out}
