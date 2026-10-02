"""Media ingestion: upload -> validate -> store -> metadata (EXIF / ffprobe) -> thumbnail -> transcript -> index.

Images are decoded with Pillow (which also verifies they are real images). Video metadata, thumbnails and audio use
ffmpeg/ffprobe when they are installed on the server; speech-to-text uses an OpenAI-compatible
/audio/transcriptions endpoint when an API key is configured. Anything unavailable is recorded as a *skipped* step
with the reason — never faked. Processing runs in a background task with its own DB session, so the UI stays live.
"""
from __future__ import annotations

import json
import logging
import re
import shutil
import subprocess
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.ingestion.pipeline import safe_filename
from app.models import Expedition, Media, Researcher, ResourceLink, ResourceTopic, Station, Topic, User
from app.services.audit import audit, notify

log = logging.getLogger("polarnexus.media")

IMAGE_EXT = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp",
             ".tif": "image/tiff", ".tiff": "image/tiff"}
VIDEO_EXT = {".mp4": "video/mp4", ".m4v": "video/mp4", ".mov": "video/quicktime", ".webm": "video/webm"}
TRANSCRIPT_EXT = {".vtt", ".srt", ".txt"}

IMAGE_STEPS = [("upload", "Upload"), ("validate", "Validate file"), ("store", "Store file"),
               ("metadata", "Extract metadata"), ("thumbnail", "Generate thumbnail"), ("exif", "Extract EXIF"),
               ("searchable", "Generate searchable metadata"), ("associate", "Associate with entities"),
               ("index", "Index"), ("ready", "Repository")]
VIDEO_STEPS = [("upload", "Upload"), ("validate", "Validate file"), ("store", "Store file"),
               ("thumbnail", "Generate thumbnail"), ("metadata", "Extract metadata"), ("audio", "Extract audio"),
               ("transcript", "Speech-to-text / transcript"), ("index", "Index transcript"),
               ("searchable", "Generate searchable metadata"), ("associate", "Associate with entities"),
               ("ready", "Repository")]


class MediaValidationError(ValueError):
    pass


def media_dir(sub: str) -> Path:
    d = Path(settings.STORAGE_DIR) / "media" / sub
    d.mkdir(parents=True, exist_ok=True)
    return d


