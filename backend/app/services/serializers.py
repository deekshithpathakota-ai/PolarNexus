"""Model -> JSON helpers shared by the API routers."""
from __future__ import annotations

from datetime import date, datetime

from app.auth.security import ROLE_INFO, permissions_for
from app.models import (
    Dataset,
    Document,
    Expedition,
    GeneratedContent,
    InstitutionalActivity,
    Media,
    Researcher,
    Station,
    User,
)
from app.services.catalog import ACTIVITY_TYPES
from app.services.provenance import content_provenance, provenance_out

# Channels: the website feed is a real, live dissemination channel of this deployment. Social/newsletter
# channels have connector code paths but no live API credentials — publishing to them is a labelled simulation.
CHANNELS = {
    "website": {"label": "Website (Outreach Feed)", "status": "live", "note": "Published to this deployment's public Outreach Feed."},
    "linkedin": {"label": "LinkedIn", "status": "connector_ready", "note": "Prototype simulation — no LinkedIn API credentials configured."},
    "instagram": {"label": "Instagram", "status": "connector_ready", "note": "Prototype simulation — no Instagram API credentials configured."},
    "newsletter": {"label": "Newsletter", "status": "connector_ready", "note": "Prototype simulation — no mailing service configured."},
}


def iso(v: datetime | date | None) -> str | None:
    return v.isoformat() if v else None


_PREFIX = {"document": "/resources", "dataset": "/datasets", "media": "/media", "expedition": "/expeditions",
           "station": "/stations", "researcher": "/researchers", "activity": "/activities"}


def _cite_url(rtype: str, slug: str) -> str | None:
    return f"{_PREFIX[rtype]}/{slug}" if rtype in _PREFIX and slug else None


def user_out(u: User) -> dict:
    return {
        "id": u.id, "email": u.email, "name": u.name, "role": u.role_name,
        "role_label": ROLE_INFO.get(u.role_name, ("User", ""))[0], "institution": u.institution,
        "permissions": permissions_for(u.role_name), "is_demo": u.is_demo,
    }


def document_out(d: Document, include_content: bool = False) -> dict:
    out = {
        "type": "document", "id": d.id, "slug": d.slug, "title": d.title, "doc_type": d.doc_type,
        "abstract": d.abstract, "authors": d.authors, "institution": d.institution, "region": d.region,
        "year": d.year, "language": d.language, "keywords": d.keywords, "source": d.source,
        "file_name": d.file_name, "page_count": d.page_count, "status": d.status, "visibility": d.visibility,
        "is_demo": d.is_demo, "views": d.views, "created_at": iso(d.created_at), "updated_at": iso(d.updated_at),
        "url": f"/resources/{d.slug}",
    }
    if include_content:
        out["sections"] = [{"chunk_id": c.id, "section": c.section, "page": c.page, "text": c.text} for c in d.chunks]
    return out


def dataset_out(d: Dataset) -> dict:
    return {
        "type": "dataset", "id": d.id, "slug": d.slug, "title": d.title, "description": d.description,
        "region": d.region, "data_type": d.data_type, "temporal_start": iso(d.temporal_start),
        "temporal_end": iso(d.temporal_end), "spatial_coverage": d.spatial_coverage, "variables": d.variables,
        "source": d.source, "format": d.format, "license": d.license, "size_label": d.size_label,
        "record_count": d.record_count, "year": d.year, "keywords": d.keywords, "is_demo": d.is_demo,
        "views": d.views, "updated_at": iso(d.updated_at), "url": f"/datasets/{d.slug}",
    }


def media_out(m: Media) -> dict:
    return {
        "type": "media", "id": m.id, "slug": m.slug, "title": m.title, "description": m.description,
        "media_type": m.media_type, "category": m.category, "region": m.region, "year": m.year, "credit": m.credit,
        "license": m.license, "tags": m.tags, "scene": m.scene, "duration": m.duration, "is_demo": m.is_demo,
        "views": m.views, "url": f"/media/{m.slug}",
        # ingestion metadata (v2)
        "status": m.status or "indexed", "filename": m.filename or "", "mime_type": m.mime_type or "",
        "size_bytes": m.size_bytes or 0, "duration_seconds": m.duration_seconds, "width": m.width, "height": m.height,
        "captured_at": iso(m.captured_at), "uploaded_at": iso(m.created_at), "location": m.location or "",
        "latitude": m.latitude, "longitude": m.longitude, "exif": m.exif or {},
        "has_file": bool(m.file_path), "file_url": f"/api/media/{m.slug}/file" if m.file_path else None,
        "thumbnail_url": f"/api/media/{m.slug}/thumbnail" if m.thumbnail_path else None,
        "transcript": m.transcript or "", "transcript_source": m.transcript_source or "",
        "processing_status": m.processing_status or "ready", "processing_steps": m.processing_steps or [],
        "processing_error": m.processing_error or "", "uploaded_by": m.uploaded_by,
    }


