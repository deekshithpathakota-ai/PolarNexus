"""Model -> JSON helpers shared by the API routers."""
from __future__ import annotations

from datetime import date, datetime

from app.auth.security import ROLE_INFO, permissions_for
from app.models import Dataset, Document, Expedition, GeneratedContent, Media, Researcher, Station, User


def iso(v: datetime | date | None) -> str | None:
    return v.isoformat() if v else None


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
    }


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
        "excerpt": c.body[:220],
    }
    if full:
        out["body"] = c.body
        out["evidence_check"] = c.evidence_check
        out["citations"] = [{"n": x.position, "chunk_id": x.chunk_id, "resource_type": x.resource_type,
                             "resource_id": x.resource_id, "slug": x.resource_slug, "label": x.label,
                             "section": x.section, "quote": x.quote,
                             "url": f"/resources/{x.resource_slug}" if x.resource_type == "document" and x.resource_slug
                             else (f"/datasets/{x.resource_slug}" if x.resource_type == "dataset" else None)}
                            for x in c.citations]
        out["history"] = [{"action": r.action, "comment": r.comment, "by": r.reviewer_name, "at": iso(r.created_at)}
                          for r in c.reviews]
    return out
