"""Institutional Activities: workshops, seminars, outreach events, briefings, announcements and achievements."""
from __future__ import annotations

import datetime as dt
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.auth.security import get_current_user_optional, require_permission
from app.core.database import get_db
from app.models import (
    Dataset,
    Document,
    DocumentChunk,
    Expedition,
    InstitutionalActivity,
    Media,
    Provenance,
    Researcher,
    ResourceLink,
    ResourceTopic,
    Station,
    Topic,
    User,
)
from app.rag.indexer import index_resource, remove_resource
from app.services.audit import audit, track
from app.services.catalog import ACTIVITY_TYPES, build_catalog
from app.services.provenance import ensure_for, get_provenance
from app.services.serializers import activity_out
from app.utils.text import slugify

router = APIRouter(prefix="/api/activities", tags=["activities"])

STATUSES = ["upcoming", "ongoing", "completed", "cancelled", "archived"]
REGIONS = ["Antarctic", "Arctic", "Southern Ocean", "Himalaya", "India"]
LINKABLE = {"researchers": (Researcher, "researcher", "involves"), "expeditions": (Expedition, "expedition", "related_expedition"),
            "stations": (Station, "station", "held_at"), "documents": (Document, "document", "presents"),
            "datasets": (Dataset, "dataset", "uses_dataset"), "media": (Media, "media", "features_media")}


class ActivityIn(BaseModel):
    title: str = Field(min_length=5, max_length=300)
    description: str = Field(min_length=20, max_length=8000)
    activity_type: Literal[tuple(ACTIVITY_TYPES)]  # type: ignore[valid-type]
    date: dt.date
    end_date: dt.date | None = None
    location: str = Field(default="", max_length=255)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    region: Literal[tuple(REGIONS)] = "India"  # type: ignore[valid-type]
    organisation: str = Field(min_length=2, max_length=255)
    department: str = Field(default="", max_length=255)
    audience: str = Field(default="", max_length=120)
    outcomes: list[str] = Field(default_factory=list, max_length=12)
    status: Literal["upcoming", "ongoing", "completed", "cancelled"] = "completed"
    visibility: Literal["public", "internal"] = "public"
    featured: bool = False
    cover_scene: str = Field(default="station", max_length=32, pattern=r"^[a-z0-9-]+$")
    topics: list[str] = Field(default_factory=list, max_length=10)
    researchers: list[str] = Field(default_factory=list, max_length=20)
    expeditions: list[str] = Field(default_factory=list, max_length=20)
    stations: list[str] = Field(default_factory=list, max_length=20)
    documents: list[str] = Field(default_factory=list, max_length=20)
    datasets: list[str] = Field(default_factory=list, max_length=20)
    media: list[str] = Field(default_factory=list, max_length=20)

    @field_validator("end_date")
    @classmethod
    def end_after_start(cls, v, info):
        start = info.data.get("date")
        if v and start and v < start:
            raise ValueError("End date must be on or after the start date.")
        return v

    @field_validator("outcomes")
    @classmethod
    def clean_outcomes(cls, v: list[str]) -> list[str]:
        return [o.strip()[:300] for o in v if o.strip()]


class ActivityPatch(BaseModel):
    title: str | None = Field(default=None, min_length=5, max_length=300)
    description: str | None = Field(default=None, min_length=20, max_length=8000)
    activity_type: Literal[tuple(ACTIVITY_TYPES)] | None = None  # type: ignore[valid-type]
    date: dt.date | None = None
    end_date: dt.date | None = None
    location: str | None = Field(default=None, max_length=255)
    organisation: str | None = Field(default=None, min_length=2, max_length=255)
    department: str | None = Field(default=None, max_length=255)
    audience: str | None = Field(default=None, max_length=120)
    outcomes: list[str] | None = Field(default=None, max_length=12)
    status: Literal["upcoming", "ongoing", "completed", "cancelled", "archived"] | None = None
    visibility: Literal["public", "internal"] | None = None
    featured: bool | None = None


def _get(db: Session, slug: str) -> InstitutionalActivity:
    a = db.scalar(select(InstitutionalActivity).where(InstitutionalActivity.slug == slug))
    if not a:
        raise HTTPException(404, "Activity not found.")
    return a


@router.get("/types")
def activity_types():
    return {"types": [{"key": k, "label": v} for k, v in ACTIVITY_TYPES.items()], "statuses": STATUSES}