def kind_for(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    if ext in IMAGE_EXT:
        return "image"
    if ext in VIDEO_EXT:
        return "video"
    raise MediaValidationError(f"Unsupported media type '{ext or 'none'}'. Images: JPG, PNG, WEBP, TIFF. "
                               "Videos: MP4, MOV, WEBM.")


def limit_bytes(kind: str) -> int:
    return (settings.MAX_IMAGE_MB if kind == "image" else settings.MAX_VIDEO_MB) * 1024 * 1024


def check_signature(path: Path, filename: str, content_type: str | None) -> str:
    """Validates the file's magic bytes against its extension. Returns the canonical MIME type."""
    ext = Path(filename).suffix.lower()
    with open(path, "rb") as fh:
        head = fh.read(32)
    if not head:
        raise MediaValidationError("The file is empty.")
    ok = False
    if ext in {".jpg", ".jpeg"}:
        ok = head.startswith(b"\xff\xd8\xff")
    elif ext == ".png":
        ok = head.startswith(b"\x89PNG\r\n\x1a\n")
    elif ext == ".webp":
        ok = head[:4] == b"RIFF" and head[8:12] == b"WEBP"
    elif ext in {".tif", ".tiff"}:
        ok = head[:4] in {b"II*\x00", b"MM\x00*"}
    elif ext in {".mp4", ".m4v", ".mov"}:
        ok = head[4:8] in {b"ftyp", b"moov", b"wide", b"mdat", b"free"}
    elif ext == ".webm":
        ok = head.startswith(b"\x1a\x45\xdf\xa3")
    if not ok:
        raise MediaValidationError("The file content does not match its extension (invalid file signature).")
    mime = IMAGE_EXT.get(ext) or VIDEO_EXT[ext]
    family = mime.split("/")[0]
    if content_type and content_type not in {"", "application/octet-stream"} and not content_type.startswith(family + "/"):
        raise MediaValidationError(f"Unexpected content type '{content_type}' for a {family} file.")
    return mime


def parse_transcript(raw: str) -> str:
    """Accepts WebVTT, SRT or plain text and returns the spoken text only."""
    lines = []
    for line in raw.splitlines():
        s = line.strip()
        if not s or s.upper().startswith("WEBVTT") or s.isdigit() or "-->" in s or s.startswith(("NOTE", "STYLE")):
            continue
        lines.append(re.sub(r"<[^>]+>", "", s))
    text = re.sub(r"\s+", " ", " ".join(lines)).strip()
    return text[:200_000]


# ------------------------------------------------------------------ image helpers
def _ratio(v) -> float:
    try:
        return float(v[0]) / float(v[1]) if isinstance(v, tuple) else float(v)
    except (TypeError, ValueError, ZeroDivisionError):
        return 0.0


def _gps(gps: dict) -> tuple[float, float] | None:
    try:
        def conv(vals):
            d, m, s = (_ratio(x) for x in vals)
            return d + m / 60 + s / 3600
        lat, lon = conv(gps[2]), conv(gps[4])
        if gps.get(1) in ("S", b"S"):
            lat = -lat
        if gps.get(3) in ("W", b"W"):
            lon = -lon
        if -90 <= lat <= 90 and -180 <= lon <= 180:
            return round(lat, 6), round(lon, 6)
    except (KeyError, TypeError, ValueError):
        return None
    return None


def image_metadata(path: Path) -> tuple[dict, dict]:
    """Returns (basic, exif). Raises MediaValidationError if the image cannot be decoded."""
    from PIL import Image, UnidentifiedImageError

    Image.MAX_IMAGE_PIXELS = settings.MAX_IMAGE_PIXELS
    try:
        with Image.open(path) as im:
            im.verify()  # structural check; the file must be reopened afterwards
        with Image.open(path) as im:
            basic = {"width": im.width, "height": im.height, "format": im.format, "mode": im.mode}
            raw = im.getexif()
            exif: dict = {}
            if raw:
                base = {271: "camera_make", 272: "camera_model", 306: "datetime", 274: "orientation"}
                for tag, name in base.items():
                    if raw.get(tag):
                        exif[name] = str(raw.get(tag)).strip("\x00 ")
                sub = raw.get_ifd(0x8769)
                for tag, name in {36867: "datetime_original", 33434: "exposure_time", 33437: "f_number",
                                  34855: "iso", 37386: "focal_length"}.items():
                    if sub.get(tag) is not None:
                        v = sub.get(tag)
                        exif[name] = round(_ratio(v), 4) if name in {"exposure_time", "f_number", "focal_length"} else str(v)
                gps = _gps(dict(raw.get_ifd(0x8825)))
                if gps:
                    exif["gps_latitude"], exif["gps_longitude"] = gps
    except (UnidentifiedImageError, OSError, SyntaxError) as exc:
        raise MediaValidationError(f"The image could not be decoded ({exc.__class__.__name__}).") from exc
    except Image.DecompressionBombError as exc:
        raise MediaValidationError("The image dimensions are too large to process safely.") from exc
    return basic, exif


def image_thumbnail(path: Path, out: Path) -> None:
    from PIL import Image, ImageOps

    with Image.open(path) as im:
        im = ImageOps.exif_transpose(im)
        im.thumbnail((640, 640))
        if im.mode not in ("RGB", "L"):
            im = im.convert("RGB")
        im.save(out, "JPEG", quality=82, optimize=True)


def _exif_datetime(exif: dict) -> datetime | None:
    for key in ("datetime_original", "datetime"):
        v = exif.get(key)
        if v:
            try:
                return datetime.strptime(v[:19], "%Y:%m:%d %H:%M:%S").replace(tzinfo=timezone.utc)
            except ValueError:
                continue
    return None


# ------------------------------------------------------------------ video helpers
def ffmpeg_available() -> bool:
    return bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))


def _run(args: list[str], timeout: int = 120) -> subprocess.CompletedProcess:
    return subprocess.run(args, capture_output=True, timeout=timeout, check=False)  # args list — never a shell


