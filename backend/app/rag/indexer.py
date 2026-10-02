"""Chunking + embedding + storage of retrievable passages for every resource type."""
from __future__ import annotations

import logging
import re

from sqlalchemy import delete, select, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import VectorState
from app.models import (
    Dataset,
    Document,
    DocumentChunk,
    Expedition,
    GeneratedContent,
    InstitutionalActivity,
    Media,
    Researcher,
    Station,
    Topic,
)
from app.rag import embeddings as emb
from app.rag.vector_store import invalidate_caches
from app.utils.text import split_sentences

log = logging.getLogger("polarnexus.indexer")

CHUNK_CHARS = 1200


def _pack_sentences(paragraph_text: str, limit: int = CHUNK_CHARS) -> list[str]:
    chunks, cur = [], ""
    for sent in split_sentences(paragraph_text):
        if cur and len(cur) + len(sent) + 1 > limit:
            chunks.append(cur.strip())
            # one-sentence overlap preserves context across boundaries
            last = split_sentences(cur)[-1] if split_sentences(cur) else ""
            cur = (last + " " + sent) if len(last) < 220 else sent
        else:
            cur = f"{cur} {sent}" if cur else sent
    if cur.strip():
        chunks.append(cur.strip())
    return chunks


def split_document(content: str) -> list[tuple[str, int, str]]:
    """Returns [(section, page, passage)]. Understands '## Heading' sections and '[[page N]]' markers."""
    out: list[tuple[str, int, str]] = []
    section, page = "Text", 1
    buf: list[str] = []

    def flush():
        body = " ".join(buf).strip()
        if body:
            for passage in _pack_sentences(body):
                out.append((section, page, passage))
        buf.clear()

    for raw in content.splitlines():
        line = raw.strip()
        m_page = re.match(r"^\[\[page (\d+)\]\]$", line)
        if m_page:
            flush()
            page = int(m_page.group(1))
            continue
        if line.startswith("## "):
            flush()
            section = line[3:].strip()[:120]
            continue
        if line.startswith("# "):
            continue
        if not line:
            flush()
            continue
        buf.append(line)
    flush()
    return out


def _rows(db: Session, model, only: tuple[str, int] | None, rtype: str, *where):
    if only and only[0] != rtype:
        return []
    stmt = select(model)
    for w in where:
        stmt = stmt.where(w)
    if only:
        stmt = stmt.where(model.id == only[1])
    return db.scalars(stmt)


def media_passages(m: Media) -> list[DocumentChunk]:
    exif_bits = []
    if m.captured_at:
        exif_bits.append(f"Captured {m.captured_at.date().isoformat()}")
    if m.location:
        exif_bits.append(f"Location: {m.location}")
    if m.duration_seconds:
        exif_bits.append(f"Duration {int(m.duration_seconds // 60)} min {int(m.duration_seconds % 60)} s")
    head = (f"{m.title}. {m.description} Tags: {', '.join(m.tags or [])}. Category: {m.category}. Region: {m.region}."
            + (" " + ". ".join(exif_bits) + "." if exif_bits else ""))
    out = [DocumentChunk(resource_type="media", resource_id=m.id, section="Media description", text=head)]
    if m.transcript:
        for i, passage in enumerate(_pack_sentences(re.sub(r"\s+", " ", m.transcript))):
            out.append(DocumentChunk(resource_type="media", resource_id=m.id, chunk_index=i + 1,
                                     section="Video transcript", text=passage))
    return out


def resource_passages(db: Session, only: tuple[str, int] | None = None) -> list[DocumentChunk]:
    """Builds unembedded chunks for every resource in the repository (or just `only=(type, id)`)."""
    chunks: list[DocumentChunk] = []
    for doc in _rows(db, Document, only, "document", Document.status != "archived"):
        chunks.extend(document_chunks(doc))
    for ds in _rows(db, Dataset, only, "dataset"):
        vars_ = ", ".join(f"{v['name']} ({v.get('unit', '')})" for v in ds.variables)
        chunks.append(DocumentChunk(resource_type="dataset", resource_id=ds.id, section="Dataset description", text=(
            f"{ds.title}. {ds.description} Variables: {vars_}. Region: {ds.region}. Coverage: {ds.spatial_coverage}.")))
    for m in _rows(db, Media, only, "media"):
        if (m.status or "indexed") == "archived" or (m.processing_status or "ready") not in {"ready", "indexing"}:
            continue
        chunks.extend(media_passages(m))
    for e in _rows(db, Expedition, only, "expedition"):
        chunks.append(DocumentChunk(resource_type="expedition", resource_id=e.id, section="Expedition overview", text=(
            f"{e.name} ({e.season}). {e.objective} Research themes: {', '.join(e.themes)}. "
            f"Highlights: {' '.join(e.highlights)}")))
    for s in _rows(db, Station, only, "station"):
        chunks.append(DocumentChunk(resource_type="station", resource_id=s.id, section="Station overview", text=(
            f"{s.name} — {s.kind}, {s.location_name}. {s.description} Research themes: {', '.join(s.themes)}.")))
    for r in _rows(db, Researcher, only, "researcher"):
        chunks.append(DocumentChunk(resource_type="researcher", resource_id=r.id, section="Researcher profile", text=(
            f"{r.name}, {r.title}, {r.institution}. Expertise: {', '.join(r.expertise)}. {r.bio}")))
    for a in _rows(db, InstitutionalActivity, only, "activity", InstitutionalActivity.status != "archived"):
        when = a.date.isoformat() if a.date else ""
        chunks.append(DocumentChunk(resource_type="activity", resource_id=a.id, section="Institutional activity", text=(
            f"{a.title}. {a.description} Activity type: {a.activity_type.replace('_', ' ')}. Organised by {a.organisation}"
            f"{', ' + a.department if a.department else ''}. Location: {a.location}. Date: {when}. "
            f"Audience: {a.audience}. Outcomes: {' '.join(a.outcomes or [])}")))
    for t in _rows(db, Topic, only, "topic"):
        chunks.append(DocumentChunk(resource_type="topic", resource_id=t.id, section="Topic", text=(
            f"{t.name} — research topic ({t.category}). {t.description}")))
    for c in _rows(db, GeneratedContent, only, "content", GeneratedContent.status == "published"):
        body = re.sub(r"\[\d+\]|[#*_]", "", c.body)
        for i, passage in enumerate(_pack_sentences(re.sub(r"\s+", " ", f"{c.title}. {body}"))[:6]):
            chunks.append(DocumentChunk(resource_type="content", resource_id=c.id, chunk_index=i,
                                        section="Published outreach", text=passage))
    return chunks


