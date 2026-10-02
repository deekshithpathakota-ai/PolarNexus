"""Append-only resource version history.

Every meaningful change (import, metadata correction, new file, verification change) appends a row with a snapshot
of the record's descriptive fields at that moment. Rows are never updated or deleted, so earlier versions stay
readable even after the live record changes.
"""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import ResourceVersion, User

SNAPSHOT_FIELDS = {
    "document": ["title", "doc_type", "abstract", "authors", "institution", "region", "year", "language", "keywords",
                 "source", "doi", "license", "publisher", "source_url", "file_name", "page_count", "visibility",
                 "status", "content_hash", "ocr_status"],
    "dataset": ["title", "description", "region", "data_type", "temporal_start", "temporal_end", "spatial_coverage",
                "variables", "source", "format", "license", "record_count", "year", "keywords", "doi", "creator",
                "source_url", "content_hash", "visibility", "status"],
    "media": ["title", "description", "media_type", "category", "region", "year", "credit", "license", "tags",
              "alt_text", "caption", "source_url", "visibility", "status"],
    "expedition": ["name", "season", "year", "objective", "themes", "leader", "vessel"],
    "station": ["name", "location_name", "latitude", "longitude", "established", "status", "description"],
    "researcher": ["name", "title", "institution", "expertise", "orcid"],
    "activity": ["title", "description", "activity_type", "date", "location", "organisation", "status", "visibility"],
}


def _jsonable(v):
    if isinstance(v, (date, datetime)):
        return v.isoformat()
    return v


def snapshot(rtype: str, obj) -> dict:
    return {f: _jsonable(getattr(obj, f, None)) for f in SNAPSHOT_FIELDS.get(rtype, []) if hasattr(obj, f)}


def record(db: Session, rtype: str, obj, change: str, status: str = "", user: User | None = None,
           user_name: str = "", commit: bool = True) -> ResourceVersion:
    n = db.scalar(select(func.max(ResourceVersion.version)).where(
        ResourceVersion.resource_type == rtype, ResourceVersion.resource_id == obj.id)) or 0
    row = ResourceVersion(resource_type=rtype, resource_id=obj.id, version=n + 1, change=change[:300], status=status,
                          user_id=user.id if user else None, user_name=(user.name if user else user_name) or "System",
                          snapshot=snapshot(rtype, obj))
    db.add(row)
    if commit:
        db.commit()
    return row


def history(db: Session, rtype: str, rid: int) -> list[dict]:
    rows = db.scalars(select(ResourceVersion).where(ResourceVersion.resource_type == rtype,
                                                    ResourceVersion.resource_id == rid)
                      .order_by(ResourceVersion.version.desc())).all()
    out = []
    for i, r in enumerate(rows):
        prev = rows[i + 1].snapshot if i + 1 < len(rows) else {}
        changed = sorted(k for k in (r.snapshot or {}) if prev and (r.snapshot or {}).get(k) != prev.get(k))
        out.append({"version": r.version, "change": r.change, "status": r.status, "user": r.user_name,
                    "date": r.created_at.isoformat() if r.created_at else None, "changed_fields": changed,
                    "snapshot": r.snapshot})
    return out


def ensure_baseline(db: Session) -> int:
    """Gives every existing resource a 'Version 1 — Imported' row (once). Idempotent; used by the v3 upgrade."""
    from app.services.provenance import MODELS, default_provenance

    have = {(t, i) for t, i in db.execute(select(ResourceVersion.resource_type, ResourceVersion.resource_id).distinct())}
    n = 0
    for rtype, model in MODELS.items():
        for obj in db.scalars(select(model)):
            if (rtype, obj.id) in have:
                continue
            status = default_provenance(rtype, obj)["verification_status"]
            label = "Imported (demonstration record)" if status in {"demo_data", "synthetic_demo"} else "Imported"
            row = ResourceVersion(resource_type=rtype, resource_id=obj.id, version=1, change=label, status=status,
                                  user_name="Seed / migration", snapshot=snapshot(rtype, obj))
            if getattr(obj, "created_at", None):
                row.created_at = obj.created_at
            db.add(row)
            n += 1
    if n:
        db.commit()
    return n
