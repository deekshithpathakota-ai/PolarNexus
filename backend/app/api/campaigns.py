"""Outreach Campaign Planner, Content Calendar and Outreach Impact Analytics.

Campaigns group planned outreach items on a calendar. Scheduling and publishing an item always respects the
existing human-review workflow: an item can be scheduled only when its content has been approved by an editor,
and publishing calls the same publish transition as the Review Center. Only the website feed is a live channel;
social, newsletter and educational-portal publishing are labelled prototype simulations.

Engagement events are stored in `outreach_events`. Seeded rows are flagged `is_demo` and every analytics response
reports how many demo vs. live events it includes, so demonstration metrics are always labelled.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.security import can, get_current_user, get_current_user_optional, require_permission
from app.core.database import get_db
from app.core.ratelimit import rate_limit
from app.models import Campaign, CampaignItem, GeneratedContent, OutreachEvent, Topic, User
from app.schemas.common import ReviewAction
from app.services.audit import audit
from app.services.catalog import build_catalog
from app.services.serializers import CHANNELS
from app.utils.text import slugify

router = APIRouter(prefix="/api", tags=["campaigns"])

AUDIENCES = {"students": "Students", "teachers": "Teachers", "researchers": "Researchers", "public": "General Public",
             "policy": "Institutional / Policy"}
CAMPAIGN_CHANNELS = {
    "website": {"label": "Website", "publish_as": ["website"]},
    "social_media": {"label": "Social Media", "publish_as": ["website", "linkedin", "instagram"]},
    "newsletter": {"label": "Newsletter", "publish_as": ["website", "newsletter"]},
    "education_portal": {"label": "Educational Portal", "publish_as": ["website", "education_portal"]},
}
CAMPAIGN_STATUSES = ["draft", "scheduled", "published", "archived"]
ITEM_STATUSES = ["planned", "scheduled", "published", "cancelled"]
READY_CONTENT = {"approved", "published"}


class CampaignIn(BaseModel):
    name: str = Field(min_length=3, max_length=200)
    description: str = Field(default="", max_length=4000)
    start_date: date | None = None
    end_date: date | None = None
    audiences: list[str] = Field(default_factory=list, max_length=5)
    topics: list[str] = Field(default_factory=list, max_length=12)
    channels: list[str] = Field(default_factory=lambda: ["website"], max_length=4)


class CampaignPatch(BaseModel):
    name: str | None = Field(default=None, min_length=3, max_length=200)
    description: str | None = Field(default=None, max_length=4000)
    start_date: date | None = None
    end_date: date | None = None
    audiences: list[str] | None = None
    topics: list[str] | None = None
    channels: list[str] | None = None
    status: str | None = Field(default=None, pattern="^(draft|scheduled|published|archived)$")


class ItemIn(BaseModel):
    title: str = Field(min_length=2, max_length=300)
    content_id: int | None = None
    content_type: str = Field(default="", max_length=48)
    channel: str = Field(default="website", pattern="^(website|social_media|newsletter|education_portal)$")
    audience: str = Field(default="", max_length=32)
    scheduled_for: date | None = None
    notes: str = Field(default="", max_length=2000)


class ItemPatch(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=300)
    content_id: int | None = None
    content_type: str | None = Field(default=None, max_length=48)
    channel: str | None = Field(default=None, pattern="^(website|social_media|newsletter|education_portal)$")
    audience: str | None = Field(default=None, max_length=32)
    scheduled_for: date | None = None
    notes: str | None = Field(default=None, max_length=2000)
    status: str | None = Field(default=None, pattern="^(planned|scheduled|cancelled)$")


class TrackIn(BaseModel):
    event: str = Field(pattern="^(view|click|share|complete)$")
    channel: str = Field(default="website", max_length=32)


def _staff(user: User) -> User:
    if not (can(user, "generate_content") or can(user, "review")):
        raise HTTPException(403, "Campaign planning is available to researchers, editors and administrators.")
    return user


def _validate(body, db: Session) -> None:
    for a in body.audiences or []:
        if a not in AUDIENCES:
            raise HTTPException(422, f"Unknown audience '{a}'.")
    for c in body.channels or []:
        if c not in CAMPAIGN_CHANNELS:
            raise HTTPException(422, f"Unknown channel '{c}'.")
    if body.topics:
        known = {t.slug for t in db.scalars(select(Topic).where(Topic.slug.in_(body.topics)))}
        if set(body.topics) - known:
            raise HTTPException(422, "Unknown topic.")
    if body.start_date and body.end_date and body.end_date < body.start_date:
        raise HTTPException(422, "The end date must be on or after the start date.")


def _get(db: Session, slug: str) -> Campaign:
    c = db.scalar(select(Campaign).where(Campaign.slug == slug))
    if not c:
        raise HTTPException(404, "Campaign not found.")
    return c


def _content_brief(c: GeneratedContent | None) -> dict | None:
    if not c:
        return None
    return {"id": c.id, "title": c.title, "status": c.status, "format": c.format, "audience": c.audience,
            "published_at": c.published_at.isoformat() if c.published_at else None, "is_demo": c.is_demo}


def item_out(db: Session, it: CampaignItem) -> dict:
    c = db.get(GeneratedContent, it.content_id) if it.content_id else None
    ch = CAMPAIGN_CHANNELS.get(it.channel, {"label": it.channel, "publish_as": ["website"]})
    simulated = [x for x in ch["publish_as"] if CHANNELS.get(x, {}).get("status") != "live"]
    blockers = []
    if not c:
        blockers.append("Link approved content to schedule this item")
    elif c.status not in READY_CONTENT:
        blockers.append(f"Content is '{c.status.replace('_', ' ')}' — it must be approved by an editor first")
    return {"id": it.id, "campaign_id": it.campaign_id, "title": it.title, "content_type": it.content_type,
            "channel": it.channel, "channel_label": ch["label"], "simulated_channels": simulated,
            "audience": it.audience, "scheduled_for": it.scheduled_for.isoformat() if it.scheduled_for else None,
            "status": it.status, "notes": it.notes, "content": _content_brief(c), "blockers": blockers,
            "can_schedule": not blockers, "can_publish": bool(c and c.status == "approved") or bool(c and c.status == "published")}


def campaign_out(db: Session, c: Campaign, full: bool = True) -> dict:
    items = sorted(c.items, key=lambda i: (i.scheduled_for or date.max, i.id))
    counts = Counter(i.status for i in items)
    out = {"id": c.id, "slug": c.slug, "name": c.name, "description": c.description,
           "start_date": c.start_date.isoformat() if c.start_date else None,
           "end_date": c.end_date.isoformat() if c.end_date else None,
           "audiences": [{"key": a, "label": AUDIENCES.get(a, a)} for a in c.audiences or []],
           "topics": c.topics or [], "channels": [{"key": ch, "label": CAMPAIGN_CHANNELS.get(ch, {}).get("label", ch),
                                                   "simulated": ch != "website"} for ch in c.channels or []],
           "status": c.status, "is_demo": c.is_demo, "item_counts": {s: counts.get(s, 0) for s in ITEM_STATUSES},
           "items_total": len(items)}
    if full:
        out["items"] = [item_out(db, i) for i in items]
    return out


@router.get("/campaigns/options")
def options(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _staff(user)
    content = db.scalars(select(GeneratedContent).where(GeneratedContent.status.notin_(["rejected"]))
                         .order_by(GeneratedContent.updated_at.desc()).limit(80)).all()
    return {"audiences": [{"key": k, "label": v} for k, v in AUDIENCES.items()],
            "channels": [{"key": k, "label": v["label"], "live": k == "website",
                          "note": "Live — published to the public Outreach Feed" if k == "website" else "Prototype simulation — no external integration configured"}
                         for k, v in CAMPAIGN_CHANNELS.items()],
            "statuses": CAMPAIGN_STATUSES, "item_statuses": ITEM_STATUSES,
            "topics": [{"slug": t.slug, "name": t.name} for t in db.scalars(select(Topic).order_by(Topic.name))],
            "content": [_content_brief(c) for c in content]}


@router.get("/campaigns")
def list_campaigns(include_archived: bool = False, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _staff(user)
    rows = db.scalars(select(Campaign).order_by(Campaign.start_date.desc().nullslast(), Campaign.id.desc())).all()
    return {"results": [campaign_out(db, c, full=False) for c in rows if include_archived or c.status != "archived"]}


@router.post("/campaigns")
def create_campaign(body: CampaignIn, db: Session = Depends(get_db), user: User = Depends(require_permission("generate_content"))):
    _validate(body, db)
    base = slugify(body.name)[:140] or "campaign"
    slug, n = base, 2
    while db.scalar(select(Campaign).where(Campaign.slug == slug)):
        slug, n = f"{base}-{n}", n + 1
    c = Campaign(slug=slug, name=body.name.strip(), description=body.description.strip(), start_date=body.start_date,
                 end_date=body.end_date, audiences=body.audiences, topics=body.topics,
                 channels=list(dict.fromkeys(body.channels or ["website"])), status="draft", created_by=user.id)
    db.add(c)
    db.commit()
    audit(db, user, "campaign_create", "campaign", c.slug, c.name)
    return campaign_out(db, c)


@router.get("/campaigns/{slug}")
def get_campaign(slug: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _staff(user)
    return campaign_out(db, _get(db, slug))


@router.patch("/campaigns/{slug}")
def update_campaign(slug: str, body: CampaignPatch, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _staff(user)
    c = _get(db, slug)
    _validate(CampaignIn(name=body.name or c.name, start_date=body.start_date or c.start_date,
                         end_date=body.end_date or c.end_date, audiences=body.audiences or [], topics=body.topics or [],
                         channels=body.channels or ["website"]), db)
    changes = body.model_dump(exclude_unset=True)
    status = changes.pop("status", None)
    for k, v in changes.items():
        setattr(c, k, v)
    if status and status != c.status:
        live = [i for i in c.items if i.status != "cancelled"]
        if status == "scheduled" and not any(i.status in {"scheduled", "published"} for i in live):
            raise HTTPException(409, "Schedule at least one item (with approved content) before scheduling the campaign.")
        if status == "published":
            if not can(user, "publish"):
                raise HTTPException(403, "Only editors can mark a campaign as published.")
            if any(i.status != "published" for i in live) or not live:
                raise HTTPException(409, "Every non-cancelled item must be published first.")
        c.status = status
    db.commit()
    audit(db, user, "campaign_update", "campaign", c.slug, ", ".join(list(changes) + ([f"status → {status}"] if status else [])) or "no changes")
    return campaign_out(db, c)


@router.delete("/campaigns/{slug}")
def archive_campaign(slug: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _staff(user)
    c = _get(db, slug)
    c.status = "archived"
    db.commit()
    audit(db, user, "campaign_archive", "campaign", c.slug, "Archived")
    return {"ok": True, "status": "archived"}


def _check_content(db: Session, cid: int | None) -> GeneratedContent | None:
    if cid is None:
        return None
    content = db.get(GeneratedContent, cid)
    if not content:
        raise HTTPException(422, "Linked content not found.")
    return content


@router.post("/campaigns/{slug}/items")
def add_item(slug: str, body: ItemIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _staff(user)
    c = _get(db, slug)
    if c.status == "archived":
        raise HTTPException(409, "Archived campaigns cannot be changed.")
    content = _check_content(db, body.content_id)
    it = CampaignItem(campaign_id=c.id, content_id=content.id if content else None, title=body.title.strip(),
                      content_type=body.content_type or (content.format if content else ""), channel=body.channel,
                      audience=body.audience, scheduled_for=body.scheduled_for, notes=body.notes,
                      status="published" if content and content.status == "published" else "planned")
    db.add(it)
    db.commit()
    audit(db, user, "campaign_item_add", "campaign", c.slug, it.title)
    return item_out(db, it)


def _item(db: Session, slug: str, item_id: int) -> tuple[Campaign, CampaignItem]:
    c = _get(db, slug)
    it = db.get(CampaignItem, item_id)
    if not it or it.campaign_id != c.id:
        raise HTTPException(404, "Calendar item not found.")
    return c, it


@router.patch("/campaigns/{slug}/items/{item_id}")
def update_item(slug: str, item_id: int, body: ItemPatch, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _staff(user)
    c, it = _item(db, slug, item_id)
    if it.status == "published" and body.status in {"planned", "cancelled"}:
        raise HTTPException(409, "Published items cannot be un-published or cancelled from the calendar.")
    changes = body.model_dump(exclude_unset=True)
    status = changes.pop("status", None)
    if "content_id" in changes:
        _check_content(db, changes["content_id"])
    for k, v in changes.items():
        setattr(it, k, v)
    db.flush()
    if status == "scheduled":
        content = db.get(GeneratedContent, it.content_id) if it.content_id else None
        if not content or content.status not in READY_CONTENT:
            raise HTTPException(409, "Only content approved by an editor can be scheduled. Submit it for review first.")
        if not it.scheduled_for:
            raise HTTPException(422, "Pick a date before scheduling.")
        it.status = "published" if content.status == "published" else "scheduled"
    elif status:
        it.status = status
    db.commit()
    audit(db, user, "campaign_item_update", "campaign", c.slug, f"{it.title}: " + ", ".join(list(changes) + ([f"status → {status}"] if status else [])))
    return item_out(db, it)


@router.post("/campaigns/{slug}/items/{item_id}/publish")
def publish_item(slug: str, item_id: int, db: Session = Depends(get_db), user: User = Depends(require_permission("publish"))):
    """Publishes through the Review Center's publish transition — never bypasses editorial approval."""
    from app.api.workflow import _transition

    c, it = _item(db, slug, item_id)
    content = db.get(GeneratedContent, it.content_id) if it.content_id else None
    if not content:
        raise HTTPException(409, "Link approved content to this item first.")
    if content.status not in READY_CONTENT:
        raise HTTPException(409, f"Content is '{content.status.replace('_', ' ')}'. It must be approved in the Review Center before publishing.")
    channels = CAMPAIGN_CHANNELS[it.channel]["publish_as"]
    if content.status == "approved":
        _transition(db, user, content, "publish", ReviewAction(channels=channels,
                                                              comment=f"Published from campaign “{c.name}” ({CAMPAIGN_CHANNELS[it.channel]['label']})"))
    it.status = "published"
    if not it.scheduled_for:
        it.scheduled_for = datetime.now(timezone.utc).date()
    db.commit()
    audit(db, user, "campaign_item_publish", "campaign", c.slug, it.title)
    return item_out(db, it)


