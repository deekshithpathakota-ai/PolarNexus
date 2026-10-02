"""Embedding provider abstraction.

* OpenAIEmbeddingProvider — neural embeddings via any OpenAI-compatible /embeddings endpoint.
* LocalLSAEmbeddingProvider — offline fallback: TF-IDF + truncated SVD (latent semantic analysis).
  It captures co-occurrence ("sea ice" ~ "cryosphere") without any external service. The fitted
  model is persisted in the database so stored vectors remain comparable across restarts.
"""
from __future__ import annotations

import logging
import pickle
from typing import Protocol

import httpx
import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import EmbeddingModelStore

log = logging.getLogger("polarnexus.embeddings")

LOCAL_MODEL_NAME = "local-lsa-v1"


class EmbeddingProvider(Protocol):
    name: str

    def embed(self, texts: list[str]) -> list[list[float]]: ...


class EmbeddingUnavailable(RuntimeError):
    pass


class OpenAIEmbeddingProvider:
    def __init__(self) -> None:
        self.name = f"openai:{settings.EMBEDDING_MODEL}"

    def embed(self, texts: list[str]) -> list[list[float]]:
        out: list[list[float]] = []
        try:
            with httpx.Client(timeout=settings.AI_TIMEOUT_SECONDS) as client:
                for i in range(0, len(texts), 64):
                    resp = client.post(
                        f"{settings.OPENAI_BASE_URL.rstrip('/')}/embeddings",
                        headers={"Authorization": f"Bearer {settings.OPENAI_API_KEY}"},
                        json={"model": settings.EMBEDDING_MODEL, "input": texts[i : i + 64]},
                    )
                    resp.raise_for_status()
                    out.extend(d["embedding"] for d in sorted(resp.json()["data"], key=lambda d: d["index"]))
        except Exception as exc:
            raise EmbeddingUnavailable(f"Embedding API unavailable: {exc}") from exc
        return out


class LocalLSAEmbeddingProvider:
    def __init__(self, pipeline) -> None:
        self.name = LOCAL_MODEL_NAME
        self.pipeline = pipeline

    @classmethod
    def fit(cls, corpus: list[str]) -> "LocalLSAEmbeddingProvider":
        from sklearn.decomposition import TruncatedSVD
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.pipeline import make_pipeline
        from sklearn.preprocessing import Normalizer

        n_components = max(2, min(192, len(corpus) - 1))
        pipeline = make_pipeline(
            TfidfVectorizer(stop_words="english", ngram_range=(1, 2), sublinear_tf=True, min_df=1, max_df=0.8),
            TruncatedSVD(n_components=n_components, random_state=42),
            Normalizer(copy=False),
        )
        pipeline.fit(corpus)
        return cls(pipeline)

    @property
    def dim(self) -> int:
        return int(self.pipeline.named_steps["truncatedsvd"].n_components)

    def embed(self, texts: list[str]) -> list[list[float]]:
        vecs = self.pipeline.transform(texts)
        return np.asarray(vecs, dtype=np.float32).tolist()

    def save(self, db: Session) -> None:
        blob = pickle.dumps(self.pipeline)
        row = db.scalar(select(EmbeddingModelStore).where(EmbeddingModelStore.name == self.name))
        if row:
            row.blob, row.dim = blob, self.dim
        else:
            db.add(EmbeddingModelStore(name=self.name, dim=self.dim, blob=blob))
        db.commit()


_local_cache: dict[str, LocalLSAEmbeddingProvider] = {}


def load_local_provider(db: Session) -> LocalLSAEmbeddingProvider | None:
    if LOCAL_MODEL_NAME in _local_cache:
        return _local_cache[LOCAL_MODEL_NAME]
    row = db.scalar(select(EmbeddingModelStore).where(EmbeddingModelStore.name == LOCAL_MODEL_NAME))
    if not row:
        return None
    provider = LocalLSAEmbeddingProvider(pickle.loads(row.blob))  # blob is written only by this app
    _local_cache[LOCAL_MODEL_NAME] = provider
    return provider


def set_local_provider(provider: LocalLSAEmbeddingProvider) -> None:
    _local_cache[LOCAL_MODEL_NAME] = provider


def get_provider(db: Session) -> EmbeddingProvider | None:
    """Active provider for queries. Returns None if no local model has been fitted yet."""
    if settings.llm_enabled:
        return OpenAIEmbeddingProvider()
    return load_local_provider(db)


def provider_description(name: str) -> str:
    if name.startswith("openai:"):
        return f"Neural embeddings ({name.split(':', 1)[1]})"
    if name == LOCAL_MODEL_NAME:
        return "Offline semantic embeddings (TF-IDF + LSA, 192-dim). Configure an embedding API for neural embeddings."
    return name
