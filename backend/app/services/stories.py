"""Research Story builder.

A story connects one piece of research to everything the repository knows about it:

    Topic → Research paper → Dataset → Expedition → Station / location → Photographs → Video → Researchers
          → Scientific summary · Public explanation · Student explanation

Items come only from typed links already in the knowledge graph (or are added by the user). The three
explanations are produced by the existing grounded summariser from the primary paper's own sections — every
sentence carries a citation, nothing is invented. A story without a paper falls back to quoting the records'
own descriptions, also cited.
"""
from __future__ import annotations

import re
from collections import OrderedDict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Dataset, Document, DocumentChunk, Expedition, InstitutionalActivity, Media, ResearchStory, Station, Topic
from app.rag.simplify import simplify
from app.rag.summary import summarize
from app.services import provenance as prov
from app.services.catalog import Catalog
from app.utils.text import slugify, split_sentences

ROLE = OrderedDict([
    ("topic", ("Research topic", 3)),
    ("document", ("Research paper", 3)),
    ("dataset", ("Dataset", 3)),
    ("expedition", ("Expedition", 3)),
    ("station", ("Station / location", 3)),
    ("image", ("Photograph", 6)),
    ("video", ("Video", 3)),
    ("researcher", ("Researcher", 4)),
    ("activity", ("Outreach & activities", 2)),
])
MODES = {"scientific": ("Scientific summary", "research"), "public": ("Public explanation", "executive"),
         "student": ("Student explanation", "student")}


def _role_key(card: dict) -> str:
    if card["type"] == "media":
        return "video" if card["extra"].get("media_type") == "video" else "image"
    return card["type"]


def suggest_items(cat: Catalog, seed_type: str, seed_id: int) -> list[dict]:
    """Walks the graph two hops from the seed and returns story items in narrative order."""
    seed = cat.card(seed_type, seed_id)
    if not seed:
        return []
    scores: dict[tuple[str, int], float] = {(seed_type, seed_id): 100.0}
    first = cat.related(seed_type, seed_id)
    for r in first:
        scores[(r["type"], r["id"])] = scores.get((r["type"], r["id"]), 0) + 10
    for r in first:
        if r["type"] in {"station", "expedition", "dataset", "document"}:
            for r2 in cat.related(r["type"], r["id"]):
                if r2["type"] in {"media", "researcher", "expedition", "station", "dataset"}:
                    scores[(r2["type"], r2["id"])] = scores.get((r2["type"], r2["id"]), 0) + 3
    for slug in seed.get("topic_slugs", []):
        key = cat.by_slug.get(("topic", slug))
        if key:
            scores[key] = scores.get(key, 0) + 8
    buckets: dict[str, list[tuple[float, dict]]] = {k: [] for k in ROLE}
    for key, sc in scores.items():
        c = cat.card(*key)
        if not c or c["type"] == "content":
            continue
        rk = _role_key(c)
        if rk in buckets:
            # prefer authoritative records at equal graph distance
            bonus = 1.0 if c.get("verification") in prov.AUTHORITATIVE_STATUSES else 0
            buckets[rk].append((sc + bonus + min(c["views"], 500) / 1000, c))
    items = []
    for rk, (label, cap) in ROLE.items():
        for _, c in sorted(buckets[rk], key=lambda x: -x[0])[:cap]:
            items.append({"type": c["type"], "id": c["id"], "role": label, "note": ""})
    return items


def _primary_document(db: Session, cat: Catalog, items: list[dict]) -> Document | None:
    for it in items:
        if it["type"] == "document" and cat.card("document", it["id"]):
            d = db.get(Document, it["id"])
            if d and d.chunks and not d.metadata_only:
                return d
    return None


def _fallback_summary(db: Session, cat: Catalog, items: list[dict], mode: str) -> dict:
    """No paper with sections: quote each record's own description (first sentences), cited."""
    sources, lines = [], []
    for it in items:
        if it["type"] not in {"dataset", "expedition", "station", "document"} or len(sources) >= 4:
            continue
        ch = db.scalar(select(DocumentChunk).where(DocumentChunk.resource_type == it["type"],
                                                   DocumentChunk.resource_id == it["id"]).order_by(DocumentChunk.chunk_index))
        card = cat.card(it["type"], it["id"])
        if not ch or not card:
            continue
        n = len(sources) + 1
        sents = [s for s in split_sentences(ch.text) if not s.startswith(card["title"])][:2]
        if not sents:
            continue
        text = " ".join(simplify(s) if mode != "scientific" else s for s in sents)
        lines.append(f"- **{card['title']}** — {text} [{n}]")
        sources.append({"n": n, "chunk_id": ch.id, "section": ch.section, "page": ch.page, "snippet": ch.text,
                        "title": card["title"], "slug": card["slug"], "url": card["url"], "resource_type": it["type"]})
    if not lines:
        return {"label": MODES[mode][0], "text": "", "sources": [], "mode": "insufficient",
                "notice": "None of the story's records contain descriptive text that could ground an explanation."}
    return {"label": MODES[mode][0], "text": "\n".join(lines), "sources": sources, "mode": "extractive",
            "notice": "Quoted from the connected records' own descriptions."}


def build_summaries(db: Session, cat: Catalog, items: list[dict]) -> dict:
    doc = _primary_document(db, cat, items)
    out = {}
    for mode, (label, kind) in MODES.items():
        if doc:
            s = summarize(db, doc, kind)
            text = s["text"]
            if mode == "public" and s["mode"] == "extractive":
                text = "\n".join(simplify(line) if not line.startswith("**") else line for line in text.split("\n"))
            out[mode] = {"label": label, "text": text, "mode": s["mode"], "notice": s.get("notice", ""),
                         "based_on": {"type": "document", "slug": doc.slug, "title": doc.title},
                         "sources": [{**x, "resource_type": "document"} for x in s["sources"]]}
        else:
            out[mode] = _fallback_summary(db, cat, items, mode)
    return out