def document_chunks(doc: Document) -> list[DocumentChunk]:
    parts = split_document(doc.content or doc.abstract)
    if not parts and doc.abstract:
        parts = [("Abstract", 1, doc.abstract)]
    return [
        DocumentChunk(resource_type="document", resource_id=doc.id, document_id=doc.id, chunk_index=i,
                      section=section, page=page, text=passage)
        for i, (section, page, passage) in enumerate(parts)
    ]


def _embed_text(c: DocumentChunk, title_lookup: dict[tuple[str, int], str]) -> str:
    title = title_lookup.get((c.resource_type, c.resource_id), "")
    return f"{title}. {c.section}. {c.text}" if title else c.text


def _titles(db: Session) -> dict[tuple[str, int], str]:
    return {("document", d.id): d.title for d in db.scalars(select(Document))}


def reindex_all(db: Session) -> dict:
    """Rebuilds every chunk + embedding. Used by seeding and the admin 'Rebuild index' action."""
    db.execute(delete(DocumentChunk))
    db.commit()
    chunks = resource_passages(db)
    titles = _titles(db)
    texts = [_embed_text(c, titles) for c in chunks]

    provider: emb.EmbeddingProvider
    if settings.llm_enabled:
        provider = emb.OpenAIEmbeddingProvider()
        try:
            vectors = provider.embed(texts)
        except emb.EmbeddingUnavailable as exc:
            log.warning("%s — falling back to local embeddings", exc)
            provider, vectors = _fit_local(db, texts)
    else:
        provider, vectors = _fit_local(db, texts)

    for c, v in zip(chunks, vectors):
        c.embedding = v
        c.embedding_model = provider.name
    db.add_all(chunks)
    db.commit()
    invalidate_caches()
    return {"chunks": len(chunks), "embedding_model": provider.name, "vector_backend": vector_backend_name()}


def _fit_local(db: Session, texts: list[str]):
    provider = emb.LocalLSAEmbeddingProvider.fit(texts)
    provider.save(db)
    emb.set_local_provider(provider)
    return provider, provider.embed(texts)


def index_document(db: Session, doc: Document) -> int:
    """Indexes one (newly ingested) document with the currently active provider."""
    db.execute(delete(DocumentChunk).where(DocumentChunk.document_id == doc.id))
    chunks = document_chunks(doc)
    if not chunks:
        db.commit()
        return 0
    texts = [f"{doc.title}. {c.section}. {c.text}" for c in chunks]
    provider = emb.get_provider(db)
    vectors: list[list[float]] | None = None
    if provider is not None:
        try:
            vectors = provider.embed(texts)
        except emb.EmbeddingUnavailable as exc:
            log.warning("Embedding failed during ingestion, chunk stored keyword-only: %s", exc)
    for i, c in enumerate(chunks):
        if vectors is not None and provider is not None:
            c.embedding = vectors[i]
            c.embedding_model = provider.name
    db.add_all(chunks)
    db.commit()
    invalidate_caches()
    return len(chunks)


def index_resource(db: Session, resource_type: str, resource_id: int) -> None:
    """Re-indexes the single description chunk of a non-document resource after a metadata edit."""
    db.execute(delete(DocumentChunk).where(DocumentChunk.resource_type == resource_type,
                                           DocumentChunk.resource_id == resource_id))
    all_chunks = [c for c in resource_passages_for(db, resource_type, resource_id)]
    provider = emb.get_provider(db)
    if provider and all_chunks:
        try:
            vecs = provider.embed([c.text for c in all_chunks])
            for c, v in zip(all_chunks, vecs):
                c.embedding, c.embedding_model = v, provider.name
        except emb.EmbeddingUnavailable:
            pass
    db.add_all(all_chunks)
    db.commit()
    invalidate_caches()


def resource_passages_for(db: Session, resource_type: str, resource_id: int) -> list[DocumentChunk]:
    return resource_passages(db, only=(resource_type, resource_id))


def remove_resource(db: Session, resource_type: str, resource_id: int) -> None:
    db.execute(delete(DocumentChunk).where(DocumentChunk.resource_type == resource_type,
                                           DocumentChunk.resource_id == resource_id))
    db.commit()
    invalidate_caches()


def vector_backend_name() -> str:
    return "pgvector" if VectorState.pgvector else "in-process (numpy cosine)"


def ensure_fulltext_index(db: Session) -> None:
    if settings.is_postgres:
        db.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_chunks_fts ON document_chunks USING GIN (to_tsvector('english', text))"))
        db.commit()
