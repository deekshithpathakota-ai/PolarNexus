"""v2 demo-data extensions: institutional activities, provenance records and the extra search passages.

`seed_activities` is called by the full seed. `upgrade_existing` runs at start-up on a database that was seeded by
an earlier version: it adds the new records WITHOUT resetting or modifying anything that already exists.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    Dataset,
    Document,
    DocumentChunk,
    Expedition,
    GeneratedContent,
    InstitutionalActivity,
    Media,
    Researcher,
    ResourceLink,
    ResourceTopic,
    Station,
    Topic,
)
from app.seed.activities import CITY, activities
from app.services.provenance import ensure_all

log = logging.getLogger("polarnexus.seed")

LINK_FIELDS = [("researchers", Researcher, "researcher", "involves"), ("expeditions", Expedition, "expedition", "related_expedition"),
               ("stations", Station, "station", "held_at"), ("documents", Document, "document", "presents"),
               ("datasets", Dataset, "dataset", "uses_dataset"), ("media", Media, "media", "features_media")]


def seed_activities(db: Session, today: date | None = None) -> int:
    if db.scalar(select(func.count()).select_from(InstitutionalActivity)):
        return 0
    today = today or datetime.now(timezone.utc).date()
    topics = {t.slug: t for t in db.scalars(select(Topic))}
    existing_links = {(l.source_type, l.source_id, l.target_type, l.target_id, l.relation) for l in db.scalars(select(ResourceLink))}
    n = 0
    for spec in activities(today):
        loc, lat, lon, region = CITY[spec["city"]]
        a = InstitutionalActivity(
            slug=spec["slug"], title=spec["title"], description=spec["description"], activity_type=spec["activity_type"],
            date=spec["date"], end_date=spec.get("end_date"), year=spec["date"].year, location=loc, latitude=lat,
            longitude=lon, region=region, organisation=spec["organisation"], department=spec.get("department", ""),
            audience=spec.get("audience", ""), outcomes=spec.get("outcomes", []), status=spec.get("status", "completed"),
            visibility="public", featured=spec.get("featured", False), cover_scene=spec.get("cover_scene", "station"),
            is_demo=True, views=(len(spec["slug"]) * 37) % 400 + 40)
        db.add(a)
        db.flush()
        for field, model, rtype, rel in LINK_FIELDS:
            for slug in spec.get(field, []):
                obj = db.scalar(select(model).where(model.slug == slug))
                key = ("activity", a.id, rtype, obj.id if obj else 0, rel)
                if obj and key not in existing_links:
                    existing_links.add(key)
                    db.add(ResourceLink(source_type="activity", source_id=a.id, target_type=rtype, target_id=obj.id, relation=rel))
        for ts in spec.get("topics", []):
            if ts in topics:
                db.add(ResourceTopic(resource_type="activity", resource_id=a.id, topic_id=topics[ts].id))
        n += 1
    db.commit()
    return n


def link_media_coordinates(db: Session) -> int:
    """Gives seeded media a map position from the station they depict (only when the media has none)."""
    n = 0
    stations = {s.id: s for s in db.scalars(select(Station))}
    for link in db.scalars(select(ResourceLink).where(ResourceLink.source_type == "media", ResourceLink.target_type == "station")):
        m = db.get(Media, link.source_id)
        st = stations.get(link.target_id)
        if m and st and m.latitude is None:
            m.latitude, m.longitude, m.location = st.latitude, st.longitude, m.location or st.location_name
            n += 1
    db.commit()
    return n


def index_new_passages(db: Session) -> int:
    """Embeds passages for resource types introduced in v2 (activities, topics, published outreach) if missing."""
    from app.rag.indexer import index_resource

    have = {(t, i) for t, i in db.execute(select(DocumentChunk.resource_type, DocumentChunk.resource_id)
                                          .where(DocumentChunk.resource_type.in_(["activity", "topic", "content"])))}
    n = 0
    for a in db.scalars(select(InstitutionalActivity)):
        if ("activity", a.id) not in have:
            index_resource(db, "activity", a.id)
            n += 1
    for t in db.scalars(select(Topic)):
        if ("topic", t.id) not in have:
            index_resource(db, "topic", t.id)
            n += 1
    for c in db.scalars(select(GeneratedContent).where(GeneratedContent.status == "published")):
        if ("content", c.id) not in have:
            index_resource(db, "content", c.id)
            n += 1
    return n


def upgrade_existing(db: Session) -> dict:
    """Additive upgrade of a database seeded by v1. Never deletes or edits existing records."""
    out = {"activities": 0, "provenance": 0, "passages": 0, "media_positions": 0}
    demo_corpus = db.scalar(select(Document).where(Document.slug == "antarctic-sea-ice-variability-study"))
    if demo_corpus:
        out["activities"] = seed_activities(db)
        out["media_positions"] = link_media_coordinates(db)
    out["provenance"] = ensure_all(db)
    if db.scalar(select(func.count()).select_from(DocumentChunk)):
        out["passages"] = index_new_passages(db)
    if any(out.values()):
        log.info("v2 data upgrade: %s", out)
    return out
