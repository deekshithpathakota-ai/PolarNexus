"""Visual semantic search: text → photographs and video frames in a shared CLIP embedding space.

    Image ─► validate ─► metadata ─► thumbnail ─► CLIP image embedding ─► visual_embeddings ─► search
    Video ─► representative key frames (scene changes + even sampling, capped) ─► CLIP embeddings with timestamps
    Query ─► CLIP text embedding ─► cosine similarity ─► best frame per media item ─► ranked media (+ timestamp)

The provider is CLIP ViT-B/32 run through ONNX Runtime by the optional `fastembed` package (no PyTorch, CPU only).
When it is not installed or cannot load, visual search reports itself as unavailable and the existing
metadata/transcript search keeps working — nothing is faked.
"""
from __future__ import annotations

import logging
import math
import re
import shutil
import subprocess
import threading
from pathlib import Path

import numpy as np
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Media, VisualEmbedding

log = logging.getLogger("polarnexus.visual")

_lock = threading.Lock()
_state: dict = {"image": None, "text": None, "error": None, "tried": False}
_cache: dict[str, tuple[np.ndarray, list[int], list[float | None], list[str]]] = {}


def _mode() -> str:
    return (settings.VISUAL_SEARCH_PROVIDER or "auto").lower()


def model_name() -> str:
    return f"clip:{settings.VISUAL_IMAGE_MODEL}"


def installed() -> bool:
    try:
        import fastembed  # noqa: F401
        return True
    except Exception:
        return False


def _load() -> bool:
    if _state["image"] is not None:
        return True
    if _mode() == "none":
        _state["error"] = "Disabled (VISUAL_SEARCH_PROVIDER=none)."
        return False
    with _lock:
        if _state["image"] is not None:
            return True
        if _state["tried"] and _state["error"]:
            return False
        _state["tried"] = True
        try:
            from fastembed import ImageEmbedding, TextEmbedding

            Path(settings.VISUAL_MODEL_CACHE).mkdir(parents=True, exist_ok=True)
            _state["image"] = ImageEmbedding(settings.VISUAL_IMAGE_MODEL, cache_dir=settings.VISUAL_MODEL_CACHE)
            _state["text"] = TextEmbedding(settings.VISUAL_TEXT_MODEL, cache_dir=settings.VISUAL_MODEL_CACHE)
            _state["error"] = None
            log.info("visual search ready: %s", settings.VISUAL_IMAGE_MODEL)
            return True
        except ImportError:
            _state["error"] = "The optional 'fastembed' package is not installed (pip install -r requirements-visual.txt)."
        except Exception as exc:  # model download blocked, corrupt cache, unsupported CPU…
            _state["error"] = f"CLIP model could not be loaded: {exc.__class__.__name__}: {str(exc)[:160]}"
            log.warning("visual search unavailable: %s", _state["error"])
        _state["image"] = _state["text"] = None
        return False


def available() -> bool:
    if _mode() == "none":
        return False
    if _mode() == "auto" and not installed():
        return False
    return _load()


def reset_for_tests() -> None:
    _state.update(image=None, text=None, error=None, tried=False)
    _cache.clear()


def status(db: Session | None = None) -> dict:
    mode = _mode()
    if mode == "none":
        return {"enabled": False, "provider": "none", "reason": "Disabled (VISUAL_SEARCH_PROVIDER=none)."}
    if not installed():
        return {"enabled": False, "provider": "clip", "model": settings.VISUAL_IMAGE_MODEL,
                "reason": "Optional 'fastembed' package not installed — visual search falls back to metadata, captions and transcripts."}
    out = {"enabled": _state["image"] is not None or (not _state["tried"]), "provider": "clip (fastembed / ONNX Runtime)",
           "model": settings.VISUAL_IMAGE_MODEL, "text_model": settings.VISUAL_TEXT_MODEL,
           "loaded": _state["image"] is not None, "reason": _state["error"]}
    if _state["error"]:
        out["enabled"] = False
    if db is not None:
        out["indexed_vectors"] = db.query(VisualEmbedding).filter(VisualEmbedding.model == model_name()).count()
        out["indexed_media"] = db.query(VisualEmbedding.media_id).filter(VisualEmbedding.model == model_name()).distinct().count()
    return out


