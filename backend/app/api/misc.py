"""Search, notifications, saved items ('My Knowledge'), education and health endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.api.knowledge import _common, _list
from app.auth.security import get_current_user, get_current_user_optional
from app.core.config import settings
from app.core.database import VectorState, db_healthy, get_db
from app.models import Notification, SavedItem, SearchLog, User
from app.rag.embeddings import get_provider
from app.rag.llm import ai_status
from app.schemas.common import SavedCreate, SemanticSearchRequest
from app.search.service import search_resources, suggest
from app.seed.education import LEARNING_PATHS, QUIZZES
from app.services.audit import track
from app.services.catalog import Filters, build_catalog
from app.services.serializers import iso

router = APIRouter(tags=["misc"])


# ------------------------------------------------------------------ search
@router.get("/api/search")
def search(params: dict = Depends(_common), db: Session = Depends(get_db), user: User | None = Depends(get_current_user_optional)):
    res = _list(db, user, None, **params)
    if params["q"]:
        db.add(SearchLog(user_id=user.id if user else None, query=params["q"][:500], mode=params["mode"],
                         filters=res["filters"], result_count=res["total"]))
        track(db, "search", meta={"query": params["q"][:200]}, user=user, commit=False)
        db.commit()
    return res


@router.post("/api/search/semantic")
def semantic_search(body: SemanticSearchRequest, db: Session = Depends(get_db),
                    user: User | None = Depends(get_current_user_optional)):
    return search_resources(db, user, body.query, "semantic", Filters(), page=body.page, page_size=body.page_size)


@router.get("/api/search/suggest")
def search_suggest(q: str = Query("", max_length=200), db: Session = Depends(get_db),
                   user: User | None = Depends(get_current_user_optional)):
    return {"suggestions": suggest(build_catalog(db, user), q)}


@router.get("/api/search/history")
def search_history(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = db.scalars(select(SearchLog).where(SearchLog.user_id == user.id).order_by(SearchLog.created_at.desc()).limit(40))
    seen, out = set(), []
    for r in rows:
        if r.query.lower() not in seen:
            seen.add(r.query.lower())
            out.append({"query": r.query, "mode": r.mode, "results": r.result_count, "at": iso(r.created_at)})
    return {"results": out[:12]}


# ------------------------------------------------------------------ notifications
def _notif_stmt(user: User):
    return select(Notification).where(or_(Notification.user_id == user.id,
                                          (Notification.user_id.is_(None)) & (Notification.role.in_([user.role_name, "all"]))))


@router.get("/api/notifications")
def notifications(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = db.scalars(_notif_stmt(user).order_by(Notification.created_at.desc()).limit(30)).all()
    return {"unread": sum(1 for r in rows if not r.read),
            "results": [{"id": r.id, "title": r.title, "body": r.body, "link": r.link, "kind": r.kind, "read": r.read,
                         "at": iso(r.created_at)} for r in rows]}


@router.post("/api/notifications/{nid}/read")
def mark_read(nid: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    n = db.scalar(_notif_stmt(user).where(Notification.id == nid))
    if not n:
        raise HTTPException(404, "Notification not found.")
    n.read = True
    db.commit()
    return {"ok": True}


@router.post("/api/notifications/read-all")
def mark_all(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    for n in db.scalars(_notif_stmt(user)):
        n.read = True
    db.commit()
    return {"ok": True}


# ------------------------------------------------------------------ saved items
@router.get("/api/saved")
def saved(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = db.scalars(select(SavedItem).where(SavedItem.user_id == user.id).order_by(SavedItem.created_at.desc()))
    return {"results": [{"id": s.id, "item_type": s.item_type, "item_slug": s.item_slug, "label": s.label,
                         "query": s.query, "at": iso(s.created_at)} for s in rows]}


@router.post("/api/saved")
def save(body: SavedCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    existing = db.scalar(select(SavedItem).where(SavedItem.user_id == user.id, SavedItem.item_type == body.item_type,
                                                 SavedItem.item_slug == body.item_slug, SavedItem.label == body.label))
    if existing:
        return {"id": existing.id, "already_saved": True}
    s = SavedItem(user_id=user.id, item_type=body.item_type, item_slug=body.item_slug, label=body.label, query=body.query)
    db.add(s)
    db.commit()
    return {"id": s.id, "already_saved": False}


@router.delete("/api/saved/{sid}")
def unsave(sid: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    s = db.get(SavedItem, sid)
    if not s or s.user_id != user.id:
        raise HTTPException(404, "Saved item not found.")
    db.delete(s)
    db.commit()
    return {"ok": True}


# ------------------------------------------------------------------ education
@router.get("/api/education")
def education(db: Session = Depends(get_db), user: User | None = Depends(get_current_user_optional)):
    cat = build_catalog(db, user)
    paths = []
    for p in LEARNING_PATHS:
        lessons = []
        for lesson in p["lessons"]:
            res = []
            for rtype, slug in lesson["resources"]:
                key = cat.by_slug.get((rtype, slug))
                if key:
                    c = cat.cards[key]
                    res.append({k: c[k] for k in ("type", "slug", "title", "kind", "url", "region", "year", "extra")})
            lessons.append({**lesson, "resources": res})
        quiz = []
        for q in QUIZZES.get(p["level"], []):
            key = cat.by_slug.get(("document", q["source"]))
            quiz.append({**q, "source_title": cat.cards[key]["title"] if key else q["source"],
                         "source_url": f"/resources/{q['source']}"})
        paths.append({**p, "lessons": lessons, "quiz": quiz})
    return {"paths": paths}


# ------------------------------------------------------------------ health
def health_payload(db: Session) -> dict:
    ok_db = db_healthy()
    provider = None
    try:
        provider = get_provider(db) if ok_db else None
    except Exception:
        provider = None
    ai = ai_status()
    storage_ok = True
    try:
        from pathlib import Path
        Path(settings.STORAGE_DIR).mkdir(parents=True, exist_ok=True)
    except OSError:
        storage_ok = False
    return {
        "status": "ok" if ok_db else "degraded",
        "api": "ok",
        "database": {"status": "ok" if ok_db else "unavailable", "engine": "postgresql" if settings.is_postgres else "sqlite"},
        "vector_search": {"status": "ok" if provider else "keyword-only",
                          "backend": "pgvector" if VectorState.pgvector else "in-process numpy",
                          "embedding_model": provider.name if provider else None},
        "ai_provider": {"status": "configured" if ai["llm_configured"] else "fallback",
                        "model": ai["llm_model"], "fallback": ai["fallback"]},
        "storage": {"status": "ok" if storage_ok else "unavailable",
                    "backend": "s3-compatible" if settings.STORAGE_URL else "local disk"},
        "demo_mode": settings.DEMO_MODE,
        "environment": settings.ENVIRONMENT,
    }


@router.get("/health")
def health(db: Session = Depends(get_db)):
    return health_payload(db)


@router.get("/api/health")
def api_health(db: Session = Depends(get_db)):
    return health_payload(db)
