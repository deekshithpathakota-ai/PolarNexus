"""Scientific-trust endpoints: version history, FAIR metadata, provenance pipeline (lineage), visual search,
duplicate checks and the admin platform-health dashboard."""
from __future__ import annotations

from collections import Counter

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.security import can, get_current_user_optional, require_permission
from app.core.database import get_db
from app.core.ratelimit import rate_limit
from app.models import (
    AIQuery,
    Dataset,
    DatasetUpload,
    Document,
    GeneratedContent,
    IngestionJob,
    Media,
    Provenance,
    RESOURCE_MODELS,
    User,
)
from app.services import fair, lineage, provenance as prov, versions, visual
from app.services.audit import audit
from app.services.catalog import build_catalog
from app.services.serializers import media_out
from app.services.storage import get_storage

router = APIRouter(prefix="/api", tags=["scientific-trust"])

TYPES = "^(document|dataset|media|expedition|station|researcher|activity)$"


def _resolve(db: Session, user: User | None, rtype: str, slug: str):
    model = RESOURCE_MODELS.get(rtype)
    obj = db.scalar(select(model).where(model.slug == slug)) if model else None
    cat = build_catalog(db, user)
    if not obj or not cat.card(rtype, obj.id):
        raise HTTPException(404, "Resource not found.")
    return obj, cat


@router.get("/versions/{rtype}/{slug}")
def version_history(rtype: str, slug: str, db: Session = Depends(get_db), user: User | None = Depends(get_current_user_optional)):
    if rtype not in RESOURCE_MODELS:
        raise HTTPException(404, "Unknown resource type.")
    obj, _ = _resolve(db, user, rtype, slug)
    rows = versions.history(db, rtype, obj.id)
    if not can(user, "manage_repository"):
        for r in rows:
            r["snapshot"] = {k: v for k, v in (r["snapshot"] or {}).items() if k != "content_archive"}
    return {"resource_type": rtype, "slug": slug, "current_version": rows[0]["version"] if rows else None, "versions": rows,
            "policy": "Append-only: earlier versions are never overwritten."}


@router.get("/fair/{rtype}/{slug}")
def fair_metadata(rtype: str, slug: str, db: Session = Depends(get_db), user: User | None = Depends(get_current_user_optional)):
    if rtype not in RESOURCE_MODELS or rtype == "topic":
        raise HTTPException(404, "Unknown resource type.")
    obj, cat = _resolve(db, user, rtype, slug)
    hist = versions.history(db, rtype, obj.id)
    return fair.build(db, cat, rtype, obj, version=hist[0]["version"] if hist else None)


@router.get("/lineage/{rtype}/{slug}")
def resource_lineage(rtype: str, slug: str, db: Session = Depends(get_db), user: User | None = Depends(get_current_user_optional)):
    if rtype == "content":
        c = db.get(GeneratedContent, int(slug)) if slug.isdigit() else None
        if not c:
            raise HTTPException(404, "Content not found.")
        allowed = c.status == "published" or (user and (c.created_by == user.id or can(user, "review")))
        if not allowed:
            raise HTTPException(404, "Content not found.")
        return lineage.content_lineage(db, c)
    if rtype not in RESOURCE_MODELS:
        raise HTTPException(404, "Unknown resource type.")
    obj, _ = _resolve(db, user, rtype, slug)
    return lineage.resource_lineage(db, rtype, obj)


@router.get("/visual/status")
def visual_status(db: Session = Depends(get_db)):
    return visual.status(db)


@router.get("/visual/search", dependencies=[Depends(rate_limit("ai"))])
def visual_search(q: str = Query(..., min_length=2, max_length=200), limit: int = Query(12, ge=1, le=40),
                  db: Session = Depends(get_db), user: User | None = Depends(get_current_user_optional)):
    """Pure text→image retrieval (CLIP). Returns matching photographs and video frames with timestamps."""
    st = visual.status(db)
    if not visual.available():
        return {"query": q, "available": False, "status": visual.status(db), "results": [],
                "notice": st.get("reason") or "Visual search is not available on this server — use the regular search, "
                          "which covers titles, descriptions, captions and transcripts."}
    hits = visual.search(db, q, k=limit * 2)
    cat = build_catalog(db, user)
    out = []
    for h in hits:
        card = cat.card("media", h["media_id"])
        m = db.get(Media, h["media_id"])
        if not card or not m:
            continue
        out.append({**media_out(m), "verification": card["verification"], "verification_label": card["verification_label"],
                    "similarity": h["similarity"], "timestamp": h["timestamp"], "frame_seconds": h["frame_seconds"],
                    "frame_url": f"/api/media/{m.slug}/frames/{h['frame_index']}" if h["frame_index"] is not None else None})
        if len(out) >= limit:
            break
    return {"query": q, "available": True, "model": st.get("model"), "results": out,
            "notice": "Ranked by CLIP text–image similarity (a relevance score, not a probability). "
                      "Only photographs and video frames with real image files are visually indexed."}


@router.post("/admin/visual/reindex")
def visual_reindex(db: Session = Depends(get_db), user: User = Depends(require_permission("manage_repository"))):
    if not visual.available():
        raise HTTPException(409, visual.status().get("reason") or "Visual search is not available on this server.")
    out = visual.reindex_all(db)
    audit(db, user, "reindex", "visual", "all", f"{out['vectors']} vectors for {out['media']} media")
    return out


