"""Administration: repository management, users & roles, audit logs, analytics, index & demo reset."""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.auth.security import ROLE_INFO, ROLE_PERMISSIONS, can, get_current_user, hash_password, require_permission
from app.core.config import settings
from app.core.database import get_db
from app.models import (
    AIQuery,
    AnalyticsEvent,
    AuditLog,
    Dataset,
    Document,
    DocumentChunk,
    Expedition,
    GeneratedContent,
    InstitutionalActivity,
    Media,
    Provenance,
    ResourceLink,
    ResourceTopic,
    Role,
    SearchLog,
    Station,
    Topic,
    User,
)
from app.rag.indexer import index_document, index_resource, reindex_all
from app.schemas.common import DocumentCreate, MetadataUpdate, TopicCreate, UserCreate, UserUpdate
from app.services.audit import audit, notify
from app.services.serializers import iso, user_out
from app.utils.text import slugify

router = APIRouter(prefix="/api", tags=["admin"])
EDITABLE = {"document": Document, "dataset": Dataset, "media": Media, "expedition": Expedition, "station": Station,
            "activity": InstitutionalActivity}


# ------------------------------------------------------------------ repository
@router.get("/admin/repository")
def repository(kind: str = Query("document", pattern="^(document|dataset|media|expedition|station|activity)$"),
               q: str | None = None, status: str | None = None, page: int = Query(1, ge=1),
               page_size: int = Query(20, le=100), db: Session = Depends(get_db),
               user: User = Depends(get_current_user)):
    if not (can(user, "manage_repository") or (kind == "document" and can(user, "manage_own"))):
        raise HTTPException(403, "Repository management requires the administrator or researcher role.")
    model = EDITABLE[kind]
    rows = db.scalars(select(model).order_by(model.updated_at.desc())).all()
    if kind == "document" and not can(user, "manage_repository"):
        rows = [r for r in rows if r.uploaded_by == user.id]
    if q:
        ql = q.lower()
        rows = [r for r in rows if ql in (getattr(r, "title", None) or getattr(r, "name", "")).lower()]
    if status and hasattr(model, "status"):
        rows = [r for r in rows if r.status == status]
    total = len(rows)
    chunk_counts = dict(db.execute(select(DocumentChunk.resource_id, func.count()).where(DocumentChunk.resource_type == kind)
                                   .group_by(DocumentChunk.resource_id)).all())
    items = []
    for r in rows[(page - 1) * page_size: page * page_size]:
        items.append({
            "id": r.id, "slug": r.slug, "title": getattr(r, "title", None) or r.name, "region": r.region,
            "year": getattr(r, "year", None), "status": getattr(r, "status", "indexed"),
            "visibility": getattr(r, "visibility", "public"), "kind": getattr(r, "doc_type", None) or getattr(r, "media_type", None)
            or getattr(r, "activity_type", None) or getattr(r, "data_type", None) or getattr(r, "program", None)
            or getattr(r, "kind", kind), "processing_status": getattr(r, "processing_status", None),
            "is_demo": getattr(r, "is_demo", not getattr(r, "verified", True)), "views": getattr(r, "views", 0),
            "chunks": chunk_counts.get(r.id, 0), "updated_at": iso(r.updated_at),
            "abstract": getattr(r, "abstract", None) or getattr(r, "description", None) or getattr(r, "objective", ""),
            "keywords": getattr(r, "keywords", []),
        })
    return {"total": total, "page": page, "pages": max(1, -(-total // page_size)), "results": items}


@router.post("/resources")
def create_document(body: DocumentCreate, db: Session = Depends(get_db), user: User = Depends(require_permission("upload"))):
    slug = slugify(body.title)
    if db.scalar(select(Document).where(Document.slug == slug)):
        slug = f"{slug}-{int(datetime.now().timestamp()) % 100000}"
    content = body.content.strip() or f"## Abstract\n{body.abstract}"
    if "## " not in content:
        content = f"## Abstract\n{body.abstract}\n\n## Text\n{content}"
    doc = Document(slug=slug, title=body.title, doc_type=body.doc_type, abstract=body.abstract, content=content,
                   authors=body.authors or [user.name], institution=body.institution or user.institution, region=body.region,
                   year=body.year, keywords=body.keywords, source=f"Added by {user.name}", status="indexed",
                   visibility=body.visibility, language=body.language, is_demo=False, uploaded_by=user.id)
    db.add(doc)
    db.flush()
    for t in db.scalars(select(Topic).where(Topic.slug.in_(body.topics))):
        db.add(ResourceTopic(resource_type="document", resource_id=doc.id, topic_id=t.id))
    db.commit()
    n = index_document(db, doc)
    audit(db, user, "create", "document", doc.slug, f"Created with {n} passages")
    notify(db, "New resource indexed", f"“{doc.title}” was added by {user.name}.", f"/resources/{doc.slug}", "info", role="admin")
    return {"slug": doc.slug, "id": doc.id, "chunks": n}


@router.patch("/admin/resources/{kind}/{rid}")
def update_metadata(kind: str, rid: int, body: MetadataUpdate, db: Session = Depends(get_db),
                    user: User = Depends(get_current_user)):
    model = EDITABLE.get(kind)
    if not model:
        raise HTTPException(404, "Unknown resource type.")
    obj = db.get(model, rid)
    if not obj:
        raise HTTPException(404, "Resource not found.")
    own = kind == "document" and obj.uploaded_by == user.id and can(user, "manage_own")
    if not (can(user, "manage_repository") or own):
        raise HTTPException(403, "You can only edit resources you uploaded.")
    changes = []
    for field in ("title", "abstract", "description", "region", "year", "keywords", "visibility", "status", "doc_type"):
        val = getattr(body, field)
        if val is None:
            continue
        attr = "name" if field == "title" and kind in {"expedition", "station"} else field
        if not hasattr(obj, attr):
            continue
        setattr(obj, attr, val)
        changes.append(field)
    if body.topics is not None:
        db.execute(delete(ResourceTopic).where(ResourceTopic.resource_type == kind, ResourceTopic.resource_id == rid))
        for t in db.scalars(select(Topic).where(Topic.slug.in_(body.topics))):
            db.add(ResourceTopic(resource_type=kind, resource_id=rid, topic_id=t.id))
        changes.append("topics")
    db.commit()
    if kind == "document" and ({"abstract", "title"} & set(changes)):
        if body.abstract and "## Abstract" in (obj.content or ""):
            import re
            obj.content = re.sub(r"(## Abstract\n)(.*?)(\n\n|\n\[\[|\Z)", lambda m: m.group(1) + body.abstract + m.group(3),
                                 obj.content, count=1, flags=re.S)
            db.commit()
        index_document(db, obj)
    elif kind != "document" and ({"description", "title"} & set(changes)):
        index_resource(db, kind, rid)
    audit(db, user, "visibility_change" if changes == ["visibility"] else "metadata_edit", kind,
          getattr(obj, "slug", rid), "Changed: " + ", ".join(changes))
    if changes:
        from app.services import versions

        versions.record(db, kind, obj, "Metadata corrected: " + ", ".join(changes), "", user)
    return {"ok": True, "changed": changes}


@router.delete("/admin/resources/{kind}/{rid}")
def delete_resource(kind: str, rid: int, hard: bool = False, db: Session = Depends(get_db),
                    user: User = Depends(require_permission("manage_repository"))):
    model = EDITABLE.get(kind)
    obj = db.get(model, rid) if model else None
    if not obj:
        raise HTTPException(404, "Resource not found.")
    slug = obj.slug
    if not hard and hasattr(obj, "status"):
        obj.status = "archived"
        db.execute(delete(DocumentChunk).where(DocumentChunk.resource_type == kind, DocumentChunk.resource_id == rid))
        db.commit()
        audit(db, user, "archive", kind, slug, "Archived (removed from search, restorable)")
        from app.rag.vector_store import invalidate_caches
        invalidate_caches()
        return {"ok": True, "archived": True}
    db.execute(delete(ResourceLink).where(((ResourceLink.source_type == kind) & (ResourceLink.source_id == rid)) |
                                          ((ResourceLink.target_type == kind) & (ResourceLink.target_id == rid))))
    db.execute(delete(ResourceTopic).where(ResourceTopic.resource_type == kind, ResourceTopic.resource_id == rid))
    db.execute(delete(DocumentChunk).where(DocumentChunk.resource_type == kind, DocumentChunk.resource_id == rid))
    db.execute(delete(Provenance).where(Provenance.resource_type == kind, Provenance.resource_id == rid))
    files = [getattr(obj, "file_path", ""), getattr(obj, "thumbnail_path", "")] if kind == "media" and not obj.is_demo else []
    db.delete(obj)
    db.commit()
    from app.rag.vector_store import invalidate_caches
    invalidate_caches()
    from pathlib import Path
    root = Path(settings.STORAGE_DIR).resolve()
    for f in files:
        try:
            fp = Path(f).resolve()
            if f and fp.is_file() and fp.is_relative_to(root):
                fp.unlink()
        except OSError:
            pass
    audit(db, user, "delete", kind, slug, "Permanently deleted")
    return {"ok": True, "deleted": True}


@router.post("/admin/resources/{kind}/{rid}/restore")
def restore(kind: str, rid: int, db: Session = Depends(get_db), user: User = Depends(require_permission("manage_repository"))):
    model = EDITABLE.get(kind)
    obj = db.get(model, rid) if model else None
    if not obj or not hasattr(obj, "status"):
        raise HTTPException(404, "Resource not found.")
    obj.status = "completed" if kind == "activity" else "indexed"
    db.commit()
    if kind == "document":
        index_document(db, obj)
    else:
        index_resource(db, kind, rid)
    audit(db, user, "restore", kind, obj.slug, "Restored from archive")
    return {"ok": True}


@router.post("/admin/topics")
def create_topic(body: TopicCreate, db: Session = Depends(get_db), user: User = Depends(require_permission("manage_repository"))):
    slug = slugify(body.name)
    if db.scalar(select(Topic).where(Topic.slug == slug)):
        raise HTTPException(409, "A topic with this name already exists.")
    t = Topic(slug=slug, name=body.name, category=body.category, description=body.description)
    db.add(t)
    db.commit()
    audit(db, user, "create", "topic", slug, body.name)
    return {"slug": slug, "id": t.id}


@router.delete("/admin/topics/{slug}")
def delete_topic(slug: str, db: Session = Depends(get_db), user: User = Depends(require_permission("manage_repository"))):
    t = db.scalar(select(Topic).where(Topic.slug == slug))
    if not t:
        raise HTTPException(404, "Topic not found.")
    db.delete(t)
    db.commit()
    audit(db, user, "delete", "topic", slug, t.name)
    return {"ok": True}


@router.post("/admin/reindex")
def reindex(db: Session = Depends(get_db), user: User = Depends(require_permission("manage_repository"))):
    res = reindex_all(db)
    audit(db, user, "reindex", "repository", "", f"{res['chunks']} passages, {res['embedding_model']}, {res['vector_backend']}")
    return res


@router.post("/admin/reset-demo")
def reset_demo(db: Session = Depends(get_db), user: User = Depends(require_permission("manage_users"))):
    db.rollback()
    db.close()  # release row locks held by this request before dropping tables
    if not settings.DEMO_MODE:
        raise HTTPException(403, "Demo reset is disabled on this deployment.")
    from app.seed.seed_demo_data import run
    from app.rag import embeddings
    embeddings._local_cache.clear()
    counts = run()
    return {"ok": True, "counts": counts}


# ------------------------------------------------------------------ users & roles
@router.get("/admin/users")
def list_users(db: Session = Depends(get_db), user: User = Depends(require_permission("manage_users"))):
    content_counts = dict(db.execute(select(GeneratedContent.created_by, func.count()).group_by(GeneratedContent.created_by)).all())
    rows = db.scalars(select(User).order_by(User.created_at)).all()
    return {"results": [{**user_out(u), "is_active": u.is_active, "last_login": iso(u.last_login),
                         "created_at": iso(u.created_at), "content_items": content_counts.get(u.id, 0)} for u in rows],
            "roles": [{"name": r, "label": ROLE_INFO[r][0], "description": ROLE_INFO[r][1], "permissions": p}
                      for r, p in ROLE_PERMISSIONS.items()]}


@router.post("/admin/users")
def create_user(body: UserCreate, db: Session = Depends(get_db), user: User = Depends(require_permission("manage_users"))):
    if db.scalar(select(User).where(User.email == body.email.lower())):
        raise HTTPException(409, "A user with this email already exists.")
    role = db.scalar(select(Role).where(Role.name == body.role))
    u = User(email=body.email.lower(), name=body.name, password_hash=hash_password(body.password), role_id=role.id,
             institution=body.institution)
    db.add(u)
    db.commit()
    audit(db, user, "user_create", "user", u.email, f"Role {body.role}")
    return user_out(u)


@router.patch("/admin/users/{uid}")
def update_user(uid: int, body: UserUpdate, db: Session = Depends(get_db), user: User = Depends(require_permission("manage_users"))):
    u = db.get(User, uid)
    if not u:
        raise HTTPException(404, "User not found.")
    if u.id == user.id and (body.role not in (None, "admin") or body.is_active is False):
        raise HTTPException(409, "You cannot remove your own administrator access.")
    if body.role:
        old = u.role_name
        u.role_id = db.scalar(select(Role.id).where(Role.name == body.role))
        db.flush()
        db.refresh(u)
        audit(db, user, "role_change", "user", u.email, f"{old} → {body.role}", commit=False)
    if body.is_active is not None:
        u.is_active = body.is_active
        audit(db, user, "user_status", "user", u.email, "activated" if body.is_active else "deactivated", commit=False)
    if body.name:
        u.name = body.name
    db.commit()
    return {**user_out(u), "is_active": u.is_active}


# ------------------------------------------------------------------ audit logs
@router.get("/admin/audit-logs")
def audit_logs(action: str | None = None, status: str | None = None, q: str | None = None, page: int = Query(1, ge=1),
               page_size: int = Query(25, le=100), db: Session = Depends(get_db),
               user: User = Depends(require_permission("view_audit"))):
    stmt = select(AuditLog).order_by(AuditLog.created_at.desc())
    if action:
        stmt = stmt.where(AuditLog.action == action)
    if status:
        stmt = stmt.where(AuditLog.status == status)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(AuditLog.user_email.ilike(like) | AuditLog.detail.ilike(like) | AuditLog.resource_id.ilike(like))
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = db.scalars(stmt.offset((page - 1) * page_size).limit(page_size)).all()
    actions = [a for (a,) in db.execute(select(AuditLog.action).distinct().order_by(AuditLog.action))]
    return {"total": total, "page": page, "pages": max(1, -(-total // page_size)), "actions": actions,
            "results": [{"id": r.id, "user": r.user_email, "action": r.action, "resource_type": r.resource_type,
                         "resource_id": r.resource_id, "detail": r.detail, "status": r.status, "at": iso(r.created_at)}
                        for r in rows]}


# ------------------------------------------------------------------ analytics
@router.get("/analytics")
def analytics(days: int = Query(60, ge=7, le=365), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if not (can(user, "view_analytics") or can(user, "review")):
        raise HTTPException(403, "Analytics are available to editors and administrators.")
    since = datetime.now(timezone.utc) - timedelta(days=days)
    events = db.execute(select(AnalyticsEvent.event_type, AnalyticsEvent.resource_type, AnalyticsEvent.resource_id,
                               AnalyticsEvent.created_at).where(AnalyticsEvent.created_at >= since)).all()
    by_day: dict[str, Counter] = defaultdict(Counter)
    views: Counter = Counter()
    for et, rt, rid, ts in events:
        by_day[ts.date().isoformat()][et] += 1
        if et == "view" and rid:
            views[(rt, rid)] += 1
    timeline = []
    for i in range(days, -1, -1):
        d = (datetime.now(timezone.utc) - timedelta(days=i)).date().isoformat()
        c = by_day.get(d, Counter())
        timeline.append({"date": d, "views": c["view"], "searches": c["search"], "ai_questions": c["ai_question"],
                         "generated": c["generate"], "published": c["publish"]})
    titles = {("document", d.id): (d.title, f"/resources/{d.slug}") for d in db.scalars(select(Document))}
    titles.update({("dataset", d.id): (d.title, f"/datasets/{d.slug}") for d in db.scalars(select(Dataset))})
    titles.update({("media", d.id): (d.title, f"/media/{d.slug}") for d in db.scalars(select(Media))})
    popular = [{"title": titles[k][0], "url": titles[k][1], "type": k[0], "views": v}
               for k, v in views.most_common(40) if k in titles][:10]
    searches = Counter(q.lower() for (q,) in db.execute(select(SearchLog.query).where(SearchLog.created_at >= since)))
    modes = Counter(m for (m,) in db.execute(select(SearchLog.mode).where(SearchLog.created_at >= since)))
    ai = db.execute(select(AIQuery.mode, AIQuery.evidence_status, AIQuery.feedback).where(AIQuery.created_at >= since)).all()
    content = db.scalars(select(GeneratedContent)).all()
    turnaround = [(c.approved_at - c.submitted_at).total_seconds() / 3600 for c in content if c.approved_at and c.submitted_at]
    type_counts = {
        "Documents": db.scalar(select(func.count()).select_from(Document)),
        "Datasets": db.scalar(select(func.count()).select_from(Dataset)),
        "Media": db.scalar(select(func.count()).select_from(Media)),
        "Expeditions": db.scalar(select(func.count()).select_from(Expedition)),
        "Stations": db.scalar(select(func.count()).select_from(Station)),
        "Activities": db.scalar(select(func.count()).select_from(InstitutionalActivity)),
    }
    doc_types = Counter(t for (t,) in db.execute(select(Document.doc_type)))
    topic_counts = db.execute(select(Topic.name, func.count()).join(ResourceTopic, ResourceTopic.topic_id == Topic.id)
                              .group_by(Topic.name).order_by(func.count().desc()).limit(10)).all()
    growth = []
    docs_by_month = Counter()
    for (ts,) in db.execute(select(Document.created_at)):
        docs_by_month[ts.strftime("%Y-%m")] += 1
    for (ts,) in db.execute(select(Dataset.created_at)):
        docs_by_month[ts.strftime("%Y-%m")] += 1
    for (ts,) in db.execute(select(Media.created_at)):
        docs_by_month[ts.strftime("%Y-%m")] += 1
    running = 0
    for month in sorted(docs_by_month):
        running += docs_by_month[month]
        growth.append({"month": month, "total": running, "added": docs_by_month[month]})
    return {
        "label": "Prototype Demonstration Analytics — generated demo activity plus live usage of this deployment.",
        "days": days,
        "totals": {
            "resources": sum(type_counts.values()),
            "indexed_passages": db.scalar(select(func.count()).select_from(DocumentChunk)),
            "pending_reviews": sum(1 for c in content if c.status == "under_review"),
            "published": sum(1 for c in content if c.status == "published"),
            "active_users": db.scalar(select(func.count()).select_from(User).where(User.last_login >= since)),
            "searches": sum(searches.values()), "ai_questions": len(ai),
            "views": sum(1 for e in events if e[0] == "view"),
        },
        "timeline": timeline, "popular": popular,
        "top_searches": [{"query": q, "count": n} for q, n in searches.most_common(10)],
        "search_modes": dict(modes),
        "ai": {"by_mode": dict(Counter(a[0] for a in ai)), "by_evidence": dict(Counter(a[1] for a in ai)),
               "feedback": dict(Counter(a[2] or "none" for a in ai))},
        "content_workflow": dict(Counter(c.status for c in content)),
        "content_formats": dict(Counter(c.format for c in content)),
        "review_turnaround_hours": round(sum(turnaround) / len(turnaround), 1) if turnaround else None,
        "resource_types": type_counts, "document_types": dict(doc_types),
        "topics": [{"name": n, "count": c} for n, c in topic_counts],
        "growth": growth[-12:],
    }
