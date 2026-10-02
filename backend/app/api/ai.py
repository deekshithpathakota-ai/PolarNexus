from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.security import get_current_user_optional
from app.core.database import get_db
from app.core.ratelimit import rate_limit
from app.models import AIQuery, Document, User
from app.rag.answer import AUDIENCES, ask
from app.rag.embeddings import get_provider, provider_description
from app.rag.indexer import vector_backend_name
from app.rag.llm import ai_status
from app.rag.summary import summarize
from app.schemas.common import AskRequest, FeedbackRequest, SummaryRequest
from app.services.audit import track
from app.services.catalog import build_catalog

router = APIRouter(prefix="/api/ai", tags=["ai"])

EXAMPLES = [
    "What factors influence Antarctic sea-ice variability?",
    "What are the major research themes in Antarctica?",
    "Which expeditions studied atmospheric science?",
    "Show resources related to Southern Ocean research",
    "How does the Southern Ocean absorb carbon dioxide?",
    "Explain the Antarctic ozone hole for a student",
]
DOC_EXAMPLES = ["Explain the key factors discussed in this resource.", "Summarize the methodology.",
                "What are the key findings?", "Explain Figure 3.", "What limitations are mentioned?",
                "Explain this research paper for a student."]


@router.post("/ask", dependencies=[Depends(rate_limit("ai"))])
def ask_endpoint(body: AskRequest, db: Session = Depends(get_db), user: User | None = Depends(get_current_user_optional)):
    result = ask(db, user, body.question, body.document_slug, body.mode, body.audience)
    track(db, "ai_question", "document" if body.document_slug else "", None, user,
          {"mode": result["mode"], "evidence": result["evidence_status"]})
    return result


@router.post("/document-question")
def document_question(body: AskRequest, db: Session = Depends(get_db), user: User | None = Depends(get_current_user_optional)):
    if not body.document_slug:
        raise HTTPException(422, "document_slug is required for a document-specific question.")
    return ask_endpoint(body, db, user)


@router.post("/summary")
def summary(body: SummaryRequest, db: Session = Depends(get_db), user: User | None = Depends(get_current_user_optional)):
    doc = db.scalar(select(Document).where(Document.slug == body.document_slug))
    if not doc or not build_catalog(db, user).card("document", doc.id):
        raise HTTPException(404, "Document not found.")
    out = summarize(db, doc, body.kind)
    track(db, "summary", "document", doc.id, user, {"kind": body.kind})
    return out


@router.post("/feedback")
def feedback(body: FeedbackRequest, db: Session = Depends(get_db)):
    q = db.get(AIQuery, body.query_id)
    if not q:
        raise HTTPException(404, "Answer not found.")
    q.feedback = body.feedback
    db.commit()
    return {"ok": True}


@router.get("/status")
def status(db: Session = Depends(get_db)):
    provider = get_provider(db)
    from app.ingestion.ocr import status as ocr_status
    from app.services.visual import status as visual_status

    return {**ai_status(), "embedding_description": provider_description(provider.name) if provider else "Index not built",
            "vector_backend": vector_backend_name(), "examples": EXAMPLES, "document_examples": DOC_EXAMPLES,
            "visual_search": visual_status(db), "ocr": ocr_status(),
            "audiences": [{"key": k, "label": k.title(), "description": v} for k, v in AUDIENCES.items()]}