@router.get("/calendar")
def calendar(start: date | None = None, end: date | None = None, campaign: str | None = Query(None, max_length=160),
             db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _staff(user)
    today = datetime.now(timezone.utc).date()
    start = start or today.replace(day=1) - timedelta(days=7)
    end = end or (start + timedelta(days=75))
    if (end - start).days > 400:
        raise HTTPException(422, "Choose a range of at most about a year.")
    stmt = select(CampaignItem).where(CampaignItem.scheduled_for >= start, CampaignItem.scheduled_for <= end)
    camps = {c.id: c for c in db.scalars(select(Campaign))}
    events = []
    for it in db.scalars(stmt.order_by(CampaignItem.scheduled_for)):
        cp = camps.get(it.campaign_id)
        if not cp or cp.status == "archived" or (campaign and cp.slug != campaign):
            continue
        events.append({**item_out(db, it), "campaign": {"slug": cp.slug, "name": cp.name, "is_demo": cp.is_demo}})
    return {"start": start.isoformat(), "end": end.isoformat(), "events": events,
            "campaigns": [{"slug": c.slug, "name": c.name} for c in camps.values() if c.status != "archived"]}


# ------------------------------------------------------------------ engagement tracking + analytics
@router.post("/outreach/{cid}/track", dependencies=[Depends(rate_limit("ai"))])
def track_event(cid: int, body: TrackIn, db: Session = Depends(get_db), user: User | None = Depends(get_current_user_optional)):
    c = db.get(GeneratedContent, cid)
    if not c or c.status != "published":
        raise HTTPException(404, "Published content not found.")
    camp = db.scalar(select(CampaignItem.campaign_id).where(CampaignItem.content_id == cid))
    db.add(OutreachEvent(content_id=cid, campaign_id=camp, event=body.event, channel=body.channel[:32] or "website",
                         audience=c.audience or "", is_demo=False))
    db.commit()
    return {"ok": True}


def _rate(a: int, b: int) -> float | None:
    return round(a / b, 4) if b else None


@router.get("/outreach-analytics")
def outreach_analytics(include_demo: bool = True, days: int = Query(120, ge=7, le=730), db: Session = Depends(get_db),
                       user: User = Depends(get_current_user)):
    if not (can(user, "view_analytics") or can(user, "review") or can(user, "generate_content")):
        raise HTTPException(403, "Outreach analytics are available to staff roles.")
    since = datetime.now(timezone.utc) - timedelta(days=days)
    rows = db.scalars(select(OutreachEvent).where(OutreachEvent.created_at >= since)).all()
    demo_n = sum(r.count for r in rows if r.is_demo)
    live_n = sum(r.count for r in rows if not r.is_demo)
    if not include_demo:
        rows = [r for r in rows if not r.is_demo]
    contents = {c.id: c for c in db.scalars(select(GeneratedContent))}
    camps = {c.id: c for c in db.scalars(select(Campaign))}
    cat = build_catalog(db, user)

    def blank():
        return {"view": 0, "click": 0, "share": 0, "complete": 0}

    totals = blank()
    by_content, by_campaign, by_audience, by_channel, by_format, by_month = (defaultdict(blank) for _ in range(6))
    topic_views: Counter = Counter()
    for r in rows:
        totals[r.event] += r.count
        c = contents.get(r.content_id)
        by_content[r.content_id][r.event] += r.count
        by_campaign[r.campaign_id or 0][r.event] += r.count
        by_audience[(c.audience if c else "") or r.audience or "unspecified"][r.event] += r.count
        by_channel[r.channel][r.event] += r.count
        by_format[c.format if c else "unknown"][r.event] += r.count
        by_month[r.created_at.strftime("%Y-%m")][r.event] += r.count
        if r.event == "view" and c and c.resource_id:
            card = cat.card(c.resource_type, c.resource_id)
            for t in (card or {}).get("topics", []):
                topic_views[t] += r.count

    def summarise(d: dict) -> dict:
        return {**d, "engagement_rate": _rate(d["click"] + d["share"], d["view"]), "completion_rate": _rate(d["complete"], d["view"])}

    content_rows = []
    for cid, d in by_content.items():
        c = contents.get(cid)
        if c:
            content_rows.append({"id": cid, "title": c.title, "format": c.format, "audience": c.audience,
                                 "published_at": c.published_at.isoformat() if c.published_at else None, **summarise(d)})
    content_rows.sort(key=lambda x: -x["view"])
    campaign_rows = [{"id": k, "name": camps[k].name if k in camps else "Not in a campaign",
                      "slug": camps[k].slug if k in camps else None, **summarise(d)} for k, d in by_campaign.items()]
    campaign_rows.sort(key=lambda x: -x["view"])
    # research → content conversion (from the real workflow tables, never demo events)
    public_research = [c for c in cat.cards.values() if c["type"] in {"document", "dataset", "expedition", "station"}]
    with_content = {(c.resource_type, c.resource_id) for c in contents.values() if c.resource_id}
    published = [c for c in contents.values() if c.status == "published"]
    basis_label = "DEMO METRICS" if include_demo and demo_n and not live_n else \
        "MIXED — includes DEMO METRICS" if include_demo and demo_n else "LIVE METRICS"
    return {
        "basis": {"label": basis_label, "demo_events": demo_n, "live_events": live_n, "include_demo": include_demo,
                  "note": "Demo metrics are seeded, synthetic engagement used to demonstrate the dashboard. They are not real statistics."
                  if include_demo and demo_n else "Only engagement recorded by this deployment's public pages."},
        "window_days": days, "totals": summarise(totals),
        "campaigns": campaign_rows, "content": content_rows[:15],
        "audiences": [{"key": k, "label": AUDIENCES.get(k, k.title()), **summarise(d)} for k, d in sorted(by_audience.items(), key=lambda x: -x[1]["view"])],
        "channels": [{"key": k, "label": CHANNELS.get(k, {}).get("label", k), "live": CHANNELS.get(k, {}).get("status") == "live", **summarise(d)}
                     for k, d in sorted(by_channel.items(), key=lambda x: -x[1]["view"])],
        "formats": [{"key": k, **summarise(d)} for k, d in sorted(by_format.items(), key=lambda x: -x[1]["view"])],
        "months": [{"month": k, **d} for k, d in sorted(by_month.items())],
        "popular_topics": [{"topic": t, "views": v} for t, v in topic_views.most_common(8)],
        "conversion": {
            "research_records": len(public_research),
            "records_with_outreach": sum(1 for c in public_research if (c["type"], c["id"]) in with_content),
            "rate": _rate(sum(1 for c in public_research if (c["type"], c["id"]) in with_content), len(public_research)),
            "drafts_generated": len(contents), "published": len(published),
            "publish_rate": _rate(len(published), len(contents)),
            "note": "Computed from the content workflow tables (real records, including seeded demo content items).",
        },
    }
