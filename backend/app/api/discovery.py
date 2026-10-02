"""Topic pages, the Knowledge Timeline, the Impact & KPI dashboard and the Provenance & Verification centre."""
from __future__ import annotations

import statistics
from collections import Counter, defaultdict
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.security import get_current_user_optional, require_permission
from app.core.database import get_db
from app.models import (
    AIQuery,
    AnalyticsEvent,
    GeneratedContent,
    Provenance,
    Review,
    SearchLog,
    Topic,
    User,
)
from app.search.service import resource_group
from app.services import provenance as prov
from app.services.audit import audit
from app.services.catalog import build_catalog

router = APIRouter(prefix="/api", tags=["discovery"])

HISTORICAL_MARKER = "(historical demo record)"
TIMELINE_TYPES = {"document", "dataset", "media", "expedition", "activity", "content"}


# ------------------------------------------------------------------ topics
@router.get("/topics/{slug}")
def topic_detail(slug: str, db: Session = Depends(get_db), user: User | None = Depends(get_current_user_optional)):
    t = db.scalar(select(Topic).where(Topic.slug == slug))
    if not t:
        raise HTTPException(404, "Topic not found.")
    cat = build_catalog(db, user)
    tagged = [c for c in cat.cards.values() if slug in c["topic_slugs"] and c["type"] != "topic"]
    groups: dict[str, list] = defaultdict(list)
    for c in sorted(tagged, key=lambda c: (-(c["views"] or 0), c["title"])):
        groups[c["type"]].append(c)
    co = Counter(s for c in tagged for s in c["topic_slugs"] if s != slug)
    names = {tp.slug: tp.name for tp in cat.topics.values()}
    related = [{"slug": s, "name": names.get(s, s), "count": n} for s, n in co.most_common(8)]
    years = [c["year"] for c in tagged if c["year"]]
    return {"type": "topic", "id": t.id, "slug": t.slug, "name": t.name, "title": t.name, "category": t.category,
            "description": t.description, "total": len(tagged),
            "counts": dict(Counter(resource_group(c) for c in tagged)),
            "groups": {k: v[:8] for k, v in groups.items()}, "related_topics": related,
            "year_span": [min(years), max(years)] if years else None,
            "provenance": prov.provenance_out({**prov.default_provenance("topic", t), "source_type": "Platform taxonomy",
                                               "source_organisation": "PolarNexus", "verification_status": "verified",
                                               "provenance_notes": "Controlled vocabulary used to connect records."})}


# ------------------------------------------------------------------ timeline
def _item_date(c: dict) -> str | None:
    e = c["extra"]
    if c["type"] == "activity":
        return e.get("date")
    return None


@router.get("/timeline")
def timeline(topic: str | None = Query(None, max_length=120), expedition: str | None = Query(None, max_length=160),
             station: str | None = Query(None, max_length=160), researcher: str | None = Query(None, max_length=160),
             activity: str | None = Query(None, max_length=160), type: list[str] | None = Query(None),
             year_from: int | None = Query(None, ge=1800, le=2100), year_to: int | None = Query(None, ge=1800, le=2100),
             limit: int = Query(250, ge=1, le=500), db: Session = Depends(get_db),
             user: User | None = Depends(get_current_user_optional)):
    """Chronological view of the records connected to a topic / expedition / station / researcher.
    Built only from existing records and their own years — nothing is inferred."""
    cat = build_catalog(db, user)
    scope: set[tuple[str, int]] | None = None
    anchors = []
    for rtype, slug in (("expedition", expedition), ("station", station), ("researcher", researcher), ("activity", activity)):
        if not slug:
            continue
        key = cat.by_slug.get((rtype, slug))
        if not key:
            raise HTTPException(404, f"{rtype.title()} not found.")
        anchors.append(cat.cards[key]["title"])
        linked = {key} | {(t, i) for t, i, _ in cat.links.get(key, set())}
        # include second-degree records reached through linked documents (e.g. station -> paper -> dataset)
        for t, i in list(linked):
            if t == "document":
                linked |= {(t2, i2) for t2, i2, _ in cat.links.get((t, i), set()) if t2 in {"dataset", "media"}}
        scope = linked if scope is None else scope & linked
    types = {t for t in (type or []) if t in TIMELINE_TYPES} or TIMELINE_TYPES
    items = []
    for key, c in cat.cards.items():
        if c["type"] not in types or not c["year"]:
            continue
        if scope is not None and key not in scope:
            continue
        if topic and topic not in c["topic_slugs"]:
            continue
        if year_from and c["year"] < year_from or year_to and c["year"] > year_to:
            continue
        items.append({"key": f"{c['type']}:{c['id']}", "type": c["type"], "kind": c["kind"], "title": c["title"],
                      "url": c["url"], "year": c["year"], "date": _item_date(c), "summary": c["summary"],
                      "region": c["region"], "is_demo": c["is_demo"], "verification": c["verification"],
                      "verification_label": c["verification_label"], "group": resource_group(c)})
    items.sort(key=lambda x: (x["year"], x["date"] or "", x["type"], x["title"]))
    by_year = Counter(i["year"] for i in items)
    if topic:
        t = db.scalar(select(Topic).where(Topic.slug == topic))
        if t:
            anchors.append(t.name)
    return {"items": items[-limit:] if len(items) > limit else items, "total": len(items),
            "years": [{"year": y, "count": n} for y, n in sorted(by_year.items())],
            "anchors": anchors, "types": sorted(types),
            "note": "Built from repository records and their recorded years. Demonstration records are labelled."}


