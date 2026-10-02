"""Keyword / full-text retrieval: PostgreSQL full-text search, or an in-process BM25 fallback."""
from __future__ import annotations

import math
import re
from collections import Counter

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import DocumentChunk
from app.utils.text import content_terms, stem

_bm25: dict = {}


def invalidate() -> None:
    _bm25.clear()


def keyword_search(db: Session, query: str, k: int = 60, document_id: int | None = None) -> list[tuple[int, float]]:
    terms = [t for t in content_terms(query) if re.fullmatch(r"[a-z0-9]+", t)]
    if not terms:
        return []
    if settings.is_postgres:
        tsq = " | ".join(f"{t}:*" for t in terms[:12])
        where = "to_tsvector('english', text) @@ to_tsquery('english', :q)"
        params: dict = {"q": tsq, "k": k}
        if document_id is not None:
            where += " AND document_id = :d"
            params["d"] = document_id
        try:
            rows = db.execute(text(
                f"SELECT id, ts_rank_cd(to_tsvector('english', text), to_tsquery('english', :q), 32) AS r "
                f"FROM document_chunks WHERE {where} ORDER BY r DESC LIMIT :k"), params).all()
            return [(int(r[0]), float(r[1])) for r in rows]
        except Exception:
            db.rollback()  # fall through to BM25
    return _bm25_search(db, terms, k, document_id)


def _build(db: Session) -> dict:
    if _bm25:
        return _bm25
    rows = db.execute(select(DocumentChunk.id, DocumentChunk.text, DocumentChunk.document_id)).all()
    docs = []
    df: Counter = Counter()
    for cid, txt, did in rows:
        tf = Counter(stem(t) for t in content_terms(txt))
        docs.append((cid, did, tf, sum(tf.values())))
        df.update(tf.keys())
    n = max(1, len(docs))
    avgdl = sum(d[3] for d in docs) / n
    _bm25.update(docs=docs, df=df, n=n, avgdl=avgdl or 1.0)
    return _bm25


def _bm25_search(db: Session, terms: list[str], k: int, document_id: int | None) -> list[tuple[int, float]]:
    idx = _build(db)
    q = [stem(t) for t in terms]
    k1, b = 1.4, 0.75
    scores = []
    for cid, did, tf, dl in idx["docs"]:
        if document_id is not None and did != document_id:
            continue
        s = 0.0
        for t in q:
            f = tf.get(t, 0)
            if not f:
                continue
            idf = math.log(1 + (idx["n"] - idx["df"][t] + 0.5) / (idx["df"][t] + 0.5))
            s += idf * f * (k1 + 1) / (f + k1 * (1 - b + b * dl / idx["avgdl"]))
        if s > 0:
            scores.append((cid, s))
    scores.sort(key=lambda x: -x[1])
    return scores[:k]