def _dates(db: Session, c: dict) -> tuple[str | None, str]:
    t, i = c["type"], c["id"]
    if t == "expedition":
        e = db.get(Expedition, i)
        return (f"{e.year}-01-01" if e and e.year else None), (e.season if e else "")
    if t == "dataset":
        d = db.get(Dataset, i)
        if d and d.temporal_start:
            return d.temporal_start.isoformat(), f"Data {d.temporal_start.year}–{d.temporal_end.year if d.temporal_end else '…'}"
    if t == "media":
        m = db.get(Media, i)
        if m and m.captured_at:
            return m.captured_at.date().isoformat(), "Captured"
    if t == "activity":
        a = db.get(InstitutionalActivity, i)
        if a and a.date:
            return a.date.isoformat(), "Held"
    if t == "station":
        s = db.get(Station, i)
        m = re.search(r"\b(19|20)\d{2}\b", s.established or "") if s else None
        if m:
            return f"{m.group(0)}-01-01", "Established"
    return (f"{c['year']}-01-01" if c.get("year") else None), "Published" if t == "document" else ""


def _coords(db: Session, c: dict) -> tuple[float, float] | None:
    model = {"station": Station, "expedition": Expedition, "media": Media, "activity": InstitutionalActivity}.get(c["type"])
    if not model:
        return None
    o = db.get(model, c["id"])
    if o is not None and o.latitude is not None and o.longitude is not None:
        return float(o.latitude), float(o.longitude)
    return None


def story_out(db: Session, cat: Catalog, s: ResearchStory, full: bool = True) -> dict:
    items = []
    for it in s.items or []:
        c = cat.card(it["type"], it["id"])
        if not c:
            continue  # not visible to this user (internal, archived) — silently omitted
        items.append({**{k: c[k] for k in ("type", "id", "slug", "title", "kind", "region", "year", "url", "summary",
                                            "is_demo", "verification", "verification_label", "topics")},
                      "role": it.get("role") or ROLE.get(_role_key(c), ("Related",))[0], "note": it.get("note", ""),
                      "extra": {k: c["extra"].get(k) for k in ("media_type", "scene", "thumbnail", "duration")} if c["type"] == "media" else {}})
    records = [i for i in items if i["type"] != "topic"]  # taxonomy entries are not evidence
    demo_items = sum(1 for i in records if i["verification"] in prov.DEMO_STATUSES)
    out = {"id": s.id, "slug": s.slug, "title": s.title, "status": s.status, "is_demo": s.is_demo,
           "created_at": s.created_at.isoformat() if s.created_at else None,
           "updated_at": s.updated_at.isoformat() if s.updated_at else None,
           "item_count": len(items), "cover": next((i for i in items if i["type"] == "media"), None),
           "roles": list(OrderedDict.fromkeys(i["role"] for i in items)),
           "basis": {"items": len(records), "demonstration": demo_items,
                     "authoritative": sum(1 for i in records if i["verification"] in prov.AUTHORITATIVE_STATUSES)}}
    if not full:
        return out
    timeline, points = [], []
    for i in items:
        d, label = _dates(db, i)
        if d:
            timeline.append({"date": d, "label": label, "title": i["title"], "type": i["type"], "url": i["url"], "kind": i["kind"]})
        xy = _coords(db, i)
        if xy:
            points.append({"lat": xy[0], "lon": xy[1], "title": i["title"], "type": i["type"], "url": i["url"],
                           "verification": i["verification"]})
    timeline.sort(key=lambda x: x["date"])
    topics = [i for i in items if i["type"] == "topic"]
    summaries = s.summaries or {}
    evidence = OrderedDict()
    for mode in MODES:
        for src in (summaries.get(mode) or {}).get("sources", []):
            evidence.setdefault((src.get("slug"), src.get("section")), src)
    out.update(items=items, timeline=timeline, map_points=points, topics=topics, summaries=summaries,
               evidence=list(evidence.values()),
               chain=[{"role": r, "items": [x for x in items if x["role"] == r]} for r in out["roles"]],
               notice=("This story is assembled from prototype demonstration records — it shows how the system connects "
                       "knowledge, not verified science.") if records and demo_items == len(records) else
                      (f"{demo_items} of {len(records)} connected records are demonstration data." if demo_items else ""))
    return out


def create_story(db: Session, cat: Catalog, title: str, seed_type: str | None, seed_id: int | None,
                 items: list[dict] | None, user_id: int | None, is_demo: bool = False, status: str = "draft") -> ResearchStory:
    if items is None:
        items = suggest_items(cat, seed_type, seed_id) if seed_type and seed_id else []
    items = [it for it in items if cat.card(it["type"], it["id"])]
    base = slugify(title)[:140] or "story"
    slug, n = base, 2
    while db.scalar(select(ResearchStory).where(ResearchStory.slug == slug)):
        slug, n = f"{base}-{n}", n + 1
    s = ResearchStory(slug=slug, title=title[:300], items=items, seed_type=seed_type or "", seed_id=seed_id,
                      summaries=build_summaries(db, cat, items), status=status, is_demo=is_demo, created_by=user_id)
    db.add(s)
    db.commit()
    return s


def default_title(cat: Catalog, seed_type: str, seed_id: int) -> str:
    c = cat.card(seed_type, seed_id)
    return f"The story behind “{c['title']}”" if c else "Research story"


def topic_for(db: Session, slug: str) -> Topic | None:
    return db.scalar(select(Topic).where(Topic.slug == slug))