# ------------------------------------------------------------------ impact & KPIs
def _pct(values: list[float], q: float) -> float | None:
    if not values:
        return None
    vs = sorted(values)
    return round(vs[min(len(vs) - 1, int(q * (len(vs) - 1) + 0.5))], 1)


@router.get("/impact")
def impact(db: Session = Depends(get_db), user: User | None = Depends(get_current_user_optional)):
    cat = build_catalog(db, user)
    groups = Counter(resource_group(c) for c in cat.cards.values())
    verification = Counter(c["verification_label"] for c in cat.cards.values() if c["type"] != "topic")

    ai_rows = db.execute(select(AIQuery.evidence_status, AIQuery.mode, AIQuery.answer, AIQuery.sources, AIQuery.duration_ms)).all()
    live_ai = [r for r in ai_rows if r[2] != HISTORICAL_MARKER]
    answered_live = [r for r in live_ai if r[0] != "insufficient"]
    cited_live = [r for r in answered_live if r[3]]
    ai_latency = [r[4] for r in live_ai if r[4] is not None]

    search_rows = db.execute(select(SearchLog.query, SearchLog.duration_ms)).all()
    search_latency = [r[1] for r in search_rows if r[1] is not None]

    content = db.scalars(select(GeneratedContent)).all()
    review_actions = Counter(a for (a,) in db.execute(select(Review.action)))
    turnaround = [(c.approved_at - c.submitted_at).total_seconds() / 3600 for c in content if c.approved_at and c.submitted_at]
    views = db.scalar(select(func.count()).select_from(AnalyticsEvent).where(AnalyticsEvent.event_type == "view")) or 0
    top_searches = Counter(q.lower().strip() for q, _ in search_rows if q).most_common(8)
    most_accessed = sorted((c for c in cat.cards.values() if c["type"] not in {"topic", "content"}), key=lambda c: -c["views"])[:8]

    return {
        "label": "Prototype Demonstration Metrics",
        "disclaimer": ("Counts describe this prototype deployment: seeded demonstration records and history plus live "
                       "usage. They are not real-world institutional impact statistics."),
        "knowledge": {"total": sum(v for k, v in groups.items() if k != "Topics"), "by_type": dict(groups),
                      "by_verification": dict(verification)},
        "ai": {
            "questions_answered": len(ai_rows),
            "evidence_grounded": sum(1 for r in ai_rows if r[0] in {"strong", "limited"}),
            "insufficient_evidence": sum(1 for r in ai_rows if r[0] == "insufficient"),
            "by_mode": dict(Counter(r[1] for r in ai_rows)),
            "live_questions": len(live_ai),
            "citation_validation_rate": round(len(cited_live) / len(answered_live), 3) if answered_live else None,
            "citation_validation_basis": (f"{len(cited_live)} of {len(answered_live)} live answers kept at least one "
                                          "citation that maps to a retrieved passage (invalid markers are removed)."
                                          if answered_live else "No live answers recorded yet on this deployment."),
        },
        "content": {
            "drafts_generated": len(content),
            "evidence_checked": sum(1 for c in content if (c.evidence_check or {}).get("overall")),
            "evidence_pass": sum(1 for c in content if (c.evidence_check or {}).get("overall") == "pass"),
            "reviews_completed": sum(review_actions[a] for a in ("approved", "rejected", "changes_requested")),
            "approved": sum(1 for c in content if c.status in {"approved", "published"}),
            "published": sum(1 for c in content if c.status == "published"),
            "by_status": dict(Counter(c.status for c in content)),
        },
        "discovery": {
            "searches": len(search_rows), "resource_views": views,
            "top_searches": [{"query": q, "count": n} for q, n in top_searches],
            "most_accessed": [{"title": c["title"], "url": c["url"], "type": c["type"], "kind": c["kind"], "views": c["views"]}
                              for c in most_accessed],
        },
        "measured": {
            "search_latency_ms": {"median": _pct(search_latency, 0.5), "p90": _pct(search_latency, 0.9), "samples": len(search_latency)},
            "ai_latency_ms": {"median": _pct(ai_latency, 0.5), "p90": _pct(ai_latency, 0.9), "samples": len(ai_latency)},
            "review_turnaround_hours": {"median": round(statistics.median(turnaround), 1) if turnaround else None,
                                        "samples": len(turnaround), "note": "Includes seeded demonstration review history."},
            "note": "Latencies are server-side timings measured on this deployment for live requests only.",
        },
        "workflow": [
            {"stage": "Find sources", "traditional": "Manual search across separate archives, drives and portals",
             "polarnexus": "One hybrid (keyword + semantic) search across documents, data, media, expeditions and activities"},
            {"stage": "Cross-reference", "traditional": "Manually matching papers to datasets, stations and expeditions",
             "polarnexus": "Typed relationships, related-knowledge panels, knowledge graph and timeline"},
            {"stage": "Check trust", "traditional": "Provenance tracked informally, if at all",
             "polarnexus": "Provenance panel and verification status on every record; demo data labelled"},
            {"stage": "Prepare outreach", "traditional": "Writing from scratch, citations added by hand",
             "polarnexus": "AI-assisted drafts built only from cited passages, with an automated evidence check"},
            {"stage": "Approve & publish", "traditional": "Email-based review",
             "polarnexus": "Human review workflow with audit trail; nothing AI-generated is published without approval"},
        ],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


# ------------------------------------------------------------------ provenance & verification
class ProvenancePatch(BaseModel):
    verification_status: str | None = Field(default=None, max_length=24)
    source_organisation: str | None = Field(default=None, max_length=255)
    source_type: str | None = Field(default=None, max_length=64)
    source_url: str | None = Field(default=None, max_length=500, pattern=r"^(https?://\S+)?$")
    original_identifier: str | None = Field(default=None, max_length=255)
    license: str | None = Field(default=None, max_length=255)
    data_quality: str | None = Field(default=None, max_length=120)
    provenance_notes: str | None = Field(default=None, max_length=4000)
    comment: str = Field(default="", max_length=1000)


def _resource(db: Session, rtype: str, key: str):
    model = prov.MODELS.get(rtype)
    if not model:
        raise HTTPException(404, "Unknown resource type.")
    obj = db.get(model, int(key)) if key.isdigit() else db.scalar(select(model).where(model.slug == key))
    if not obj:
        raise HTTPException(404, "Resource not found.")
    return obj


@router.get("/provenance/statuses")
def statuses():
    return {"statuses": [{"key": k, "label": v[0], "description": v[1]} for k, v in prov.VERIFICATION.items()],
            "filters": list(prov.FILTERS)}


@router.get("/provenance/{rtype}/{key}")
def provenance_detail(rtype: str, key: str, db: Session = Depends(get_db), user: User | None = Depends(get_current_user_optional)):
    obj = _resource(db, rtype, key)
    if not build_catalog(db, user).card(rtype, obj.id):
        raise HTTPException(404, "Resource not found.")
    return prov.get_provenance(db, rtype, obj)


@router.get("/admin/provenance")
def provenance_queue(status: str | None = Query(None, max_length=24), type: str | None = Query(None, max_length=24),
                     q: str | None = Query(None, max_length=200), page: int = Query(1, ge=1), page_size: int = Query(25, le=100),
                     db: Session = Depends(get_db), user: User = Depends(require_permission("manage_repository"))):
    prov.ensure_all(db)
    cat = build_catalog(db, user)
    rows = db.scalars(select(Provenance).order_by(Provenance.updated_at.desc())).all()
    counts = Counter(r.verification_status for r in rows)
    by_type = Counter(r.resource_type for r in rows)
    out = []
    for r in rows:
        card = cat.card(r.resource_type, r.resource_id)
        if not card or (status and r.verification_status != status) or (type and r.resource_type != type):
            continue
        if q and q.lower() not in card["title"].lower():
            continue
        out.append({"resource_type": r.resource_type, "resource_id": r.resource_id, "title": card["title"],
                    "url": card["url"], "kind": card["kind"], "slug": card["slug"], "is_demo": card["is_demo"],
                    **prov.provenance_out(r)})
    total = len(out)
    return {"total": total, "page": page, "pages": max(1, -(-total // page_size)),
            "results": out[(page - 1) * page_size: page * page_size],
            "counts": {k: counts.get(k, 0) for k in prov.VERIFICATION}, "by_type": dict(by_type),
            "statuses": [{"key": k, "label": v[0]} for k, v in prov.VERIFICATION.items()]}


@router.patch("/admin/provenance/{rtype}/{key}")
def update_provenance(rtype: str, key: str, body: ProvenancePatch, db: Session = Depends(get_db),
                      user: User = Depends(require_permission("manage_repository"))):
    obj = _resource(db, rtype, key)
    row = prov.ensure_for(db, rtype, obj, commit=False)
    db.flush()
    changes = body.model_dump(exclude_unset=True, exclude={"comment"})
    if not changes:
        raise HTTPException(422, "No changes supplied.")
    old = row.verification_status
    if body.verification_status is not None:
        try:
            prov.validate_status_change(rtype, obj, body.verification_status)
        except ValueError as exc:
            audit(db, user, "verify", rtype, getattr(obj, "slug", obj.id), f"Refused: {exc}", status="failure")
            raise HTTPException(422, str(exc))
    for k, v in changes.items():
        setattr(row, k, v)
    if body.verification_status is not None and body.verification_status != old:
        row.last_verified_at = datetime.now(timezone.utc)
        row.verified_by = user.name if body.verification_status in prov.TRUSTED_STATUSES else ""
    db.commit()
    new = row.verification_status
    action = ("verify" if new in prov.TRUSTED_STATUSES and new != old else
              "reject" if new == "unverified" and old != "unverified" else
              "verification_change" if new != old else "provenance_edit")
    audit(db, user, action, rtype, getattr(obj, "slug", obj.id),
          f"{prov.VERIFICATION[old][0]} → {prov.VERIFICATION[new][0]}" + (f". {body.comment}" if body.comment else "")
          + ("" if new != old else f" (fields: {', '.join(sorted(changes))})"))
    return prov.provenance_out(row)


# ------------------------------------------------------------------ small lookup used by filters
@router.get("/filters/options")
def filter_options(db: Session = Depends(get_db), user: User | None = Depends(get_current_user_optional)):
    cat = build_catalog(db, user)
    orgs = Counter(c["organisation"] for c in cat.cards.values() if c.get("organisation") and c["type"] != "topic")
    return {"organisations": [o for o, _ in orgs.most_common(40)], "verification": list(prov.FILTERS),
            "researchers": sorted(({"slug": c["slug"], "name": c["title"]} for c in cat.cards.values()
                                   if c["type"] == "researcher"), key=lambda x: x["name"]),
            "media_types": ["Image", "Video", "Infographic"],
            "languages": sorted({c["language"] for c in cat.cards.values() if c.get("language")})}