def _norm(v) -> list[float]:
    a = np.asarray(v, dtype=np.float32)
    n = float(np.linalg.norm(a)) or 1.0
    return (a / n).tolist()


def embed_images(paths: list[Path]) -> list[list[float]]:
    if not _load():
        raise RuntimeError(_state["error"] or "Visual search unavailable.")
    return [_norm(v) for v in _state["image"].embed([str(p) for p in paths], batch_size=8)]


def embed_text(query: str) -> list[float]:
    if not _load():
        raise RuntimeError(_state["error"] or "Visual search unavailable.")
    return _norm(next(iter(_state["text"].embed([query]))))


# ------------------------------------------------------------------ video key frames
def _ffmpeg() -> bool:
    return bool(shutil.which("ffmpeg"))


def frames_dir() -> Path:
    d = Path(settings.STORAGE_DIR) / "media" / "frames"
    d.mkdir(parents=True, exist_ok=True)
    return d


def extract_keyframes(path: Path, duration: float | None, stem: str) -> list[tuple[float, Path]]:
    """Representative frames: scene-change frames plus even sampling, never more than VIDEO_MAX_KEYFRAMES."""
    if not _ffmpeg():
        return []
    cap = max(1, settings.VIDEO_MAX_KEYFRAMES)
    out_dir = frames_dir()
    times: list[float] = []
    # 1) scene changes (ffmpeg's scene score) — timestamps parsed from showinfo
    res = subprocess.run(["ffmpeg", "-v", "info", "-i", str(path), "-vf", "select='gt(scene,0.35)',showinfo", "-an",
                          "-f", "null", "-"], capture_output=True, timeout=300, check=False)
    for m in re.finditer(rb"pts_time:([0-9.]+)", res.stderr or b""):
        times.append(round(float(m.group(1)), 2))
    # 2) even sampling so long static shots are also represented
    dur = float(duration or 0)
    if dur > 0:
        n = min(cap, max(3, math.ceil(dur / 8)))
        times += [round(dur * (i + 0.5) / n, 2) for i in range(n)]
    else:
        times.append(0.5)
    picked: list[float] = []
    for t in sorted(set(times)):
        if all(abs(t - p) >= 1.5 for p in picked):
            picked.append(t)
    if len(picked) > cap:  # keep an even spread
        step = len(picked) / cap
        picked = [picked[int(i * step)] for i in range(cap)]
    frames = []
    for t in picked:
        fp = out_dir / f"{stem}_{int(t * 100):07d}.jpg"
        r = subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", f"{t:.2f}", "-i", str(path), "-frames:v", "1",
                            "-vf", "scale=448:-2", str(fp)], capture_output=True, timeout=60, check=False)
        if r.returncode == 0 and fp.exists():
            frames.append((t, fp))
    return frames


# ------------------------------------------------------------------ indexing
def _source_image(m: Media) -> Path | None:
    for p in (m.file_path, m.thumbnail_path):
        if p and Path(p).is_file():
            return Path(p)
    return None