def activity_out(a: InstitutionalActivity) -> dict:
    return {
        "type": "activity", "id": a.id, "slug": a.slug, "title": a.title, "description": a.description,
        "activity_type": a.activity_type, "activity_type_label": ACTIVITY_TYPES.get(a.activity_type, a.activity_type),
        "date": iso(a.date), "end_date": iso(a.end_date), "year": a.year, "location": a.location,
        "latitude": a.latitude, "longitude": a.longitude, "region": a.region, "organisation": a.organisation,
        "department": a.department, "audience": a.audience, "outcomes": a.outcomes or [], "status": a.status,
        "visibility": a.visibility, "featured": a.featured, "cover_scene": a.cover_scene, "cover_media_id": a.cover_media_id,
        "is_demo": a.is_demo, "views": a.views, "created_at": iso(a.created_at), "updated_at": iso(a.updated_at),
        "url": f"/activities/{a.slug}",
    }


def channel_status(channels: list[str]) -> list[dict]:
    return [{"channel": ch, **CHANNELS.get(ch, {"label": ch, "status": "connector_ready", "note": "Prototype simulation"})}
            for ch in channels]


def expedition_out(e: Expedition) -> dict:
    return {
        "type": "expedition", "id": e.id, "slug": e.slug, "name": e.name, "title": e.name, "number": e.number,
        "program": e.program, "region": e.region, "season": e.season, "year": e.year, "objective": e.objective,
        "themes": e.themes, "participants": e.participants, "leader": e.leader, "vessel": e.vessel,
        "highlights": e.highlights, "latitude": e.latitude, "longitude": e.longitude,
        "verified_note": e.verified_note, "is_demo": e.is_demo, "views": e.views, "url": f"/expeditions/{e.slug}",
    }


def station_out(s: Station) -> dict:
    return {
        "type": "station", "id": s.id, "slug": s.slug, "name": s.name, "title": s.name, "kind": s.kind,
        "region": s.region, "country": s.country, "location_name": s.location_name, "latitude": s.latitude,
        "longitude": s.longitude, "established": s.established, "status": s.status, "themes": s.themes,
        "description": s.description, "facts_source": s.facts_source, "verified": s.verified, "views": s.views,
        "url": f"/stations/{s.slug}",
    }


def researcher_out(r: Researcher) -> dict:
    return {
        "type": "researcher", "id": r.id, "slug": r.slug, "name": r.name, "title": r.name, "position": r.title,
        "institution": r.institution, "expertise": r.expertise, "bio": r.bio, "is_demo": r.is_demo,
        "url": f"/researchers/{r.slug}",
    }


def content_out(c: GeneratedContent, users: dict[int, User] | None = None, full: bool = True) -> dict:
    users = users or {}
    out = {
        "id": c.id, "title": c.title, "format": c.format, "status": c.status, "generation_mode": c.generation_mode,
        "resource_type": c.resource_type, "resource_id": c.resource_id, "resource_title": c.resource_title,
        "created_by": users[c.created_by].name if c.created_by in users else None,
        "created_by_id": c.created_by,
        "reviewer": users[c.reviewer_id].name if c.reviewer_id in users else None,
        "version": c.version, "channels": c.channels, "is_demo": c.is_demo,
        "created_at": iso(c.created_at), "updated_at": iso(c.updated_at), "submitted_at": iso(c.submitted_at),
        "approved_at": iso(c.approved_at), "published_at": iso(c.published_at),
        "evidence_overall": (c.evidence_check or {}).get("overall"),
        "excerpt": c.body[:220], "audience": c.audience or "", "language": c.language or "English",
        "translated_from": c.translated_from, "channel_status": channel_status(c.channels or []),
    }
    if full:
        out["body"] = c.body
        out["evidence_check"] = c.evidence_check
        out["citations"] = [{"n": x.position, "chunk_id": x.chunk_id, "resource_type": x.resource_type,
                             "resource_id": x.resource_id, "slug": x.resource_slug, "label": x.label,
                             "section": x.section, "page": x.page, "quote": x.quote,
                             "url": _cite_url(x.resource_type, x.resource_slug)}
                            for x in c.citations]
        out["history"] = [{"action": r.action, "comment": r.comment, "by": r.reviewer_name, "at": iso(r.created_at)}
                          for r in c.reviews]
        out["provenance"] = provenance_out(content_provenance(c, users[c.reviewer_id].name if c.reviewer_id in users else None))
    return out
