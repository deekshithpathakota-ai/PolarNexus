"""Unified catalogue view over all knowledge entities: cards, relationships and filters."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Dataset,
    Document,
    Expedition,
    Media,
    Researcher,
    ResourceLink,
    ResourceTopic,
    Station,
    Topic,
    User,
)
from app.utils.text import truncate_words

URL_PREFIX = {
    "document": "/resources",
    "dataset": "/datasets",
    "media": "/media",
    "expedition": "/expeditions",
    "station": "/stations",
    "researcher": "/researchers",
    "topic": "/explore?topic=",
}

PROFESSIONAL_ROLES = {"researcher", "editor", "admin"}


def resource_url(rtype: str, slug: str) -> str:
    prefix = URL_PREFIX[rtype]
    return f"{prefix}{slug}" if prefix.endswith("=") else f"{prefix}/{slug}"


def kind_label(rtype: str, obj) -> str:
    if rtype == "document":
        return obj.doc_type
    if rtype == "dataset":
        return "Dataset"
    if rtype == "media":
        return {"image": "Image", "video": "Video", "infographic": "Infographic"}.get(obj.media_type, "Image")
    if rtype == "expedition":
        return "Expedition"
    if rtype == "station":
        return "Research Station"
    if rtype == "researcher":
        return "Researcher"
    return rtype.title()


@dataclass
class Catalog:
    cards: dict[tuple[str, int], dict] = field(default_factory=dict)
    links: dict[tuple[str, int], set[tuple[str, int, str]]] = field(default_factory=lambda: defaultdict(set))
    topics: dict[int, Topic] = field(default_factory=dict)
    by_slug: dict[tuple[str, str], tuple[str, int]] = field(default_factory=dict)

    def card(self, rtype: str, rid: int) -> dict | None:
        return self.cards.get((rtype, rid))

    def related(self, rtype: str, rid: int, types: set[str] | None = None) -> list[dict]:
        out = []
        for t, i, rel in sorted(self.links.get((rtype, rid), set())):
            if types and t not in types:
                continue
            c = self.cards.get((t, i))
            if c:
                out.append({**c, "relation": rel})
        return out


def build_catalog(db: Session, user: User | None = None) -> Catalog:
    cat = Catalog()
    pro = bool(user and user.role_name in PROFESSIONAL_ROLES)
    cat.topics = {t.id: t for t in db.scalars(select(Topic))}
    topic_map: dict[tuple[str, int], list[Topic]] = defaultdict(list)
    for rt in db.scalars(select(ResourceTopic)):
        if rt.topic_id in cat.topics:
            topic_map[(rt.resource_type, rt.resource_id)].append(cat.topics[rt.topic_id])

    def add(rtype: str, obj, summary: str, region: str, year: int | None, source: str, extra: dict,
            visibility: str = "public", status: str = "indexed", language: str = "English"):
        if visibility != "public" and not pro:
            return
        if status == "archived" and not (user and user.role_name == "admin"):
            return
        tps = topic_map.get((rtype, obj.id), [])
        title = obj.name if rtype in {"researcher", "station", "expedition"} else obj.title
        card = {
            "type": rtype, "id": obj.id, "slug": obj.slug, "title": title,
            "kind": kind_label(rtype, obj), "summary": truncate_words(summary, 38),
            "region": region, "year": year, "source": source,
            "topics": [t.name for t in tps], "topic_slugs": [t.slug for t in tps],
            "views": getattr(obj, "views", 0) or 0, "is_demo": bool(getattr(obj, "is_demo", False)),
            "url": resource_url(rtype, obj.slug), "language": language, "visibility": visibility,
            "status": status, "extra": extra,
        }
        cat.cards[(rtype, obj.id)] = card
        cat.by_slug[(rtype, obj.slug)] = (rtype, obj.id)

    for d in db.scalars(select(Document)):
        add("document", d, d.abstract, d.region, d.year, d.source,
            {"authors": d.authors, "institution": d.institution, "keywords": d.keywords},
            d.visibility, d.status, d.language)
    for ds in db.scalars(select(Dataset)):
        add("dataset", ds, ds.description, ds.region, ds.year, ds.source,
            {"format": ds.format, "data_type": ds.data_type, "records": ds.record_count,
             "variables": [v["name"] for v in ds.variables]}, ds.visibility, ds.status)
    for m in db.scalars(select(Media)):
        add("media", m, m.description, m.region, m.year, m.credit,
            {"media_type": m.media_type, "scene": m.scene, "category": m.category, "duration": m.duration},
            m.visibility)
    for e in db.scalars(select(Expedition)):
        add("expedition", e, e.objective, e.region, e.year, "Expedition record",
            {"season": e.season, "program": e.program, "number": e.number})
    for s in db.scalars(select(Station)):
        add("station", s, s.description, s.region, None, s.facts_source or "Station record",
            {"latitude": s.latitude, "longitude": s.longitude, "established": s.established,
             "status": s.status, "verified": s.verified})
    for r in db.scalars(select(Researcher)):
        add("researcher", r, r.bio, "", None, r.institution,
            {"institution": r.institution, "expertise": r.expertise, "title": r.title})

    for link in db.scalars(select(ResourceLink)):
        a, b = (link.source_type, link.source_id), (link.target_type, link.target_id)
        if a in cat.cards and b in cat.cards:
            cat.links[a].add((b[0], b[1], link.relation))
            cat.links[b].add((a[0], a[1], link.relation))
    return cat


TYPE_FILTER_MAP = {
    # UI label -> predicate on card
    "Research Paper": lambda c: c["type"] == "document" and c["kind"] == "Research Paper",
    "Technical Report": lambda c: c["type"] == "document" and c["kind"] == "Technical Report",
    "Expedition Report": lambda c: c["type"] == "document" and c["kind"] == "Expedition Report",
    "Educational Resource": lambda c: c["type"] == "document" and c["kind"] == "Educational Resource",
    "News / Outreach": lambda c: c["type"] == "document" and c["kind"] == "News / Outreach",
    "Dataset": lambda c: c["type"] == "dataset",
    "Image": lambda c: c["type"] == "media" and c["kind"] == "Image",
    "Video": lambda c: c["type"] == "media" and c["kind"] == "Video",
    "Infographic": lambda c: c["type"] == "media" and c["kind"] == "Infographic",
    "Expedition": lambda c: c["type"] == "expedition",
    "Research Station": lambda c: c["type"] == "station",
    "Researcher": lambda c: c["type"] == "researcher",
}


@dataclass
class Filters:
    regions: list[str] = field(default_factory=list)
    types: list[str] = field(default_factory=list)
    topics: list[str] = field(default_factory=list)
    year_from: int | None = None
    year_to: int | None = None
    station: str | None = None
    expedition: str | None = None
    researcher: str | None = None
    language: str | None = None
    data_type: str | None = None

    def active(self) -> bool:
        return bool(self.regions or self.types or self.topics or self.year_from or self.year_to or self.station
                    or self.expedition or self.researcher or self.language or self.data_type)

    def as_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if v}


def apply_filters(cat: Catalog, cards: list[dict], f: Filters) -> list[dict]:
    def linked_to(c: dict, rtype: str, slug: str | None) -> bool:
        if not slug:
            return True
        key = cat.by_slug.get((rtype, slug))
        if not key:
            return False
        if (c["type"], c["id"]) == key:
            return True
        return any((t, i) == key for t, i, _ in cat.links.get((c["type"], c["id"]), set()))

    out = []
    for c in cards:
        if f.regions and c["region"] not in f.regions:
            continue
        if f.types and not any(TYPE_FILTER_MAP.get(t, lambda _c: False)(c) for t in f.types):
            continue
        if f.topics and not set(f.topics) & set(c["topic_slugs"]):
            continue
        if f.year_from and (c["year"] is None or c["year"] < f.year_from):
            continue
        if f.year_to and (c["year"] is None or c["year"] > f.year_to):
            continue
        if f.language and c["language"] != f.language:
            continue
        if f.data_type and c["extra"].get("data_type") != f.data_type:
            continue
        if not (linked_to(c, "station", f.station) and linked_to(c, "expedition", f.expedition)
                and linked_to(c, "researcher", f.researcher)):
            continue
        out.append(c)
    return out
