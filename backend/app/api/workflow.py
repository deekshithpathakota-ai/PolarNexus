"""Content Studio + Review Center + public outreach feed."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.security import can, get_current_user, require_permission
from app.content.generator import AUDIENCES, DEFAULT_AUDIENCE, FORMATS, create_draft, recheck
from app.core.database import get_db
from app.models import GeneratedContent, Review, User
from app.schemas.common import ContentUpdate, GenerateRequest, ReviewAction, TranslateRequest
from app.services.audit import audit, notify, track
from app.services.serializers import CHANNELS, content_out

router = APIRouter(prefix="/api", tags=["content"])

STATUSES = ["draft", "evidence_checked", "under_review", "changes_requested", "approved", "published", "rejected"]
WORKFLOW = [
    {"key": "draft", "label": "Draft"},
    {"key": "evidence_checked", "label": "Evidence checked"},
    {"key": "under_review", "label": "Submitted for review"},
    {"key": "changes_requested", "label": "Changes requested"},
    {"key": "approved", "label": "Approved · ready to publish"},
    {"key": "rejected", "label": "Rejected"},
    {"key": "published", "label": "Published"},
]


def _users(db: Session) -> dict[int, User]:
    return {u.id: u for u in db.scalars(select(User))}


def _get(db: Session, cid: int) -> GeneratedContent:
    c = db.get(GeneratedContent, cid)
    if not c:
        raise HTTPException(404, "Content item not found.")
    return c


def _now():
    return datetime.now(timezone.utc)


@router.get("/content/formats")
def formats():
    return {"formats": [{"key": k, "label": v[0], "group": v[1], "default_audience": DEFAULT_AUDIENCE.get(k)}
                        for k, v in FORMATS.items()],
            "audiences": [{"key": k, "label": v} for k, v in AUDIENCES.items()],
            "workflow": WORKFLOW,
            "source_types": ["document", "dataset", "topic", "expedition", "station", "researcher", "activity", "chunks"]}


@router.get("/outreach/channels")
def channels():
    return {"channels": [{"channel": k, **v} for k, v in CHANNELS.items()],
            "note": "Only the website feed is a live channel in this prototype. Other channels are connector-ready "
                    "and publishing to them is recorded as a prototype simulation."}


@router.post("/content/generate")
def generate(body: GenerateRequest, db: Session = Depends(get_db),
             user: User = Depends(require_permission("generate_content"))):
    try:
        c = create_draft(db, user, body.format, body.resource_type, body.resource_slug, body.chunk_ids,
                         audience=body.audience)
    except LookupError as exc:
        raise HTTPException(404, str(exc))
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    c.reviews.append(Review(reviewer_id=user.id, reviewer_name=user.name, action="created",
                            comment=f"Draft generated ({c.generation_mode})"))
    db.commit()
    audit(db, user, "ai_generate", "content", c.id, f"{c.format} draft from {c.resource_type} '{c.resource_title}' ({c.generation_mode})")
    track(db, "generate", c.resource_type, c.resource_id, user, {"format": c.format})
    return content_out(c, _users(db))


@router.get("/content")
def list_content(status: str | None = Query(None), mine: bool = False, page: int = Query(1, ge=1),
                 page_size: int = Query(20, le=100), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    stmt = select(GeneratedContent).order_by(GeneratedContent.updated_at.desc())
    if status:
        stmt = stmt.where(GeneratedContent.status.in_(status.split(",")))
    if mine or not can(user, "review"):
        stmt = stmt.where(GeneratedContent.created_by == user.id)
    rows = db.scalars(stmt).all()
    users = _users(db)
    counts = {s: 0 for s in STATUSES}
    for r in db.scalars(select(GeneratedContent) if can(user, "review") else
                        select(GeneratedContent).where(GeneratedContent.created_by == user.id)):
        counts[r.status] = counts.get(r.status, 0) + 1
    total = len(rows)
    return {"total": total, "page": page, "pages": max(1, -(-total // page_size)), "counts": counts,
            "results": [content_out(c, users, full=False) for c in rows[(page - 1) * page_size: page * page_size]]}


@router.get("/content/{cid}")
def get_content(cid: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    c = _get(db, cid)
    if c.created_by != user.id and not can(user, "review"):
        raise HTTPException(403, "You can only view your own drafts.")
    return content_out(c, _users(db))


@router.put("/content/{cid}")
def update_content(cid: int, body: ContentUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    c = _get(db, cid)
    is_owner = c.created_by == user.id
    if not (is_owner and can(user, "generate_content")) and not can(user, "edit_content"):
        raise HTTPException(403, "You do not have permission to edit this content.")
    if c.status in {"published", "rejected"}:
        raise HTTPException(409, f"{c.status.title()} content cannot be edited. Create a new draft instead.")
    if body.title:
        c.title = body.title
    if body.body:
        c.body = body.body
    c.version += 1
    if c.generation_mode != "manual":
        c.generation_mode = f"{c.generation_mode}+edited" if "+edited" not in c.generation_mode else c.generation_mode
    recheck(c)
    if c.status == "approved":
        c.status = "under_review"  # any edit after approval needs a fresh approval
    elif c.status == "evidence_checked":
        c.status = "draft"  # edited text must be evidence-checked again
    c.reviews.append(Review(reviewer_id=user.id, reviewer_name=user.name, action="edited", comment=f"Version {c.version}"))
    db.commit()
    audit(db, user, "content_edit", "content", c.id, f"Edited to version {c.version}")
    return content_out(c, _users(db))


@router.post("/content/{cid}/check")
def run_check(cid: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    c = _get(db, cid)
    if c.created_by != user.id and not can(user, "review"):
        raise HTTPException(403, "You can only check your own drafts.")
    check = recheck(c)
    if c.status == "draft" and check.get("overall") in {"pass", "warn"}:
        c.status = "evidence_checked"
        c.reviews.append(Review(reviewer_id=user.id, reviewer_name=user.name, action="evidence_checked",
                                comment=f"Automated evidence check: {check.get('overall')}"))
    db.commit()
    audit(db, user, "content_check", "content", c.id, f"Evidence check: {check.get('overall')}")
    return {**check, "status": c.status}


@router.post("/content/{cid}/submit")
def submit(cid: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    c = _get(db, cid)
    if c.created_by != user.id and not can(user, "edit_content"):
        raise HTTPException(403, "Only the author or an editor can submit this draft.")
    if c.status not in {"draft", "evidence_checked", "changes_requested"}:
        raise HTTPException(409, f"Content in status '{c.status}' cannot be submitted.")
    if not c.citations:
        raise HTTPException(422, "Attach at least one source before submitting for review.")
    if c.status != "evidence_checked":  # the evidence check always runs before review
        check = recheck(c)
        c.reviews.append(Review(reviewer_id=user.id, reviewer_name=user.name, action="evidence_checked",
                                comment=f"Automated evidence check before submission: {check.get('overall')}"))
    c.status, c.submitted_at = "under_review", _now()
    c.reviews.append(Review(reviewer_id=user.id, reviewer_name=user.name, action="submitted", comment="Submitted for editorial review"))
    db.commit()
    notify(db, "Content awaiting review", f"“{c.title}” was submitted by {user.name}.", f"/review?item={c.id}", "review", role="editor")
    audit(db, user, "content_submit", "content", c.id, c.title)
    return content_out(c, _users(db))


@router.delete("/content/{cid}")
def delete_content(cid: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    c = _get(db, cid)
    if c.status == "published":
        raise HTTPException(409, "Published content cannot be deleted.")
    if c.created_by != user.id and user.role_name != "admin":
        raise HTTPException(403, "Only the author or an administrator can delete this draft.")
    db.delete(c)
    db.commit()
    audit(db, user, "content_delete", "content", cid, "Draft deleted")
    return {"ok": True}


# ------------------------------------------------------------------ reviews
@router.get("/reviews/queue")
def review_queue(db: Session = Depends(get_db), user: User = Depends(require_permission("review"))):
    users = _users(db)
    rows = db.scalars(select(GeneratedContent).order_by(GeneratedContent.submitted_at.desc().nullslast(),
                                                        GeneratedContent.updated_at.desc())).all()
    # evidence-checked drafts are still with their author; reviewers see them in the draft group
    groups = {s: [content_out(c, users, full=False) for c in rows if c.status == s] for s in STATUSES}
    return {"groups": groups, "counts": {s: len(v) for s, v in groups.items()}}


def _transition(db: Session, user: User, c: GeneratedContent, action: str, body: ReviewAction) -> dict:
    allowed = {
        "approve": ({"under_review"}, "approved"),
        "reject": ({"under_review", "approved", "changes_requested"}, "rejected"),
        "request_changes": ({"under_review", "approved"}, "changes_requested"),
        "publish": ({"approved"}, "published"),
    }
    if action == "comment":
        c.reviews.append(Review(reviewer_id=user.id, reviewer_name=user.name, action="comment", comment=body.comment))
        db.commit()
        return content_out(c, _users(db))
    sources, target = allowed[action]
    if c.status not in sources:
        raise HTTPException(409, f"Cannot {action.replace('_', ' ')} content that is '{c.status.replace('_', ' ')}'.")
    if action in {"reject", "request_changes"} and len(body.comment.strip()) < 5:
        raise HTTPException(422, "Please add a short comment explaining the decision.")
    if action == "approve":
        if c.created_by == user.id and user.role_name != "admin":
            raise HTTPException(403, "Reviewers cannot approve their own content.")
        check = recheck(c)
        if check.get("overall") == "fail" and not body.acknowledge_warnings:
            raise HTTPException(422, "The evidence check reported failures. Review the flagged items and confirm to approve anyway.")
        c.approved_at, c.reviewer_id = _now(), user.id
    if action == "publish":
        c.published_at = _now()
        c.channels = list(dict.fromkeys(body.channels or ["website"]))
        if "website" not in c.channels:
            c.channels.insert(0, "website")  # the live feed is the system of record for published content
    c.status = target
    simulated = [ch for ch in c.channels if CHANNELS.get(ch, {}).get("status") != "live"] if action == "publish" else []
    comment = body.comment or {"approve": "Approved after review — ready to publish",
                               "publish": "Published to " + ", ".join(c.channels)
                               + (f" (prototype simulation: {', '.join(simulated)})" if simulated else "")}.get(action, "")
    c.reviews.append(Review(reviewer_id=user.id, reviewer_name=user.name, action=target, comment=comment))
    db.commit()
    audit(db, user, f"content_{action}", "content", c.id, f"{c.title} → {target}")
    if c.created_by:
        kinds = {"approved": "success", "published": "success", "rejected": "error", "changes_requested": "warning"}
        notify(db, f"Content {target.replace('_', ' ')}", f"“{c.title}” — {comment}", "/studio" if target != "published" else "/outreach",
               kinds.get(target, "info"), user_id=c.created_by)
    if action == "publish":
        track(db, "publish", c.resource_type, c.resource_id, user, {"channels": c.channels, "simulated": simulated})
        from app.rag.indexer import index_resource
        index_resource(db, "content", c.id)  # published outreach becomes discoverable in unified search
    return content_out(c, _users(db))


@router.post("/reviews")
def review_generic(body: ReviewAction, db: Session = Depends(get_db), user: User = Depends(require_permission("review"))):
    if not body.content_id or not body.action:
        raise HTTPException(422, "content_id and action are required.")
    return _transition(db, user, _get(db, body.content_id), body.action, body)


@router.post("/reviews/{cid}/approve")
def approve(cid: int, body: ReviewAction | None = None, db: Session = Depends(get_db), user: User = Depends(require_permission("approve"))):
    return _transition(db, user, _get(db, cid), "approve", body or ReviewAction())


@router.post("/reviews/{cid}/reject")
def reject(cid: int, body: ReviewAction, db: Session = Depends(get_db), user: User = Depends(require_permission("approve"))):
    return _transition(db, user, _get(db, cid), "reject", body)


@router.post("/reviews/{cid}/request-changes")
def request_changes(cid: int, body: ReviewAction, db: Session = Depends(get_db), user: User = Depends(require_permission("review"))):
    return _transition(db, user, _get(db, cid), "request_changes", body)


@router.post("/reviews/{cid}/publish")
def publish(cid: int, body: ReviewAction | None = None, db: Session = Depends(get_db), user: User = Depends(require_permission("publish"))):
    return _transition(db, user, _get(db, cid), "publish", body or ReviewAction())


# ------------------------------------------------------------------ public outreach feed (dissemination)
@router.get("/outreach")
def outreach_feed(format: str | None = None, page: int = Query(1, ge=1), page_size: int = Query(12, le=50),
                  db: Session = Depends(get_db)):
    stmt = select(GeneratedContent).where(GeneratedContent.status == "published").order_by(GeneratedContent.published_at.desc())
    if format:
        stmt = stmt.where(GeneratedContent.format == format)
    rows = db.scalars(stmt).all()
    users = _users(db)
    items = []
    for c in rows[(page - 1) * page_size: page * page_size]:
        o = content_out(c, users)
        o.pop("evidence_check", None)
        items.append(o)
    return {"total": len(rows), "page": page, "pages": max(1, -(-len(rows) // page_size)), "results": items}


@router.get("/outreach/{cid}")
def outreach_item(cid: int, db: Session = Depends(get_db)):
    c = db.get(GeneratedContent, cid)
    if not c or c.status != "published":
        raise HTTPException(404, "Published content not found.")
    o = content_out(c, _users(db))
    o.pop("evidence_check", None)
    o["evidence_summary"] = {"overall": (c.evidence_check or {}).get("overall"),
                             "checks": [{"label": x["label"], "status": x["status"]} for x in (c.evidence_check or {}).get("checks", [])]}
    return o


TRANSLATE_SYSTEM = ("Translate the user's outreach text into {lang}. Translate ONLY — do not add, remove or soften any "
                    "claim, number or name. Keep every citation marker like [1] exactly where it is, keep Markdown "
                    "formatting, and keep scientific names. Return only the translation.")


def translation_problems(src: str, out: str) -> list[str]:
    """A machine translation is kept only if every citation marker, number and unit survives unchanged."""
    import re as _re

    problems = []
    if sorted(_re.findall(r"\[\d+\]", out)) != sorted(_re.findall(r"\[\d+\]", src)):
        problems.append("citation markers changed")
    strip = lambda t: _re.sub(r"\[\d+\]", " ", t)  # noqa: E731
    nums = lambda t: sorted(n.replace(",", "") for n in _re.findall(r"\d+(?:[.,]\d+)*", strip(t)))  # noqa: E731
    if nums(out) != nums(src):
        problems.append("numbers changed")
    units = lambda t: sorted(_re.findall(r"°C|°|km²|km2|%|ppm|hPa|PSU|m/s", t))  # noqa: E731
    if units(out) != units(src):
        problems.append("units changed")
    return problems


@router.post("/content/{cid}/translate")
def translate(cid: int, body: TranslateRequest, db: Session = Depends(get_db),
              user: User = Depends(require_permission("generate_content"))):
    """Creates a translation DRAFT (never published directly). With an LLM configured the text is machine-translated
    with citation markers preserved; otherwise a clearly-marked draft is created for a human translator."""
    from app.models import Citation
    from app.rag.llm import LLMUnavailable, get_llm

    src = _get(db, cid)
    if src.created_by != user.id and not can(user, "edit_content"):
        raise HTTPException(403, "You can only translate your own content.")
    llm = get_llm()
    mode, new_body, title = "manual", src.body, f"[{body.language}] {src.title}"
    note = "awaiting human translation"
    if llm:
        try:
            out = llm.complete(TRANSLATE_SYSTEM.format(lang=body.language), src.body, max_tokens=1200, temperature=0.1)
            problems = translation_problems(src.body, out)
            if not problems:
                mode, new_body, note = "llm-translation", out, "machine translation — citations, numbers and units verified"
            else:
                note = "machine translation discarded: " + "; ".join(problems)
        except LLMUnavailable:
            note = "language model unavailable — awaiting human translation"
    if mode == "manual":
        new_body = (f"> Translation pending ({body.language}). Replace the English text below with a faithful "
                    f"translation, keeping every [n] marker.\n\n{src.body}")
    c = GeneratedContent(title=title[:300], format=src.format, body=new_body, status="draft", generation_mode=mode,
                         resource_type=src.resource_type, resource_id=src.resource_id, resource_title=src.resource_title,
                         created_by=user.id, channels=[], is_demo=False, audience=src.audience, language=body.language,
                         translated_from=src.id, evidence_check={})
    for x in src.citations:
        c.citations.append(Citation(chunk_id=x.chunk_id, position=x.position, resource_type=x.resource_type,
                                    resource_id=x.resource_id, resource_slug=x.resource_slug, label=x.label,
                                    section=x.section, page=x.page, quote=x.quote))
    c.evidence_check = {"overall": "warn", "checks": [{"id": "translation", "label": "Translation review", "status": "warn",
                        "detail": f"Prototype translation workflow ({note}). The lexical evidence check compares English "
                                  "text with English sources, so a bilingual editor must confirm this translation."}],
                        "sentences": [], "method_note": "Translations require human verification by a bilingual editor."}
    c.reviews.append(Review(reviewer_id=user.id, reviewer_name=user.name, action="created",
                            comment=f"Translation draft ({body.language}) of #{src.id} — {note}"))
    db.add(c)
    db.commit()
    audit(db, user, "content_translate", "content", c.id, f"{body.language} draft from #{src.id} ({mode})")
    return content_out(c, _users(db))
