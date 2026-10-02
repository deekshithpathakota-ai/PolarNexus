"""Media upload, processing status, retry, and safe file serving."""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.security import can, get_current_user, get_current_user_optional, require_permission
from app.core.config import settings
from app.core.database import get_db
from app.ingestion import media as mi
from app.models import Expedition, Media, Researcher, Station, Topic, User
from app.services.audit import audit
from app.services.catalog import build_catalog
from app.services.serializers import media_out
from app.utils.text import slugify

router = APIRouter(prefix="/api", tags=["media-ingestion"])

REGIONS = {"Antarctic", "Arctic", "Southern Ocean", "Himalaya", "India"}
CATEGORIES = {"Antarctica", "Arctic", "Atmospheric Science", "Expeditions", "Ice & Glaciers", "Ocean", "Outreach",
              "Research Stations", "Researchers", "Wildlife", "Other"}
CHUNK = 1024 * 1024


async def _save_stream(upload: UploadFile, dest: Path, limit: int) -> int:
    """Streams the upload to disk in 1 MB chunks, enforcing the size limit without buffering the whole file."""
    size = 0
    try:
        with open(dest, "wb") as fh:
            while True:
                chunk = await upload.read(CHUNK)
                if not chunk:
                    break
                size += len(chunk)
                if size > limit:
                    raise HTTPException(413, f"The file exceeds the {limit // (1024 * 1024)} MB limit for this media type.")
                fh.write(chunk)
    except HTTPException:
        dest.unlink(missing_ok=True)
        raise
    return size


def _within_storage(p: str) -> Path | None:
    """Path-traversal guard: only files inside STORAGE_DIR are ever served."""
    if not p:
        return None
    root = Path(settings.STORAGE_DIR).resolve()
    try:
        path = Path(p).resolve()
    except OSError:
        return None
    return path if path.is_file() and path.is_relative_to(root) else None


def _visible(db: Session, m: Media, user: User | None) -> bool:
    if user and (m.uploaded_by == user.id or can(user, "manage_repository")):
        return True
    return build_catalog(db, user).card("media", m.id) is not None


def _get(db: Session, slug: str) -> Media:
    m = db.scalar(select(Media).where(Media.slug == slug))
    if not m:
        raise HTTPException(404, "Media item not found.")
    return m


@router.post("/media/upload")
async def upload_media(background: BackgroundTasks, file: UploadFile = File(...), title: str = Form(""),
                       description: str = Form(""), category: str = Form("Other"), region: str = Form("Antarctic"),
                       year: str = Form(""), tags: str = Form(""), credit: str = Form(""), license: str = Form(""),
                       location: str = Form(""), station: str = Form(""), expedition: str = Form(""),
                       researcher: str = Form(""), topics: str = Form(""), visibility: str = Form("public"),
                       captured_at: str = Form(""), transcript: UploadFile | None = File(None),
                       db: Session = Depends(get_db), user: User = Depends(require_permission("upload"))):
    original = file.filename or "upload"
    try:
        kind = mi.kind_for(original)
        if region not in REGIONS:
            raise mi.MediaValidationError("Unknown region.")
        if category not in CATEGORIES:
            raise mi.MediaValidationError("Unknown category.")
        if visibility not in {"public", "internal"}:
            raise mi.MediaValidationError("Visibility must be public or internal.")
        if year and not (year.isdigit() and 1900 <= int(year) <= 2100):
            raise mi.MediaValidationError("Year must be between 1900 and 2100.")
        for value, model, label in ((station, Station, "station"), (expedition, Expedition, "expedition"),
                                    (researcher, Researcher, "researcher")):
            if value and not db.scalar(select(model).where(model.slug == value)):
                raise mi.MediaValidationError(f"Unknown {label}.")
        topic_slugs = [t.strip() for t in topics.split(",") if t.strip()][:10]
        if topic_slugs and len(db.scalars(select(Topic).where(Topic.slug.in_(topic_slugs))).all()) != len(set(topic_slugs)):
            raise mi.MediaValidationError("Unknown topic.")
    except mi.MediaValidationError as exc:
        audit(db, user, "upload", "media", original[:64], f"Rejected: {exc}", status="failure")
        raise HTTPException(422, str(exc))

    safe, dest = mi.new_media_paths(original)
    size = await _save_stream(file, dest, mi.limit_bytes(kind))
    transcript_path = None
    try:
        mime = mi.check_signature(dest, safe, file.content_type)
        if kind == "image":
            mi.image_metadata(dest)  # decode now so an invalid image is rejected immediately
        elif mi.ffmpeg_available():
            mi.probe(dest)
        if transcript and transcript.filename:
            if kind != "video":
                raise mi.MediaValidationError("Transcripts can only be attached to videos.")
            text_ext = Path(transcript.filename).suffix.lower()
            if text_ext not in mi.TRANSCRIPT_EXT:
                raise mi.MediaValidationError("Transcript must be a .vtt, .srt or .txt file.")
            tpath = mi.media_dir("transcripts") / f"{dest.stem}{text_ext}"
            await _save_stream(transcript, tpath, 2 * 1024 * 1024)
            raw = tpath.read_bytes()
            if b"\x00" in raw:
                tpath.unlink(missing_ok=True)
                raise mi.MediaValidationError("The transcript contains binary content.")
            try:
                raw.decode("utf-8")
            except UnicodeDecodeError:
                tpath.unlink(missing_ok=True)
                raise mi.MediaValidationError("Transcripts must be UTF-8 text.")
            transcript_path = str(tpath)
    except mi.MediaValidationError as exc:
        dest.unlink(missing_ok=True)
        audit(db, user, "upload", "media", safe, f"Rejected: {exc}", status="failure")
        raise HTTPException(422, str(exc))

    clean_title = (title.strip() or Path(safe).stem.replace("-", " ").replace("_", " ").title())[:300]
    slug = slugify(clean_title)[:140] or "media"
    if db.scalar(select(Media).where(Media.slug == slug)):
        slug = f"{slug}-{dest.stem[:8]}"
    from datetime import datetime, timezone
    cap = None
    if captured_at:
        try:
            cap = datetime.fromisoformat(captured_at).replace(tzinfo=timezone.utc)
        except ValueError:
            raise HTTPException(422, "captured_at must be an ISO date (YYYY-MM-DD).")
    m = Media(slug=slug, title=clean_title, description=description.strip()[:5000], media_type=kind, category=category,
              region=region, year=int(year) if year else (cap.year if cap else datetime.now(timezone.utc).year),
              credit=(credit.strip() or f"Uploaded by {user.name}")[:255], license=license.strip()[:128] or "All rights reserved (uploader)",
              tags=[t.strip()[:40] for t in tags.split(",") if t.strip()][:20], scene="ice", file_path=str(dest),
              visibility=visibility, is_demo=False, status="indexed", filename=safe, mime_type=mime, size_bytes=size,
              location=location.strip()[:255], captured_at=cap, processing_status="processing",
              processing_steps=mi.initial_steps(kind), uploaded_by=user.id)
    db.add(m)
    db.commit()
    links = {"station": station or None, "expedition": expedition or None, "researcher": researcher or None, "topics": topic_slugs}
    background.add_task(mi.process_media, m.id, transcript_path, links, user.id)
    return media_out(m)


