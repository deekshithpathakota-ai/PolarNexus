"""Research Story API: build, view, edit and publish connected, evidence-grounded research narratives."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.security import can, get_current_user_optional, require_permission
from app.core.database import get_db
from app.models import ResearchStory, User
from app.services import stories as svc
from app.services.audit import audit, track
from app.services.catalog import build_catalog

router = APIRouter(prefix="/api/stories", tags=["research-stories"])

ITEM_TYPES = {"document", "dataset", "media", "expedition", "station", "researcher", "topic", "activity"}


class StoryItem(BaseModel):
    type: str = Field(pattern="^(document|dataset|media|expedition|station|researcher|topic|activity)$")
    slug: str | None = Field(default=None, max_length=160)
    id: int | None = None
    role: str = Field(default="", max_length=60)
    note: str = Field(default="", max_length=500)


class StoryCreate(BaseModel):
    title: str | None = Field(default=None, max_length=300)
    seed_type: str | None = Field(default=None, pattern="^(document|dataset|media|expedition|station|researcher|topic|activity)$")
    seed_slug: str | None = Field(default=None, max_length=160)
    items: list[StoryItem] | None = None


class StoryUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=300)
    items: list[StoryItem] | None = None
    status: str | None = Field(default=None, pattern="^(draft|published|archived)$")
    regenerate: bool = False


def _resolve(cat, items: list[StoryItem]) -> list[dict]:
    out = []
    for it in items:
        key = (it.type, it.id) if it.id else cat.by_slug.get((it.type, it.slug or ""))
        if not key or not cat.card(*key):
            raise HTTPException(422, f"Unknown or inaccessible {it.type}: {it.slug or it.id}.")
        out.append({"type": key[0], "id": key[1], "role": it.role, "note": it.note})
    return out


def _get(db: Session, slug: str) -> ResearchStory:
    s = db.scalar(select(ResearchStory).where(ResearchStory.slug == slug))
    if not s:
        raise HTTPException(404, "Research story not found.")
    return s


def _can_edit(user: User | None, s: ResearchStory) -> bool:
    return bool(user and (s.created_by == user.id or can(user, "edit_content") or can(user, "manage_repository")))


@router.get("")
def list_stories(mine: bool = False, db: Session = Depends(get_db), user: User | None = Depends(get_current_user_optional)):
    cat = build_catalog(db, user)
    rows = db.scalars(select(ResearchStory).order_by(ResearchStory.updated_at.desc())).all()
    out = []
    for s in rows:
        visible = s.status == "published" or _can_edit(user, s)
        if not visible or (mine and (not user or s.created_by != user.id)) or (s.status == "archived" and not _can_edit(user, s)):
            continue
        out.append(svc.story_out(db, cat, s, full=False))
    return {"results": out, "total": len(out)}


@router.get("/suggest")
def suggest(seed_type: str = Query(..., pattern="^(document|dataset|media|expedition|station|researcher|topic|activity)$"),
            seed_slug: str = Query(..., max_length=160), db: Session = Depends(get_db),
            user: User | None = Depends(get_current_user_optional)):
    """Preview of the items a story would connect, before saving."""
    cat = build_catalog(db, user)
    key = cat.by_slug.get((seed_type, seed_slug))
    if not key:
        raise HTTPException(404, "Starting record not found.")
    items = svc.suggest_items(cat, *key)
    cards = [{**{k: cat.card(i["type"], i["id"])[k] for k in ("type", "id", "slug", "title", "kind", "url", "verification",
                                                               "verification_label", "is_demo")}, "role": i["role"]} for i in items]
    return {"title": svc.default_title(cat, *key), "items": cards}


@router.post("")
def create(body: StoryCreate, db: Session = Depends(get_db), user: User = Depends(require_permission("generate_content"))):
    cat = build_catalog(db, user)
    seed = cat.by_slug.get((body.seed_type, body.seed_slug or "")) if body.seed_type else None
    if body.seed_type and not seed:
        raise HTTPException(404, "Starting record not found.")
    items = _resolve(cat, body.items) if body.items is not None else None
    if not seed and not items:
        raise HTTPException(422, "Choose a starting record or add at least one item.")
    title = (body.title or "").strip() or (svc.default_title(cat, *seed) if seed else "Research story")
    s = svc.create_story(db, cat, title, seed[0] if seed else None, seed[1] if seed else None, items, user.id)
    audit(db, user, "story_create", "story", s.slug, f"{len(s.items)} items")
    return svc.story_out(db, cat, s)


@router.get("/{slug}")
def get_story(slug: str, db: Session = Depends(get_db), user: User | None = Depends(get_current_user_optional)):
    s = _get(db, slug)
    if s.status != "published" and not _can_edit(user, s):
        raise HTTPException(404, "Research story not found.")
    s.views = (s.views or 0) + 1
    db.commit()
    track(db, "view", "story", s.id, user)
    out = svc.story_out(db, build_catalog(db, user), s)
    out["can_edit"] = _can_edit(user, s)
    return out


@router.patch("/{slug}")
def update(slug: str, body: StoryUpdate, db: Session = Depends(get_db), user: User = Depends(require_permission("generate_content"))):
    s = _get(db, slug)
    if not _can_edit(user, s):
        raise HTTPException(403, "Only the author or an editor can change this story.")
    cat = build_catalog(db, user)
    changed = []
    if body.title is not None and body.title.strip():
        s.title = body.title.strip()[:300]
        changed.append("title")
    if body.items is not None:
        s.items = _resolve(cat, body.items)
        changed.append("items")
    if body.items is not None or body.regenerate:
        s.summaries = svc.build_summaries(db, cat, s.items)
        changed.append("summaries")
    if body.status is not None and body.status != s.status:
        if body.status == "published" and not (can(user, "publish") or can(user, "manage_repository")):
            raise HTTPException(403, "An editor must publish research stories.")
        s.status = body.status
        changed.append(f"status → {body.status}")
    db.commit()
    audit(db, user, "story_update", "story", s.slug, ", ".join(changed) or "no changes")
    out = svc.story_out(db, cat, s)
    out["can_edit"] = True
    return out


@router.delete("/{slug}")
def archive(slug: str, db: Session = Depends(get_db), user: User = Depends(require_permission("generate_content"))):
    """Archives (never deletes) a story."""
    s = _get(db, slug)
    if not _can_edit(user, s):
        raise HTTPException(403, "Only the author or an editor can archive this story.")
    s.status = "archived"
    db.commit()
    audit(db, user, "story_archive", "story", s.slug, "Archived")
    return {"ok": True, "status": "archived"}
