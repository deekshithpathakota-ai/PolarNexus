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
from app.ingestion.ocr import extract_pdf_with_ocr
from app.models import Document, IngestionJob, ResourceTopic, ResourceVersion, Topic, User
from app.services import versions
from app.services.duplicates import find_doi, sha256_file
from app.services.storage import mirror
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
         ("ocr", "OCR scanned pages"), ("metadata", "Extract metadata"), ("chunk", "Create document chunks"), ("embed", "Generate embeddings"),
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
        ocr_report: dict = {"status": "not_needed", "pages_ocr": []}
        if ext == ".pdf":
            text, pages, meta, ocr_report = extract_pdf_with_ocr(Path(path))
            native = pages - len(ocr_report.get("pages_needing_ocr", []))
            _step(db, job, "extract", "done", f"{pages} page(s); embedded text on {native} page(s)")
            job.ocr_status = ocr_report["status"]
            if ocr_report["status"] == "not_needed":
                _step(db, job, "ocr", "skipped", "Not needed — every page has embedded text")
            elif ocr_report["status"] == "unavailable":
                _step(db, job, "ocr", "skipped", f"{len(ocr_report['pages_needing_ocr'])} scanned page(s) found but OCR is "
                      "not available on this server (install tesseract-ocr or set OCR_ENABLED=true)")
            else:
                _step(db, job, "ocr", "done" if ocr_report["status"] != "failed" else "failed",
                      f"{ocr_report.get('engine') or 'tesseract'}: text recognised on page(s) "
                      f"{', '.join(map(str, ocr_report['pages_ocr'])) or 'none'}"
                      + (f"; failed on {', '.join(map(str, ocr_report['pages_failed']))}" if ocr_report.get("pages_failed") else ""))
        else:
            text, pages, meta = extract_text(Path(path), ext)
            _step(db, job, "extract", "done", f"{pages} page(s), {len(text):,} characters")
            _step(db, job, "ocr", "skipped", "Not applicable to text files")
        if len(text.strip()) < 200:
            if ocr_report.get("status") == "unavailable":
                raise ValidationError("No extractable text found. This looks like a scanned PDF and OCR is not available on this server.")
            raise ValidationError("No extractable text found (the PDF may be scanned and OCR could not read it).")
        md = infer_metadata(text, Path(path).name, meta, db)
        for k, v in overrides.items():
            if v and k != "update_slug":
                md[k] = v
        doi = find_doi(text[:20000])
        _step(db, job, "metadata", "done", f"Title, year {md['year']}, region {md['region']}, {len(md['keywords'])} keywords"
              + (f", DOI {doi}" if doi else ""))
        content_hash = sha256_file(path)
        target = db.scalar(select(Document).where(Document.slug == overrides["update_slug"])) if overrides.get("update_slug") else None
        if target is not None:
            # "Update existing": the current state is preserved in the version history before the new file replaces it
            versions.record(db, "document", target, "Snapshot before new file", target.status, user, commit=False)
            prev = db.scalar(select(ResourceVersion).where(ResourceVersion.resource_type == "document",
                                                          ResourceVersion.resource_id == target.id)
                             .order_by(ResourceVersion.version.desc()))
            if prev is not None:
                prev.snapshot = {**(prev.snapshot or {}), "file_path": target.file_path,
                                 "content_archive": (target.content or "")[:200_000]}
            doc = target
            doc.content, doc.abstract, doc.file_name, doc.file_path = text, md["abstract"], Path(path).name, path
            doc.page_count, doc.status, doc.keywords = pages, "processing", md["keywords"]
            doc.content_hash, doc.ocr_status, doc.ocr_pages = content_hash, ocr_report["status"], ocr_report.get("pages_ocr", [])
            doc.doi = doc.doi or doi
            change = f"New document uploaded ({Path(path).name})"
        else:
            slug = slugify(md["title"])
            if db.scalar(select(Document).where(Document.slug == slug)):
                slug = f"{slug}-{job.id}"
            doc = Document(slug=slug, title=md["title"], doc_type=md.get("doc_type") or "Technical Report",
                           abstract=md["abstract"], content=text, authors=md.get("authors") or [user.name],
                           institution=user.institution, region=md["region"], year=int(md["year"]),
                           keywords=md["keywords"], source=f"Uploaded by {user.name}", file_name=Path(path).name,
                           file_path=path, page_count=pages, status="processing", visibility=md.get("visibility") or "public",
                           is_demo=False, uploaded_by=user.id, content_hash=content_hash, doi=doi,
                           ocr_status=ocr_report["status"], ocr_pages=ocr_report.get("pages_ocr", []))
            db.add(doc)
            db.flush()
            for tid in md["topics"]:
                db.add(ResourceTopic(resource_type="document", resource_id=doc.id, topic_id=tid))
            change = f"Uploaded ({Path(path).name})" + (f" · OCR {ocr_report['status']}" if ocr_report["status"] != "not_needed" else "")
        job.document_id = doc.id
        db.commit()
        mirror(path)
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
        from app.services.provenance import ensure_for

        ensure_for(db, "document", doc)
        versions.record(db, "document", doc, change, "user_uploaded", user)
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
