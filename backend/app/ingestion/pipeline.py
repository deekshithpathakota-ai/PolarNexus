"""Document ingestion: validate -> store -> extract text -> extract metadata -> chunk -> embed -> index.

Each step is recorded on the IngestionJob so the UI can show real progress."""
from __future__ import annotations

import logging
import re
import time
from collections import Counter
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.models import Document, IngestionJob, ResourceTopic, Topic, User
from app.rag.embeddings import get_provider
from app.rag.indexer import index_document, vector_backend_name
from app.services.audit import audit, notify
from app.utils.text import content_terms, slugify

log = logging.getLogger("polarnexus.ingestion")

ALLOWED = {
    ".pdf": ("application/pdf", [b"%PDF-"]),
    ".txt": ("text/plain", []),
    ".md": ("text/markdown", []),
}
STEPS = [("upload", "Upload document"), ("validate", "Validate file"), ("extract", "Extract text"),
         ("metadata", "Extract metadata"), ("chunk", "Create document chunks"), ("embed", "Generate embeddings"),
         ("store", "Store vectors"), ("index", "Index document"), ("ready", "Mark repository status")]

REGION_KEYWORDS = {
    "Antarctic": ["antarctic", "antarctica", "maitri", "bharati", "dronning maud", "larsemann", "schirmacher"],
    "Arctic": ["arctic", "svalbard", "ny-alesund", "ny-ålesund", "kongsfjorden", "himadri", "greenland"],
    "Southern Ocean": ["southern ocean", "circumpolar", "polar front", "subantarctic"],
    "Himalaya": ["himalaya", "himalayan", "chandra", "himansh", "third pole"],
}


class ValidationError(ValueError):
    pass


def safe_filename(name: str) -> str:
    base = Path(name).name
    stem, ext = Path(base).stem, Path(base).suffix.lower()
    stem = re.sub(r"[^A-Za-z0-9._-]+", "-", stem).strip(".-")[:80] or "upload"
    return f"{stem}{ext}"


def validate_upload(filename: str, data: bytes, content_type: str | None) -> str:
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED:
        raise ValidationError(f"Unsupported file type '{ext or 'none'}'. Allowed for documents: PDF, TXT, MD.")
    if len(data) == 0:
        raise ValidationError("The file is empty.")
    if len(data) > settings.MAX_UPLOAD_MB * 1024 * 1024:
        raise ValidationError(f"The file exceeds the {settings.MAX_UPLOAD_MB} MB limit.")
    if ".." in filename or "/" in filename or "\\" in filename:
        raise ValidationError("Invalid file name.")
    expected_mime, magic = ALLOWED[ext]
    if magic and not any(data.startswith(m) for m in magic):
        raise ValidationError("The file content does not match its extension (invalid PDF signature).")
    if ext in {".txt", ".md"}:
        try:
            data.decode("utf-8")
        except UnicodeDecodeError:
            raise ValidationError("Text files must be UTF-8 encoded.")
        if b"\x00" in data:
            raise ValidationError("The file contains binary content.")
    if content_type and content_type not in {expected_mime, "application/octet-stream", "text/x-markdown", ""} \
            and not content_type.startswith("text/") and ext != ".pdf":
        raise ValidationError(f"Unexpected content type '{content_type}'.")
    return ext