@router.get("")
def list_activities(q: str | None = Query(None, max_length=200), activity_type: list[str] | None = Query(None),
                    year: int | None = Query(None, ge=1900, le=2100), organisation: str | None = Query(None, max_length=255),
                    location: str | None = Query(None, max_length=255), topic: str | None = Query(None, max_length=120),
                    verification: list[str] | None = Query(None), status: str | None = Query(None, max_length=24),
                    featured: bool | None = None,
                    sort: str = Query("newest", pattern="^(newest|oldest|alphabetical|views|upcoming)$"),
                    page: int = Query(1, ge=1, le=500), page_size: int = Query(12, ge=1, le=60),
                    db: Session = Depends(get_db), user: User | None = Depends(get_current_user_optional)):
    cat = build_catalog(db, user)
    from app.services import provenance as prov

    cards = [c for c in cat.cards.values() if c["type"] == "activity"]
    rows = {a.id: a for a in db.scalars(select(InstitutionalActivity))}
    facet_types: dict[str, int] = {}
    facet_orgs: dict[str, int] = {}
    facet_years: dict[int, int] = {}
    for c in cards:
        a = rows[c["id"]]
        facet_types[a.activity_type] = facet_types.get(a.activity_type, 0) + 1
        facet_orgs[a.organisation] = facet_orgs.get(a.organisation, 0) + 1
        if a.year:
            facet_years[a.year] = facet_years.get(a.year, 0) + 1
    out = []
    ql = (q or "").lower().strip()
    for c in cards:
        a = rows[c["id"]]
        if activity_type and a.activity_type not in activity_type:
            continue
        if year and a.year != year:
            continue
        if organisation and organisation.lower() not in a.organisation.lower():
            continue
        if location and location.lower() not in (a.location or "").lower():
            continue
        if topic and topic not in c["topic_slugs"]:
            continue
        if status and a.status != status:
            continue
        if featured is not None and a.featured != featured:
            continue
        if verification and not any(prov.FILTERS.get(v, lambda _p: False)(
                {"verification_status": c["verification"], "source_type": ""}) for v in verification):
            continue
        if ql and not any(ql in (x or "").lower() for x in (a.title, a.description, a.organisation, a.location, a.audience)):
            continue
        out.append({**activity_out(a), "topics": c["topics"], "topic_slugs": c["topic_slugs"],
                    "verification": c["verification"], "verification_label": c["verification_label"],
                    "related_count": len(cat.links.get(("activity", a.id), ()))})
    keyfn = {
        "newest": lambda x: (x["date"] or "",),
        "oldest": lambda x: (x["date"] or "9999",),
        "alphabetical": lambda x: (x["title"].lower(),),
        "views": lambda x: (x["views"],),
        "upcoming": lambda x: (x["status"] != "upcoming", x["date"] or ""),
    }[sort]
    out.sort(key=keyfn, reverse=sort in {"newest", "views"})
    total = len(out)
    return {"total": total, "page": page, "page_size": page_size, "pages": max(1, -(-total // page_size)),
            "results": out[(page - 1) * page_size: page * page_size],
            "facets": {"activity_types": {k: facet_types[k] for k in ACTIVITY_TYPES if k in facet_types},
                       "organisations": dict(sorted(facet_orgs.items(), key=lambda x: -x[1])),
                       "years": dict(sorted(facet_years.items(), reverse=True))},
            "type_labels": ACTIVITY_TYPES}


@router.get("/{slug}")
def get_activity(slug: str, db: Session = Depends(get_db), user: User | None = Depends(get_current_user_optional)):
    a = _get(db, slug)
    cat = build_catalog(db, user)
    card = cat.card("activity", a.id)
    if not card:
        raise HTTPException(404, "Activity not found or not available to your role.")
    a.views = (a.views or 0) + 1
    track(db, "view", "activity", a.id, user, commit=False)
    db.commit()
    from app.api.knowledge import _related_block, _topics

    out = activity_out(a)
    out.update(topics=_topics(db, "activity", a.id), related=_related_block(cat, "activity", a.id),
               provenance=get_provenance(db, "activity", a), verification=card["verification"],
               verification_label=card["verification_label"])
    return out


def _set_links(db: Session, a: InstitutionalActivity, body: ActivityIn) -> None:
    db.execute(delete(ResourceLink).where(ResourceLink.source_type == "activity", ResourceLink.source_id == a.id))
    db.execute(delete(ResourceTopic).where(ResourceTopic.resource_type == "activity", ResourceTopic.resource_id == a.id))
    for field, (model, rtype, rel) in LINKABLE.items():
        slugs = list(dict.fromkeys(getattr(body, field)))
        if not slugs:
            continue
        found = db.scalars(select(model).where(model.slug.in_(slugs))).all()
        missing = set(slugs) - {o.slug for o in found}
        if missing:
            raise HTTPException(422, f"Unknown {field}: {', '.join(sorted(missing))}")
        for o in found:
            db.add(ResourceLink(source_type="activity", source_id=a.id, target_type=rtype, target_id=o.id, relation=rel))
    for t in db.scalars(select(Topic).where(Topic.slug.in_(body.topics))):
        db.add(ResourceTopic(resource_type="activity", resource_id=a.id, topic_id=t.id))


@router.post("")
def create_activity(body: ActivityIn, db: Session = Depends(get_db), user: User = Depends(require_permission("manage_repository"))):
    slug = slugify(body.title)[:150]
    if db.scalar(select(InstitutionalActivity).where(InstitutionalActivity.slug == slug)):
        slug = f"{slug}-{body.date.isoformat()}"
    if db.scalar(select(InstitutionalActivity).where(InstitutionalActivity.slug == slug)):
        raise HTTPException(409, "An activity with this title and date already exists.")
    data = body.model_dump(exclude={"topics", *LINKABLE})
    a = InstitutionalActivity(slug=slug, **data, year=body.date.year, is_demo=False, created_by=user.id)
    db.add(a)
    db.flush()
    _set_links(db, a, body)
    db.commit()
    ensure_for(db, "activity", a)
    index_resource(db, "activity", a.id)
    audit(db, user, "create", "activity", a.slug, f"{ACTIVITY_TYPES[a.activity_type]}: {a.title}")
    return activity_out(a)


@router.put("/{slug}")
def replace_activity(slug: str, body: ActivityIn, db: Session = Depends(get_db),
                     user: User = Depends(require_permission("manage_repository"))):
    a = _get(db, slug)
    for k, v in body.model_dump(exclude={"topics", *LINKABLE}).items():
        setattr(a, k, v)
    a.year = body.date.year
    _set_links(db, a, body)
    db.commit()
    index_resource(db, "activity", a.id)
    audit(db, user, "update", "activity", a.slug, "Activity updated (details and links)")
    return activity_out(a)


@router.patch("/{slug}")
def patch_activity(slug: str, body: ActivityPatch, db: Session = Depends(get_db),
                   user: User = Depends(require_permission("manage_repository"))):
    a = _get(db, slug)
    changes = body.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(422, "No changes supplied.")
    if "end_date" in changes and changes["end_date"] and changes["end_date"] < (changes.get("date") or a.date):
        raise HTTPException(422, "End date must be on or after the start date.")
    old_visibility, old_status = a.visibility, a.status
    for k, v in changes.items():
        setattr(a, k, [o.strip() for o in v if o.strip()] if k == "outcomes" else v)
    if "date" in changes and a.date:
        a.year = a.date.year
    db.commit()
    if a.status == "archived":
        remove_resource(db, "activity", a.id)
    else:
        index_resource(db, "activity", a.id)
    action = ("archive" if a.status == "archived" and old_status != "archived" else
              "restore" if old_status == "archived" and a.status != "archived" else
              "feature" if set(changes) == {"featured"} else
              "visibility_change" if "visibility" in changes and a.visibility != old_visibility else "update")
    audit(db, user, action, "activity", a.slug, "Changed: " + ", ".join(sorted(changes)))
    return activity_out(a)


@router.delete("/{slug}")
def delete_activity(slug: str, db: Session = Depends(get_db), user: User = Depends(require_permission("manage_repository"))):
    a = _get(db, slug)
    aid, title = a.id, a.title
    db.execute(delete(ResourceLink).where(((ResourceLink.source_type == "activity") & (ResourceLink.source_id == aid)) |
                                          ((ResourceLink.target_type == "activity") & (ResourceLink.target_id == aid))))
    db.execute(delete(ResourceTopic).where(ResourceTopic.resource_type == "activity", ResourceTopic.resource_id == aid))
    db.execute(delete(DocumentChunk).where(DocumentChunk.resource_type == "activity", DocumentChunk.resource_id == aid))
    db.execute(delete(Provenance).where(Provenance.resource_type == "activity", Provenance.resource_id == aid))
    db.delete(a)
    db.commit()
    remove_resource(db, "activity", aid)
    audit(db, user, "delete", "activity", slug, f"Permanently deleted: {title}")
    return {"ok": True, "deleted": True}
