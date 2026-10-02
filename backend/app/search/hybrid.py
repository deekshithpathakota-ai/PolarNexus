"""Hybrid retrieval: keyword (full-text/BM25) + semantic (vector) fused with Reciprocal Rank Fusion."""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import DocumentChunk
from app.rag import embeddings as emb
from app.rag.vector_store import vector_search
from app.search.keyword import _build as bm25_index
from app.search.keyword import keyword_search
from app.utils.text import content_terms, normalize, stem

log = logging.getLogger("polarnexus.search")
RRF_K = 60


@dataclass
class ChunkHit:
    chunk: DocumentChunk
    score: float = 0.0
    keyword_rank: int | None = None
    vector_rank: int | None = None
    vector_sim: float = 0.0
    keyword_score: float = 0.0
    term_coverage: float = 0.0
    matched_terms: list[str] = field(default_factory=list)


@dataclass
class Retrieval:
    hits: list[ChunkHit]
    mode_used: str
    semantic_available: bool
    notice: str = ""


def retrieve(db: Session, query: str, mode: str = "hybrid", k: int = 40,
             document_id: int | None = None) -> Retrieval:
    mode = mode if mode in {"keyword", "semantic", "hybrid"} else "hybrid"
    kw: list[tuple[int, float]] = []
    vec: list[tuple[int, float]] = []
    semantic_available = True
    notice = ""

    if mode in {"keyword", "hybrid"}:
        kw = keyword_search(db, query, k=k * 2, document_id=document_id)
    if mode in {"semantic", "hybrid"}:
        provider = emb.get_provider(db)
        if provider is None:
            semantic_available, notice = False, "Semantic index not built yet — showing keyword results."
        else:
            try:
                qvec = provider.embed([query])[0]
                vec = vector_search(db, qvec, provider.name, k=k * 2, document_id=document_id)
            except emb.EmbeddingUnavailable as exc:
                log.warning("semantic search unavailable: %s", exc)
                semantic_available = False
                notice = "Semantic search temporarily unavailable — showing keyword results."
        if not semantic_available and not kw:
            kw = keyword_search(db, query, k=k * 2, document_id=document_id)

    fused: dict[int, ChunkHit] = {}
    for rank, (cid, s) in enumerate(kw):
        h = fused.setdefault(cid, ChunkHit(chunk=None))  # type: ignore[arg-type]
        h.keyword_rank, h.keyword_score = rank + 1, s
        h.score += 1.0 / (RRF_K + rank + 1)
    for rank, (cid, sim) in enumerate(vec):
        if sim <= 0.05:  # ignore near-orthogonal vectors
            continue
        h = fused.setdefault(cid, ChunkHit(chunk=None))  # type: ignore[arg-type]
        h.vector_rank, h.vector_sim = rank + 1, sim
        h.score += 1.0 / (RRF_K + rank + 1)

    if not fused:
        used = "keyword" if not semantic_available else mode
        return Retrieval([], used, semantic_available, notice)

    chunks = {c.id: c for c in db.scalars(select(DocumentChunk).where(DocumentChunk.id.in_(list(fused))))}
    qterms = content_terms(query)
    qstems = {stem(t): t for t in qterms}
    idx = bm25_index(db)
    idf = {s: math.log(1 + (idx["n"] - idx["df"].get(s, 0) + 0.5) / (idx["df"].get(s, 0) + 0.5)) for s in qstems}
    idf_total = sum(idf.values()) or 1.0
    hits = []
    for cid, h in fused.items():
        if cid not in chunks:
            continue
        h.chunk = chunks[cid]
        ctext = normalize(h.chunk.text + " " + h.chunk.section)
        cstems = {stem(t) for t in content_terms(ctext)}
        matched = [orig for s, orig in qstems.items() if s in cstems]
        h.matched_terms = matched
        h.term_coverage = sum(idf[s] for s, orig in qstems.items() if orig in matched) / idf_total
        hits.append(h)
    hits.sort(key=lambda x: -x.score)
    used = mode if semantic_available else "keyword"
    return Retrieval(hits[:k], used, semantic_available, notice)