def extract_text(path: Path, ext: str) -> tuple[str, int, dict]:
    if ext == ".pdf":
        import fitz  # PyMuPDF

        with fitz.open(path) as pdf:
            pages = [p.get_text("text") for p in pdf]
            meta = pdf.metadata or {}
        parts = []
        for i, t in enumerate(pages, start=1):
            t = re.sub(r"[ \t]+", " ", t).strip()
            if t:
                parts.append(f"[[page {i}]]\n{t}")
        return "\n\n".join(parts), len(pages), meta
    text = path.read_text(encoding="utf-8")
    return text, max(1, len(text) // 3000 + 1), {}


def infer_metadata(text: str, filename: str, pdf_meta: dict, db: Session) -> dict:
    lines = [l.strip("# ").strip() for l in text.splitlines() if l.strip() and not l.startswith("[[page")]
    title = (pdf_meta.get("title") or "").strip() or next((l for l in lines if 8 <= len(l) <= 160), Path(filename).stem)
    years = [int(y) for y in re.findall(r"\b(19[5-9]\d|20[0-4]\d)\b", text[:6000])]
    year = Counter(years).most_common(1)[0][0] if years else time.gmtime().tm_year
    low = text.lower()
    region_scores = {r: sum(low.count(k) for k in kws) for r, kws in REGION_KEYWORDS.items()}
    region = max(region_scores, key=region_scores.get) if any(region_scores.values()) else "Antarctic"
    terms = Counter(t for t in content_terms(text) if len(t) > 4 and not t.isdigit())
    keywords = [t for t, _ in terms.most_common(8)]
    topic_hits = []
    for t in db.scalars(select(Topic)):
        words = [w for w in content_terms(t.name + " " + t.description) if len(w) > 4][:6]
        score = sum(low.count(w) for w in words)
        if score >= 3:
            topic_hits.append((score, t))
    topic_hits.sort(key=lambda x: -x[0])
    abstract_match = re.search(r"abstract[:\s]*\n?(.{80,1200}?)(\n\n|\n[A-Z][a-z]+\n)", text, flags=re.I | re.S)
    abstract = abstract_match.group(1).strip() if abstract_match else " ".join(lines[1:6])[:900]
    return {"title": title[:300], "year": year, "region": region, "keywords": keywords,
            "topics": [t.id for _, t in topic_hits[:4]], "abstract": re.sub(r"\s+", " ", abstract)}


def _step(db: Session, job: IngestionJob, key: str, status: str, detail: str = "") -> None:
    steps = [dict(s) for s in job.steps]
    for s in steps:
        if s["key"] == key:
            s["status"], s["detail"] = status, detail
    job.steps = steps
    db.commit()
    time.sleep(0.25)  # keeps progress visible in the UI for very small files


def new_job(db: Session, filename: str, user: User) -> IngestionJob:
    job = IngestionJob(file_name=filename, status="processing", created_by=user.id,
                       steps=[{"key": k, "label": l, "status": "pending", "detail": ""} for k, l in STEPS])
    db.add(job)
    db.commit()
    return job


def run_ingestion(job_id: int, path: str, ext: str, overrides: dict, user_id: int) -> None:
    """Runs in a background task with its own session."""
    db = SessionLocal()
    job = db.get(IngestionJob, job_id)
    user = db.get(User, user_id)
    try:
        _step(db, job, "upload", "done", f"{Path(path).name} received")
        _step(db, job, "validate", "done", f"{ext.upper().lstrip('.')} — {Path(path).stat().st_size / 1024:.0f} KB, signature and size checked")
        _step(db, job, "extract", "running")
        text, pages, meta = extract_text(Path(path), ext)
        if len(text.strip()) < 200:
            raise ValidationError("No extractable text found (scanned PDFs need OCR, which is not enabled in this prototype).")
        _step(db, job, "extract", "done", f"{pages} page(s), {len(text):,} characters")
        md = infer_metadata(text, Path(path).name, meta, db)
        for k, v in overrides.items():
            if v:
                md[k] = v
        _step(db, job, "metadata", "done", f"Title, year {md['year']}, region {md['region']}, {len(md['keywords'])} keywords")
        slug = slugify(md["title"])
        if db.scalar(select(Document).where(Document.slug == slug)):
            slug = f"{slug}-{job.id}"
        doc = Document(slug=slug, title=md["title"], doc_type=md.get("doc_type") or "Technical Report",
                       abstract=md["abstract"], content=text, authors=md.get("authors") or [user.name],
                       institution=user.institution, region=md["region"], year=int(md["year"]),
                       keywords=md["keywords"], source=f"Uploaded by {user.name}", file_name=Path(path).name,
                       file_path=path, page_count=pages, status="processing", visibility=md.get("visibility") or "public",
                       is_demo=False, uploaded_by=user.id)
        db.add(doc)
        db.flush()
        for tid in md["topics"]:
            db.add(ResourceTopic(resource_type="document", resource_id=doc.id, topic_id=tid))
        job.document_id = doc.id
        db.commit()
        _step(db, job, "chunk", "running")
        n = index_document(db, doc)
        _step(db, job, "chunk", "done", f"{n} passages with page provenance")
        provider = get_provider(db)
        _step(db, job, "embed", "done", provider.name if provider else "keyword-only (no embedding model)")
        _step(db, job, "store", "done", vector_backend_name())
        _step(db, job, "index", "done", "Full-text + vector index updated")
        doc.status = "indexed"
        job.status = "completed"
        db.commit()
        _step(db, job, "ready", "done", "Indexed and searchable")
        audit(db, user, "upload", "document", doc.slug, f"Ingested {Path(path).name} ({n} passages)")
        notify(db, "Document processing completed", f"“{doc.title}” is indexed and searchable.",
               f"/resources/{doc.slug}", "success", user_id=user.id)
        notify(db, "New resource indexed", f"“{doc.title}” was added by {user.name}.", f"/resources/{doc.slug}",
               "info", role="admin")
    except Exception as exc:  # record failure on the job; never crash the worker
        log.exception("ingestion failed")
        db.rollback()
        job = db.get(IngestionJob, job_id)
        steps = [dict(s) for s in job.steps]
        for s in steps:
            if s["status"] in {"running", "pending"}:
                s["status"] = "failed" if s["status"] == "running" else "skipped"
        job.steps, job.status = steps, "failed"
        job.error = str(exc) if isinstance(exc, ValidationError) else "Processing failed. Please check the file and try again."
        if job.document_id:
            d = db.get(Document, job.document_id)
            if d:
                d.status = "failed"
        db.commit()
        audit(db, user, "upload", "document", Path(path).name, job.error, status="failure")
    finally:
        db.close()