def index_media(db: Session, m: Media) -> dict:
    """(Re)builds the visual vectors of one media item. Returns {status, vectors, detail}."""
    if not available():
        m.visual_status = "skipped"
        db.commit()
        return {"status": "skipped", "vectors": 0, "detail": status().get("reason") or "Visual search unavailable"}
    db.execute(delete(VisualEmbedding).where(VisualEmbedding.media_id == m.id))
    rows: list[VisualEmbedding] = []
    try:
        if m.media_type == "video":
            src = Path(m.file_path) if m.file_path and Path(m.file_path).is_file() else None
            frames = extract_keyframes(src, m.duration_seconds, Path(m.file_path).stem) if src else []
            if not frames:
                img = _source_image(m) if not src else None
                if m.thumbnail_path and Path(m.thumbnail_path).is_file():
                    frames = [(None, Path(m.thumbnail_path))]
                elif img:
                    frames = [(None, img)]
            if frames:
                vecs = embed_images([f for _, f in frames])
                rows = [VisualEmbedding(media_id=m.id, frame_seconds=t, frame_path=str(f), model=model_name(), embedding=v)
                        for (t, f), v in zip(frames, vecs)]
            detail = f"{len(rows)} key frame(s) embedded" if rows else "No frames could be extracted"
        else:
            src = _source_image(m)
            if src:
                rows = [VisualEmbedding(media_id=m.id, frame_seconds=None, frame_path="", model=model_name(),
                                        embedding=embed_images([src])[0])]
            detail = "Image embedded (CLIP ViT-B/32)" if rows else "No image file to embed (illustrative artwork)"
    except Exception as exc:
        log.warning("visual indexing failed for %s: %s", m.slug, exc)
        db.rollback()
        m = db.get(Media, m.id)
        m.visual_status = "failed"
        db.commit()
        return {"status": "failed", "vectors": 0, "detail": f"Visual embedding failed: {exc.__class__.__name__}"}
    db.add_all(rows)
    m.visual_status = "indexed" if rows else "skipped"
    db.commit()
    _cache.clear()
    return {"status": m.visual_status, "vectors": len(rows), "detail": detail}


def reindex_all(db: Session) -> dict:
    n_media = n_vec = 0
    for m in db.scalars(select(Media).where(Media.file_path != "")):
        r = index_media(db, m)
        if r["vectors"]:
            n_media += 1
            n_vec += r["vectors"]
    return {"media": n_media, "vectors": n_vec, "model": model_name()}


def _matrix(db: Session):
    key = model_name()
    if key not in _cache:
        rows = db.execute(select(VisualEmbedding.media_id, VisualEmbedding.frame_seconds, VisualEmbedding.embedding,
                                 VisualEmbedding.frame_path).where(VisualEmbedding.model == key)).all()
        mat = np.asarray([r[2] for r in rows], dtype=np.float32) if rows else np.zeros((0, 1), dtype=np.float32)
        _cache[key] = (mat, [r[0] for r in rows], [r[1] for r in rows], [r[3] for r in rows])
    return _cache[key]


def search(db: Session, query: str, k: int = 30, min_similarity: float | None = None) -> list[dict]:
    """Best-matching frame per media item, best first: [{media_id, similarity, frame_seconds, frame_index}]."""
    if not query.strip() or not available():
        return []
    mat, mids, secs, paths = _matrix(db)
    if not len(mids):
        return []
    q = np.asarray(embed_text(query), dtype=np.float32)
    sims = mat @ q
    best: dict[int, tuple[float, int]] = {}
    for i, s in enumerate(sims):
        mid = mids[i]
        if mid not in best or s > best[mid][0]:
            best[mid] = (float(s), i)
    ranked = sorted(best.items(), key=lambda kv: -kv[1][0])
    if not ranked:
        return []
    top = ranked[0][1][0]
    floor = settings.VISUAL_MIN_SIMILARITY if min_similarity is None else min_similarity
    out = []
    for mid, (s, i) in ranked[:k]:
        # CLIP similarities are compressed (~0.15–0.35); keep items near the best match and above a calibrated floor
        if s < floor or s < top - 0.04:
            continue
        frame_index = None
        if paths[i]:
            ordered = sorted(secs[j] or 0.0 for j in range(len(mids)) if mids[j] == mid and paths[j])
            frame_index = ordered.index(secs[i] or 0.0)
        out.append({"media_id": mid, "similarity": round(s, 4), "frame_seconds": secs[i],
                    "frame_index": frame_index, "timestamp": fmt_ts(secs[i])})
    return out


def fmt_ts(seconds: float | None) -> str | None:
    if seconds is None:
        return None
    s = int(round(seconds))
    return f"{s // 60:02d}:{s % 60:02d}"