@router.get("/duplicates/{rtype}/{slug}")
def duplicates_of(rtype: str, slug: str, db: Session = Depends(get_db), user: User = Depends(require_permission("manage_repository"))):
    from app.services import duplicates as dup

    obj, _ = _resolve(db, user, rtype, slug)
    if rtype == "document":
        return {"duplicates": dup.check_document(db, content_hash=obj.content_hash, title=obj.title, filename=obj.file_name,
                                                 text=obj.content or "", doi=obj.doi, exclude_id=obj.id)}
    if rtype == "dataset":
        return {"duplicates": dup.check_dataset(db, content_hash=obj.content_hash, title=obj.title, doi=obj.doi,
                                                columns=[c.get("name", "") for c in (obj.columns_schema or [])], exclude_id=obj.id)}
    if rtype == "media":
        return {"duplicates": dup.check_media(db, content_hash=obj.content_hash, title=obj.title, filename=obj.filename, exclude_id=obj.id)}
    raise HTTPException(422, "Duplicate checks are available for documents, datasets and media.")


@router.get("/admin/platform-health")
def platform_health(db: Session = Depends(get_db), user: User = Depends(require_permission("view_analytics"))):
    from app.ingestion.ocr import status as ocr_status
    from app.rag.llm import ai_status
    from app.services import duplicates as dup

    cat = build_catalog(db, user)
    prov.ensure_all(db)
    pv = Counter(r.verification_status for r in db.scalars(select(Provenance)))
    total = sum(1 for c in cat.cards.values() if c["type"] not in {"topic", "content"})
    failed_docs = db.scalar(select(func.count()).select_from(IngestionJob).where(IngestionJob.status == "failed")) or 0
    failed_media = db.scalar(select(func.count()).select_from(Media).where(Media.processing_status == "failed")) or 0
    failed_ds = db.scalar(select(func.count()).select_from(DatasetUpload).where(DatasetUpload.status == "failed")) or 0
    queue = (db.scalar(select(func.count()).select_from(IngestionJob).where(IngestionJob.status.in_(["queued", "processing"]))) or 0) \
        + (db.scalar(select(func.count()).select_from(Media).where(Media.processing_status.notin_(["ready", "failed"]))) or 0) \
        + (db.scalar(select(func.count()).select_from(DatasetUpload).where(DatasetUpload.status == "registering")) or 0)
    q = db.scalars(select(AIQuery)).all()
    insufficient = sum(1 for x in q if x.evidence_status == "insufficient")
    content = Counter(c.status for c in db.scalars(select(GeneratedContent)))
    ocr_failed = db.scalar(select(func.count()).select_from(Document).where(Document.ocr_status.in_(["failed", "unavailable"]))) or 0
    ocr_partial = db.scalar(select(func.count()).select_from(Document).where(Document.ocr_status == "partial")) or 0
    invalid_ds = sum(1 for d in db.scalars(select(Dataset)) if ((d.quality_report or {}).get("summary") or {}).get("errors"))
    invalid_uploads = sum(1 for u in db.scalars(select(DatasetUpload).where(DatasetUpload.status == "analyzed"))
                          if ((u.analysis or {}).get("summary") or {}).get("errors"))
    missing = fair.missing_metadata_count(db, cat)
    return {
        "repository": {"total_resources": total, "verified": pv.get("verified", 0), "public_source": pv.get("public_source", 0),
                       "partner": pv.get("partner_source", 0), "pending": pv.get("pending_review", 0) + pv.get("unverified", 0)
                       + pv.get("user_uploaded", 0), "demo": pv.get("demo_data", 0), "synthetic": pv.get("synthetic_demo", 0),
                       "failed_ingestion": failed_docs + failed_media + failed_ds,
                       "failed_breakdown": {"documents": failed_docs, "media": failed_media, "datasets": failed_ds},
                       "processing_queue": queue, "storage": get_storage().describe()},
        "ai": {"requests": len(q), "retrieval_success": len(q) - insufficient, "insufficient_evidence": insufficient,
               "retrieval_success_rate": round((len(q) - insufficient) / len(q), 3) if q else None,
               "citation_validation_failures": sum(1 for x in q if (x.citations_removed or 0) > 0),
               "citation_markers_removed": sum(x.citations_removed or 0 for x in q),
               "by_strength": dict(Counter(x.evidence_strength or "not recorded" for x in q)),
               "provider": ai_status(), "visual": visual.status(db), "ocr": ocr_status(),
               "note": "Citation-validation failures are counted from v3 onwards (earlier answers were not instrumented)."},
        "content": {"draft": content.get("draft", 0) + content.get("evidence_checked", 0),
                    "pending_review": content.get("under_review", 0) + content.get("changes_requested", 0),
                    "approved": content.get("approved", 0), "published": content.get("published", 0),
                    "rejected": content.get("rejected", 0)},
        "data_quality": {"duplicate_candidates": dup.count_candidates(db),
                         "missing_metadata": missing["resources_missing_required"], "missing_by_field": missing["by_field"],
                         "ocr_failures": ocr_failed, "ocr_partial": ocr_partial,
                         "invalid_datasets": invalid_ds + invalid_uploads},
    }
