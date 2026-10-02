import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.security import can, require_permission
from app.core.config import settings
from app.core.database import get_db
from app.ingestion.pipeline import ValidationError, new_job, run_ingestion, safe_filename, validate_upload
from app.models import IngestionJob, User
from app.services.audit import audit
from app.services.serializers import iso

router = APIRouter(prefix="/api/ingestion", tags=["ingestion"])

DOC_TYPES = {"Research Paper", "Technical Report", "Expedition Report", "Educational Resource", "News / Outreach"}
REGIONS = {"Antarctic", "Arctic", "Southern Ocean", "Himalaya", "India"}


def job_out(j: IngestionJob) -> dict:
    return {"id": j.id, "file_name": j.file_name, "status": j.status, "steps": j.steps, "error": j.error,
            "document_id": j.document_id, "created_at": iso(j.created_at)}


@router.post("/upload")
async def upload(background: BackgroundTasks, file: UploadFile = File(...), title: str = Form(""),
                 doc_type: str = Form("Technical Report"), region: str = Form(""), year: str = Form(""),
                 authors: str = Form(""), visibility: str = Form("public"),
                 db: Session = Depends(get_db), user: User = Depends(require_permission("upload"))):
    name = safe_filename(file.filename or "upload")
    data = await file.read(settings.MAX_UPLOAD_MB * 1024 * 1024 + 1)
    try:
        ext = validate_upload(name, data, file.content_type)
        if doc_type not in DOC_TYPES:
            raise ValidationError("Unknown document type.")
        if region and region not in REGIONS:
            raise ValidationError("Unknown region.")
        if year and not (year.isdigit() and 1900 <= int(year) <= 2100):
            raise ValidationError("Year must be between 1900 and 2100.")
        if visibility not in {"public", "internal"}:
            raise ValidationError("Visibility must be public or internal.")
    except ValidationError as exc:
        audit(db, user, "upload", "document", name, f"Rejected: {exc}", status="failure")
        raise HTTPException(422, str(exc))
    folder = Path(settings.STORAGE_DIR) / "documents"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{uuid.uuid4().hex[:10]}-{name}"
    path.write_bytes(data)
    job = new_job(db, name, user)
    overrides = {"title": title.strip()[:300], "doc_type": doc_type, "region": region, "year": int(year) if year else None,
                 "authors": [a.strip() for a in authors.split(",") if a.strip()][:20], "visibility": visibility}
    background.add_task(run_ingestion, job.id, str(path), ext, overrides, user.id)
    return job_out(job)


@router.get("/jobs/{job_id}")
def get_job(job_id: int, db: Session = Depends(get_db), user: User = Depends(require_permission("upload"))):
    j = db.get(IngestionJob, job_id)
    if not j or (j.created_by != user.id and not can(user, "manage_repository")):
        raise HTTPException(404, "Job not found.")
    out = job_out(j)
    if j.document_id:
        from app.models import Document
        d = db.get(Document, j.document_id)
        out["document"] = {"slug": d.slug, "title": d.title, "status": d.status} if d else None
    return out


@router.get("/jobs")
def list_jobs(db: Session = Depends(get_db), user: User = Depends(require_permission("upload"))):
    stmt = select(IngestionJob).order_by(IngestionJob.created_at.desc())
    if not can(user, "manage_repository"):
        stmt = stmt.where(IngestionJob.created_by == user.id)
    return {"results": [job_out(j) for j in db.scalars(stmt.limit(30))]}
