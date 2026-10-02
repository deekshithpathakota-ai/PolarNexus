"""FAIR-oriented scientific metadata.

Assembles a Dublin Core / DataCite-inspired metadata record from what the repository actually holds (the record
itself, its provenance row and linked researchers/topics). Missing values are returned as null and listed under
`missing` — nothing is guessed or generated. ORCID iDs are shown only when one has been stored for a researcher.
"""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy.orm import Session

from app.services import provenance as prov
from app.services.catalog import Catalog

FIELDS = [
    # key, label, Dublin Core term, required-for-completeness
    ("title", "Title", "dc:title", True),
    ("creator", "Creator", "dc:creator", True),
    ("contributor", "Contributor", "dc:contributor", False),
    ("subject", "Subject", "dc:subject", True),
    ("description", "Description", "dc:description", True),
    ("publisher", "Publisher", "dc:publisher", True),
    ("date", "Date", "dc:date", True),
    ("type", "Type", "dc:type", True),
    ("format", "Format", "dc:format", False),
    ("identifier", "Identifier", "dc:identifier", True),
    ("doi", "DOI", "datacite:doi", False),
    ("source", "Source", "dc:source", True),
    ("language", "Language", "dc:language", True),
    ("rights", "Rights / licence", "dc:rights", True),
    ("version", "Version", "datacite:version", False),
    ("spatial", "Spatial coverage", "dcterms:spatial", True),
    ("temporal", "Temporal coverage", "dcterms:temporal", False),
]

RESOURCE_TYPE = {"document": "Text", "dataset": "Dataset", "media": "Image", "expedition": "Event",
                 "station": "PhysicalObject", "researcher": "Agent", "activity": "Event"}


def _iso(v):
    if isinstance(v, (date, datetime)):
        return v.isoformat()[:10]
    return v


def _nz(v):
    if v in (None, "", [], {}):
        return None
    return v


def build(db: Session, cat: Catalog, rtype: str, obj, version: int | None = None) -> dict:
    p = prov.get_provenance(db, rtype, obj)
    card = cat.card(rtype, obj.id) or {}
    people = [r for r in cat.related(rtype, obj.id, {"researcher"})]
    v: dict = {k: None for k, *_ in FIELDS}
    v["title"] = card.get("title") or getattr(obj, "title", None) or getattr(obj, "name", None)
    v["subject"] = _nz(card.get("topics") or getattr(obj, "keywords", None) or getattr(obj, "tags", None))
    v["identifier"] = f"polarnexus:{rtype}/{obj.slug}"
    v["type"] = RESOURCE_TYPE.get(rtype, rtype)
    v["source"] = _nz(p.get("source_url")) or _nz(getattr(obj, "source_url", "")) or _nz(p.get("source_organisation"))
    v["rights"] = _nz(getattr(obj, "license", "")) or _nz(p.get("license"))
    v["language"] = _nz(getattr(obj, "language", "")) or ("en" if rtype in {"document", "dataset"} else None)
    v["version"] = version
    v["publisher"] = _nz(getattr(obj, "publisher", "")) or _nz(p.get("source_organisation"))
    v["date"] = _iso(p.get("publication_date")) or (str(obj.year) if getattr(obj, "year", None) else None)
    v["doi"] = _nz(getattr(obj, "doi", ""))
    contributors = [{"name": r["title"], "orcid": None, "profile": r["url"]} for r in people]
    if rtype == "document":
        v["creator"] = _nz([{"name": a, "orcid": None} for a in (obj.authors or [])])
        v["description"] = _nz(obj.abstract)
        v["format"] = ("application/pdf" if (obj.file_name or "").lower().endswith(".pdf") else
                       "text/markdown" if (obj.file_name or "").lower().endswith(".md") else None)
        v["spatial"] = _nz(obj.region)
        v["temporal"] = str(obj.year) if obj.year else None
    elif rtype == "dataset":
        v["creator"] = _nz([{"name": obj.creator, "orcid": None}] if obj.creator else None)
        v["description"] = _nz(obj.description)
        v["format"] = _nz(obj.format)
        v["spatial"] = _nz(obj.spatial_coverage) or _nz(obj.region)
        if obj.temporal_start or obj.temporal_end:
            v["temporal"] = f"{_iso(obj.temporal_start) or '?'}/{_iso(obj.temporal_end) or '?'}"
    elif rtype == "media":
        v["creator"] = _nz([{"name": obj.credit, "orcid": None}] if obj.credit else None)
        v["description"] = _nz(obj.description)
        v["format"] = _nz(obj.mime_type)
        v["type"] = "MovingImage" if obj.media_type == "video" else "StillImage"
        v["spatial"] = (f"{obj.location or obj.region} ({obj.latitude:.4f}, {obj.longitude:.4f})"
                        if obj.latitude is not None and obj.longitude is not None else _nz(obj.location) or _nz(obj.region))
        v["temporal"] = _iso(obj.captured_at) or (str(obj.year) if obj.year else None)
    elif rtype == "expedition":
        v["description"] = _nz(obj.objective)
        v["spatial"] = _nz(obj.region)
        v["temporal"] = _nz(obj.season)
    elif rtype == "station":
        v["description"] = _nz(obj.description)
        v["spatial"] = f"{obj.location_name} ({obj.latitude:.4f}, {obj.longitude:.4f})"
        v["temporal"] = _nz(obj.established)
    elif rtype == "researcher":
        v["creator"] = [{"name": obj.name, "orcid": _nz(obj.orcid)}]
        v["description"] = _nz(obj.bio)
    elif rtype == "activity":
        v["description"] = _nz(obj.description)
        v["spatial"] = _nz(obj.location)
        v["temporal"] = _iso(obj.date)
    if contributors and rtype not in {"researcher"}:
        v["contributor"] = contributors
    rows, missing = [], []
    required = [k for k, _, _, req in FIELDS if req]
    for key, label, term, req in FIELDS:
        val = _nz(v.get(key))
        rows.append({"key": key, "label": label, "term": term, "value": val, "required": req})
        if val is None and req:
            missing.append(label)
    present = sum(1 for k in required if _nz(v.get(k)) is not None)
    return {
        "standard": "Dublin Core (DCMI Terms) with DataCite-style DOI/version fields",
        "fields": rows,
        "missing": missing,
        "completeness": round(present / len(required), 2),
        "verification": {"status": p["verification_status"], "label": p["verification_label"], "is_demo": p["is_demo"]},
        "orcid_note": "ORCID iDs are displayed only when a real iD has been recorded; none are inferred.",
        "dublin_core": {term: _nz(v.get(key)) for key, _, term, _ in FIELDS},
    }


def missing_metadata_count(db: Session, cat: Catalog) -> dict:
    """Admin data-quality metric: resources whose FAIR record lacks any required field."""
    from app.models import RESOURCE_MODELS

    out = {"resources_missing_required": 0, "by_field": {}}
    for rtype in ("document", "dataset", "media"):
        model = RESOURCE_MODELS[rtype]
        for obj in db.query(model).all():
            if not cat.card(rtype, obj.id):
                continue
            rec = build(db, cat, rtype, obj)
            if rec["missing"]:
                out["resources_missing_required"] += 1
                for f in rec["missing"]:
                    out["by_field"][f] = out["by_field"].get(f, 0) + 1
    return out