@router.get("/media/{slug}/processing")
def processing_status(slug: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    m = _get(db, slug)
    if m.uploaded_by != user.id and not can(user, "manage_repository"):
        raise HTTPException(404, "Media item not found.")
    return {"slug": m.slug, "processing_status": m.processing_status, "steps": m.processing_steps or [],
            "error": m.processing_error or "", "media": media_out(m)}


@router.post("/media/{slug}/reprocess")
def reprocess(slug: str, background: BackgroundTasks, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    m = _get(db, slug)
    if m.uploaded_by != user.id and not can(user, "manage_repository"):
        raise HTTPException(403, "Only the uploader or an administrator can retry processing.")
    if not _within_storage(m.file_path):
        raise HTTPException(409, "The original file is no longer available; please upload it again.")
    if m.processing_status not in {"failed", "ready"}:
        raise HTTPException(409, "This item is already being processed.")
    tpath = next((str(p) for p in mi.media_dir("transcripts").glob(f"{Path(m.file_path).stem}.*")), None)
    m.processing_status, m.processing_error, m.processing_steps = "processing", "", mi.initial_steps(m.media_type)
    db.commit()
    audit(db, user, "reprocess", "media", m.slug, "Processing restarted")
    background.add_task(mi.process_media, m.id, tpath, {}, user.id)
    return media_out(m)


@router.get("/my/media-uploads")
def my_uploads(db: Session = Depends(get_db), user: User = Depends(require_permission("upload"))):
    stmt = select(Media).where(Media.is_demo.is_(False)).order_by(Media.created_at.desc())
    if not can(user, "manage_repository"):
        stmt = stmt.where(Media.uploaded_by == user.id)
    return {"results": [media_out(m) for m in db.scalars(stmt.limit(30))]}


@router.get("/media-options")
def upload_options(db: Session = Depends(get_db)):
    return {"regions": sorted(REGIONS), "categories": sorted(CATEGORIES),
            "image_formats": sorted({e.lstrip('.').upper() for e in mi.IMAGE_EXT}),
            "video_formats": sorted({e.lstrip('.').upper() for e in mi.VIDEO_EXT}),
            "max_image_mb": settings.MAX_IMAGE_MB, "max_video_mb": settings.MAX_VIDEO_MB,
            "video_processing": "ffmpeg" if mi.ffmpeg_available() else "unavailable",
            "speech_to_text": settings.STT_MODEL if settings.stt_enabled else None,
            "stations": [{"slug": s.slug, "name": s.name} for s in db.scalars(select(Station).order_by(Station.name))],
            "expeditions": [{"slug": e.slug, "name": e.name} for e in db.scalars(select(Expedition).order_by(Expedition.year.desc()))],
            "researchers": [{"slug": r.slug, "name": r.name} for r in db.scalars(select(Researcher).order_by(Researcher.name))],
            "topics": [{"slug": t.slug, "name": t.name} for t in db.scalars(select(Topic).order_by(Topic.name))]}


def _serve(path: Path | None, mime: str, download_name: str | None = None):
    if not path:
        raise HTTPException(404, "File not available.")
    headers = {"Cache-Control": "private, max-age=3600", "X-Content-Type-Options": "nosniff",
               "Content-Security-Policy": "default-src 'none'; sandbox"}
    return FileResponse(path, media_type=mime, headers=headers, filename=download_name,
                        content_disposition_type="inline")


@router.get("/media/{slug}/file")
def media_file(slug: str, db: Session = Depends(get_db), user: User | None = Depends(get_current_user_optional)):
    m = _get(db, slug)
    if not _visible(db, m, user):
        raise HTTPException(404, "Media item not found.")
    return _serve(_within_storage(m.file_path), m.mime_type or "application/octet-stream", m.filename or None)


@router.get("/media/{slug}/thumbnail")
def media_thumbnail(slug: str, db: Session = Depends(get_db), user: User | None = Depends(get_current_user_optional)):
    m = _get(db, slug)
    if not _visible(db, m, user):
        raise HTTPException(404, "Media item not found.")
    return _serve(_within_storage(m.thumbnail_path), "image/jpeg")
