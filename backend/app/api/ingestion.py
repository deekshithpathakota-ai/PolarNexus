import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.security import can, require_permission
from app.core.config import settings
from app.core.database import get_db
from app.core.ratelimit import rate_limit
from app.ingestion.pipeline import ValidationError, new_job, run_ingestion, safe_filename, validate_upload
from app.models import Document, IngestionJob, User
from app.services import duplicates as dup
from app.services.audit import audit
from app.services.serializers import iso

router = APIRouter(prefix="/api/ingestion", tags=["ingestion"])

DOC_TYPES = {"Research Paper", "Technical Report", "Expedition Report", "Educational Resource", "News / Outreach"}
REGIONS = {"Antarctic", "Arctic", "Southern Ocean", "Himalaya", "India"}


def job_out(j: IngestionJob) -> dict:
    return {"id": j.id, "file_name": j.file_name, "status": j.status, "steps": j.steps, "error": j.error,
            "document_id": j.document_id, "created_at": iso(j.created_at), "ocr_status": j.ocr_status or ""}


@router.post("/check-duplicates")
async def check_duplicates(file: UploadFile = File(...), title: str = Form(""),
                           db: Session = Depends(get_db), user: User = Depends(require_permission("upload"))):
    """Pre-upload duplicate check (content hash, DOI, title, file name, text overlap). Nothing is stored."""
    name = safe_filename(file.filename or "upload")
    data = await file.read(settings.MAX_UPLOAD_MB * 1024 * 1024 + 1)
    try:
        ext = validate_upload(name, data, file.content_type)
    except ValidationError as exc:
        raise HTTPException(422, str(exc))
    text = ""
    if ext in {".txt", ".md"}:
        text = data.decode("utf-8", "replace")
    else:
        try:
            import fitz

            with fitz.open(stream=data, filetype="pdf") as pdf:
                text = "\n".join(p.get_text("text") for p in pdf)[:200_000]
                title = title or (pdf.metadata or {}).get("title") or ""
        except Exception:
            text = ""
    cands = dup.check_document(db, content_hash=dup.sha256_bytes(data), title=title or name, filename=name, text=text)
    return {"file_name": name, "duplicates": cands, "potential_duplicate": bool(cands),
            "options": ["keep_both", "update_existing", "review", "cancel"]}


@router.post("/upload", dependencies=[Depends(rate_limit("upload"))])
async def upload(background: BackgroundTasks, file: UploadFile = File(...), title: str = Form(""),
                 doc_type: str = Form("Technical Report"), region: str = Form(""), year: str = Form(""),
                 authors: str = Form(""), visibility: str = Form("public"), update_existing: str = Form(""),
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
        if update_existing:
            target = db.scalar(select(Document).where(Document.slug == update_existing))
            if not target:
                raise ValidationError("The document to update was not found.")
            if not (can(user, "manage_repository") or target.uploaded_by == user.id):
                raise ValidationError("You can only add a new version to documents you uploaded.")
            if target.is_demo or target.metadata_only:
                raise ValidationError("Demonstration and metadata-only records cannot be replaced by an upload.")
    except ValidationError as exc:
        audit(db, user, "upload", "document", name, f"Rejected: {exc}", status="failure")
        raise HTTPException(422, str(exc))
    folder = Path(settings.STORAGE_DIR) / "documents"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{uuid.uuid4().hex[:10]}-{name}"
    path.write_bytes(data)
    job = new_job(db, name, user)
    overrides = {"title": title.strip()[:300], "doc_type": doc_type, "region": region, "year": int(year) if year else None,
                 "authors": [a.strip() for a in authors.split(",") if a.strip()][:20], "visibility": visibility,
                 "update_slug": update_existing or None}
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