def probe(path: Path) -> dict:
    res = _run(["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(path)], 60)
    if res.returncode != 0:
        raise MediaValidationError("The video could not be read (ffprobe failed). The file may be corrupt.")
    data = json.loads(res.stdout or b"{}")
    v = next((s for s in data.get("streams", []) if s.get("codec_type") == "video"), None)
    a = next((s for s in data.get("streams", []) if s.get("codec_type") == "audio"), None)
    if not v:
        raise MediaValidationError("No video stream found in the file.")
    fmt = data.get("format", {})
    tags = {k.lower(): val for k, val in (fmt.get("tags") or {}).items()}
    return {"duration": float(fmt.get("duration") or v.get("duration") or 0), "width": v.get("width"),
            "height": v.get("height"), "video_codec": v.get("codec_name"), "audio_codec": a.get("codec_name") if a else None,
            "has_audio": bool(a), "container": fmt.get("format_name"), "bit_rate": fmt.get("bit_rate"),
            "creation_time": tags.get("creation_time"), "location": tags.get("location") or tags.get("com.apple.quicktime.location.iso6709")}


def _iso6709(s: str | None) -> tuple[float, float] | None:
    m = re.match(r"^([+-]\d+(?:\.\d+)?)([+-]\d+(?:\.\d+)?)", s or "")
    if m:
        lat, lon = float(m.group(1)), float(m.group(2))
        if -90 <= lat <= 90 and -180 <= lon <= 180:
            return lat, lon
    return None


def transcribe(audio: Path) -> str:
    with open(audio, "rb") as fh, httpx.Client(timeout=max(60.0, settings.AI_TIMEOUT_SECONDS * 4)) as client:
        resp = client.post(f"{settings.OPENAI_BASE_URL.rstrip('/')}/audio/transcriptions",
                           headers={"Authorization": f"Bearer {settings.OPENAI_API_KEY}"},
                           data={"model": settings.STT_MODEL, "response_format": "text"},
                           files={"file": (audio.name, fh, "audio/wav")})
        resp.raise_for_status()
        return resp.text.strip()


# ------------------------------------------------------------------ job bookkeeping
def initial_steps(kind: str) -> list[dict]:
    steps = IMAGE_STEPS if kind == "image" else VIDEO_STEPS
    return [{"key": k, "label": l, "status": "pending", "detail": ""} for k, l in steps]


def _step(db: Session, m: Media, key: str, status: str, detail: str = "", processing_status: str | None = None) -> None:
    steps = [dict(s) for s in (m.processing_steps or [])]
    for s in steps:
        if s["key"] == key:
            s["status"], s["detail"] = status, detail[:300]
    m.processing_steps = steps
    if processing_status:
        m.processing_status = processing_status
    db.commit()
    time.sleep(0.15)  # keeps progress visible in the UI for small files


def _associate(db: Session, m: Media, links: dict) -> str:
    done = []
    existing = {(l.target_type, l.target_id) for l in db.scalars(select(ResourceLink).where(
        ResourceLink.source_type == "media", ResourceLink.source_id == m.id))}
    for field, model, rtype, rel in (("station", Station, "station", "depicts"), ("expedition", Expedition, "expedition", "captured_during"),
                                     ("researcher", Researcher, "researcher", "features")):
        slug = links.get(field)
        if not slug:
            continue
        obj = db.scalar(select(model).where(model.slug == slug))
        if obj and (rtype, obj.id) not in existing:
            db.add(ResourceLink(source_type="media", source_id=m.id, target_type=rtype, target_id=obj.id, relation=rel))
            done.append(f"{rtype}: {getattr(obj, 'name', slug)}")
            if rtype == "station" and m.latitude is None:
                m.latitude, m.longitude = obj.latitude, obj.longitude
                m.location = m.location or obj.location_name
    have_topics = {rt.topic_id for rt in db.scalars(select(ResourceTopic).where(
        ResourceTopic.resource_type == "media", ResourceTopic.resource_id == m.id))}
    for t in db.scalars(select(Topic).where(Topic.slug.in_(links.get("topics") or []))):
        if t.id not in have_topics:
            db.add(ResourceTopic(resource_type="media", resource_id=m.id, topic_id=t.id))
            done.append(f"topic: {t.name}")
    db.commit()
    return ", ".join(done) or "No entities selected"


def _searchable(m: Media) -> str:
    """Adds factual, file-derived keywords (format, orientation, camera, duration) to the tags — nothing inferred."""
    tags = list(m.tags or [])
    extra = [m.media_type]
    if m.width and m.height:
        extra.append("landscape" if m.width > m.height else "portrait" if m.height > m.width else "square")
    if (m.exif or {}).get("camera_model"):
        extra.append(str(m.exif["camera_model"]))
    if m.transcript:
        extra.append("transcript")
    for t in extra:
        if t and t.lower() not in {x.lower() for x in tags}:
            tags.append(t)
    m.tags = tags[:30]
    if not m.description.strip():
        dims = f" ({m.width}×{m.height})" if m.width else ""
        m.description = f"{m.title}. Uploaded {m.media_type}{dims}."
    return f"{len(tags)} tags; " + ("transcript indexed" if m.transcript else "description and tags indexed")


# ------------------------------------------------------------------ pipeline
def process_media(media_id: int, transcript_path: str | None, links: dict, user_id: int) -> None:
    """Background task. Updates the Media row's steps as it goes; never raises."""
    from app.rag.indexer import index_resource
    from app.services.provenance import ensure_for

    db = SessionLocal()
    m = db.get(Media, media_id)
    user = db.get(User, user_id)
    if not m:
        db.close()
        return
    path = Path(m.file_path)
    try:
        _step(db, m, "upload", "done", f"{m.filename} received", "processing")
        _step(db, m, "validate", "done", f"{m.mime_type}, {m.size_bytes / 1024 / 1024:.2f} MB — signature, size and type checked")
        _step(db, m, "store", "done", "Stored on the server's local disk" + (" (object storage configurable)" if not settings.STORAGE_URL else ""))
        thumb = media_dir("thumbs") / f"{path.stem}.jpg"

        if m.media_type == "image":
            _step(db, m, "metadata", "running", processing_status="extracting_metadata")
            basic, exif = image_metadata(path)
            m.width, m.height = basic["width"], basic["height"]
            _step(db, m, "metadata", "done", f"{basic['format']} {basic['width']}×{basic['height']} ({basic['mode']})")
            image_thumbnail(path, thumb)
            m.thumbnail_path = str(thumb)
            _step(db, m, "thumbnail", "done", "640 px JPEG preview")
            if exif:
                m.exif = exif
                m.captured_at = m.captured_at or _exif_datetime(exif)
                if "gps_latitude" in exif and m.latitude is None:
                    m.latitude, m.longitude = exif["gps_latitude"], exif["gps_longitude"]
                _step(db, m, "exif", "done", ", ".join(f"{k.replace('_', ' ')}" for k in list(exif)[:6]))
            else:
                _step(db, m, "exif", "skipped", "No EXIF block in this file")
        else:
            if not ffmpeg_available():
                for k in ("thumbnail", "metadata", "audio"):
                    _step(db, m, k, "skipped", "ffmpeg/ffprobe not installed on this server")
                info = {"has_audio": False}
            else:
                _step(db, m, "metadata", "running", processing_status="extracting_metadata")
                info = probe(path)
                m.duration_seconds = round(info["duration"], 2) if info["duration"] else None
                m.width, m.height = info["width"], info["height"]
                if m.duration_seconds:
                    m.duration = f"{int(m.duration_seconds // 60)}:{int(m.duration_seconds % 60):02d}"
                m.exif = {k: v for k, v in info.items() if v not in (None, "")}
                if info.get("creation_time") and not m.captured_at:
                    try:
                        m.captured_at = datetime.fromisoformat(info["creation_time"].replace("Z", "+00:00"))
                    except ValueError:
                        pass
                loc = _iso6709(info.get("location"))
                if loc and m.latitude is None:
                    m.latitude, m.longitude = loc
                at = min(1.0, (info["duration"] or 2) / 2)
                res = _run(["ffmpeg", "-y", "-v", "error", "-ss", f"{at:.2f}", "-i", str(path), "-frames:v", "1",
                            "-vf", "scale=640:-2", str(thumb)], 60)
                if res.returncode == 0 and thumb.exists():
                    m.thumbnail_path = str(thumb)
                    _step(db, m, "thumbnail", "done", f"Frame at {at:.1f} s")
                else:
                    _step(db, m, "thumbnail", "failed", "Could not extract a frame")
                _step(db, m, "metadata", "done", f"{info['video_codec']} {info['width']}×{info['height']}, "
                      f"{m.duration or '?'} min, audio: {info['audio_codec'] or 'none'}")
            audio = media_dir("audio") / f"{path.stem}.wav"
            audio_ok = False
            if info.get("has_audio") and ffmpeg_available():
                res = _run(["ffmpeg", "-y", "-v", "error", "-i", str(path), "-vn", "-ac", "1", "-ar", "16000",
                            "-t", "900", str(audio)], 300)
                audio_ok = res.returncode == 0 and audio.exists()
                _step(db, m, "audio", "done" if audio_ok else "failed",
                      "16 kHz mono WAV (first 15 min)" if audio_ok else "Audio extraction failed")
            elif ffmpeg_available():
                _step(db, m, "audio", "skipped", "No audio track")

            _step(db, m, "transcript", "running", processing_status="generating_transcript")
            if transcript_path:
                m.transcript = parse_transcript(Path(transcript_path).read_text(encoding="utf-8", errors="replace"))
                m.transcript_source = "uploaded"
                _step(db, m, "transcript", "done", f"Uploaded transcript — {len(m.transcript.split())} words")
            elif audio_ok and settings.stt_enabled:
                try:
                    m.transcript = transcribe(audio)[:200_000]
                    m.transcript_source = f"stt:{settings.STT_MODEL}"
                    _step(db, m, "transcript", "done", f"Speech-to-text ({settings.STT_MODEL}) — {len(m.transcript.split())} words")
                except Exception as exc:  # STT is optional — the video is still indexed by its metadata
                    log.warning("speech-to-text failed: %s", exc)
                    _step(db, m, "transcript", "failed", "Speech-to-text service unavailable — indexed without transcript")
            else:
                reason = ("No speech-to-text service configured" if audio_ok else "No audio to transcribe")
                _step(db, m, "transcript", "skipped", f"{reason}. Attach a .vtt/.srt/.txt transcript to make speech searchable.")
            if audio.exists():
                audio.unlink(missing_ok=True)  # derived file; the original video is kept

        _step(db, m, "associate", "done", _associate(db, m, links))
        _step(db, m, "searchable", "done", _searchable(m))
        _step(db, m, "index", "running", processing_status="indexing")
        index_resource(db, "media", m.id)
        _step(db, m, "index", "done", "Full-text + vector index updated")
        ensure_for(db, "media", m)
        m.processing_status = "ready"
        _step(db, m, "ready", "done", "Searchable in the repository", "ready")
        audit(db, user, "upload", "media", m.slug, f"Ingested {m.media_type} {m.filename}")
        if user:
            notify(db, "Media processing completed", f"“{m.title}” is indexed and searchable.", f"/media/{m.slug}",
                   "success", user_id=user.id)
    except Exception as exc:
        log.exception("media ingestion failed")
        db.rollback()
        m = db.get(Media, media_id)
        steps = [dict(s) for s in (m.processing_steps or [])]
        for s in steps:
            if s["status"] in {"running", "pending"}:
                s["status"] = "failed" if s["status"] == "running" else "skipped"
        m.processing_steps, m.processing_status = steps, "failed"
        m.processing_error = str(exc) if isinstance(exc, MediaValidationError) else "Processing failed. Check the file and retry."
        db.commit()
        audit(db, user, "upload", "media", m.slug, m.processing_error, status="failure")
    finally:
        db.close()


def new_media_paths(filename: str) -> tuple[str, Path]:
    safe = safe_filename(filename)
    return safe, media_dir("originals") / f"{uuid.uuid4().hex[:12]}-{safe}"
