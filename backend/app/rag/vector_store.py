"""Vector similarity search: pgvector when available, otherwise an in-process numpy index."""
from __future__ import annotations

import numpy as np
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.database import VectorState
from app.models import DocumentChunk

_cache: dict[str, tuple[np.ndarray, list[int]]] = {}
_version = {"n": 0}


def invalidate_caches() -> None:
    _cache.clear()
    _version["n"] += 1
    from app.search import keyword

    keyword.invalidate()


def _matrix(db: Session, model: str) -> tuple[np.ndarray, list[int]]:
    if model not in _cache:
        rows = db.execute(
            select(DocumentChunk.id, DocumentChunk.embedding).where(
                DocumentChunk.embedding_model == model, DocumentChunk.embedding.is_not(None))
        ).all()
        ids = [r[0] for r in rows]
        mat = np.asarray([r[1] for r in rows], dtype=np.float32) if rows else np.zeros((0, 1), dtype=np.float32)
        if len(mat):
            norms = np.linalg.norm(mat, axis=1, keepdims=True)
            mat = mat / np.where(norms == 0, 1, norms)
        _cache[model] = (mat, ids)
    return _cache[model]


def vector_search(db: Session, query_vec: list[float], model: str, k: int = 60,
                  document_id: int | None = None) -> list[tuple[int, float]]:
    """Returns [(chunk_id, cosine_similarity)] best-first."""
    if VectorState.pgvector:
        qv = "[" + ",".join(f"{x:.6f}" for x in query_vec) + "]"
        where = "embedding_model = :m AND embedding IS NOT NULL"
        params: dict = {"m": model, "q": qv, "k": k}
        if document_id is not None:
            where += " AND document_id = :d"
            params["d"] = document_id
        rows = db.execute(text(
            f"SELECT id, 1 - (embedding <=> CAST(:q AS vector)) AS score FROM document_chunks "
            f"WHERE {where} ORDER BY embedding <=> CAST(:q AS vector) LIMIT :k"), params).all()
        return [(int(r[0]), float(r[1])) for r in rows]

    mat, ids = _matrix(db, model)
    if not len(ids):
        return []
    q = np.asarray(query_vec, dtype=np.float32)
    q = q / (np.linalg.norm(q) or 1.0)
    scores = mat @ q
    if document_id is not None:
        allowed = set(db.scalars(select(DocumentChunk.id).where(DocumentChunk.document_id == document_id)))
        mask = np.array([i in allowed for i in ids])
        scores = np.where(mask, scores, -1.0)
    order = np.argsort(-scores)[:k]
    return [(ids[i], float(scores[i])) for i in order if scores[i] > -1.0]
