"""Duplicate detection for uploads.

Signals, strongest first: identical content hash, identical DOI / identifier, near-identical title or file name,
overlapping text (word-shingle Jaccard). Each candidate is reported with the signals that fired and a similarity
percentage. Nothing is ever merged or deleted automatically — the uploader chooses Keep both / Update existing /
Review / Cancel.
"""
from __future__ import annotations

import hashlib
import re
from difflib import SequenceMatcher
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Dataset, Document, Media
from app.utils.text import normalize

DOI_RE = re.compile(r"\b(10\.\d{4,9}/[-._;()/:A-Za-z0-9]+[A-Za-z0-9])")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def find_doi(text: str) -> str:
    m = DOI_RE.search(text or "")
    return m.group(1).rstrip(".").lower() if m else ""


def _ratio(a: str, b: str) -> float:
    a, b = normalize(a or ""), normalize(b or "")
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def _shingles(text: str, k: int = 5) -> set[str]:
    words = normalize(text or "").split()[:2500]
    return {" ".join(words[i:i + k]) for i in range(max(0, len(words) - k + 1))}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _stem_name(name: str) -> str:
    stem = Path(name or "").stem.lower()
    stem = re.sub(r"^[0-9a-f]{10,12}-", "", stem)  # storage prefix added on upload
    return re.sub(r"[^a-z0-9]+", " ", stem).strip()


def check_document(db: Session, *, content_hash: str = "", title: str = "", filename: str = "", text: str = "",
                   doi: str = "", exclude_id: int | None = None, limit: int = 5) -> list[dict]:
    doi = (doi or find_doi(text[:20000])).lower()
    sh = _shingles(text) if text else set()
    out = []
    for d in db.scalars(select(Document)):
        if exclude_id and d.id == exclude_id:
            continue
        signals, score = [], 0.0
        if content_hash and d.content_hash and d.content_hash == content_hash:
            signals.append("Identical file (content hash)")
            score = 1.0
        d_doi = (d.doi or find_doi((d.content or "")[:20000])).lower()
        if doi and d_doi and doi == d_doi:
            signals.append(f"Same DOI ({doi})")
            score = max(score, 0.98)
        t = _ratio(title, d.title) if title else 0.0
        if t >= 0.85:
            signals.append(f"Very similar title ({round(t * 100)}%)")
            score = max(score, t * 0.95)
        f = _ratio(_stem_name(filename), _stem_name(d.file_name)) if filename and d.file_name else 0.0
        if f >= 0.9:
            signals.append(f"Same file name ({round(f * 100)}%)")
            score = max(score, 0.6 + 0.3 * f)
        if sh and len(sh) > 20:
            j = _jaccard(sh, _shingles(d.content or d.abstract))
            if j >= 0.3:
                signals.append(f"Overlapping text ({round(j * 100)}% shared passages)")
                score = max(score, 0.5 + 0.5 * j)
        if signals:
            out.append({"type": "document", "id": d.id, "slug": d.slug, "title": d.title, "url": f"/resources/{d.slug}",
                        "similarity": round(score * 100), "signals": signals, "year": d.year,
                        "file_name": d.file_name, "status": d.status})
    out.sort(key=lambda x: -x["similarity"])
    return out[:limit]


def check_dataset(db: Session, *, content_hash: str = "", title: str = "", filename: str = "", doi: str = "",
                  columns: list[str] | None = None, exclude_id: int | None = None, limit: int = 5) -> list[dict]:
    out = []
    cols = {normalize(c) for c in (columns or [])}
    for ds in db.scalars(select(Dataset)):
        if exclude_id and ds.id == exclude_id:
            continue
        signals, score = [], 0.0
        if content_hash and ds.content_hash and ds.content_hash == content_hash:
            signals.append("Identical file (content hash)")
            score = 1.0
        if doi and ds.doi and doi.lower() == ds.doi.lower():
            signals.append(f"Same DOI ({doi})")
            score = max(score, 0.98)
        t = _ratio(title, ds.title) if title else 0.0
        if t >= 0.85:
            signals.append(f"Very similar title ({round(t * 100)}%)")
            score = max(score, t * 0.9)
        if filename and ds.file_path and _ratio(_stem_name(filename), _stem_name(ds.file_path)) >= 0.92:
            signals.append("Same file name")
            score = max(score, 0.75)
        if cols and ds.columns_schema:
            other = {normalize(c.get("name", "")) for c in ds.columns_schema}
            j = _jaccard(cols, other)
            if j >= 0.8 and len(cols) >= 3 and t >= 0.5:
                signals.append(f"Same columns ({round(j * 100)}%) and similar title")
                score = max(score, 0.55 + 0.3 * j)
        if signals:
            out.append({"type": "dataset", "id": ds.id, "slug": ds.slug, "title": ds.title, "url": f"/datasets/{ds.slug}",
                        "similarity": round(score * 100), "signals": signals, "year": ds.year, "status": ds.status})
    out.sort(key=lambda x: -x["similarity"])
    return out[:limit]


def check_media(db: Session, *, content_hash: str = "", title: str = "", filename: str = "",
                exclude_id: int | None = None, limit: int = 5) -> list[dict]:
    out = []
    for m in db.scalars(select(Media)):
        if exclude_id and m.id == exclude_id:
            continue
        signals, score = [], 0.0
        if content_hash and m.content_hash and m.content_hash == content_hash:
            signals.append("Identical file (content hash)")
            score = 1.0
        t = _ratio(title, m.title) if title else 0.0
        if t >= 0.9:
            signals.append(f"Very similar title ({round(t * 100)}%)")
            score = max(score, t * 0.8)
        if filename and m.filename and _ratio(_stem_name(filename), _stem_name(m.filename)) >= 0.95:
            signals.append("Same file name")
            score = max(score, 0.7)
        if signals:
            out.append({"type": "media", "id": m.id, "slug": m.slug, "title": m.title, "url": f"/media/{m.slug}",
                        "similarity": round(score * 100), "signals": signals, "year": m.year})
    out.sort(key=lambda x: -x["similarity"])
    return out[:limit]


def count_candidates(db: Session) -> int:
    """Admin data-quality metric: records that share a content hash, DOI or a near-identical title."""
    n = 0
    docs = list(db.scalars(select(Document)))
    seen_hash: dict[str, int] = {}
    for d in docs:
        if d.content_hash:
            seen_hash[d.content_hash] = seen_hash.get(d.content_hash, 0) + 1
    n += sum(c - 1 for c in seen_hash.values() if c > 1)
    titles = [normalize(d.title) for d in docs]
    for i in range(len(titles)):
        for j in range(i + 1, len(titles)):
            if titles[i] and SequenceMatcher(None, titles[i], titles[j]).ratio() >= 0.93:
                n += 1
    return n
