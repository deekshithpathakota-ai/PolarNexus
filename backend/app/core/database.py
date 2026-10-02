"""Database engine, session handling and vector-backend detection."""
import logging
from collections.abc import Generator

from sqlalchemy import JSON, create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.types import TypeDecorator

from app.core.config import settings

log = logging.getLogger("polarnexus.db")

_connect_args = {"check_same_thread": False} if settings.sqlalchemy_url.startswith("sqlite") else {}
engine = create_engine(settings.sqlalchemy_url, pool_pre_ping=True, connect_args=_connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class VectorState:
    """Which vector backend is active. Decided once at startup, before tables are created."""

    pgvector: bool = False


def detect_vector_backend() -> bool:
    if not settings.is_postgres:
        VectorState.pgvector = False
        return False
    try:
        with engine.begin() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        VectorState.pgvector = True
    except Exception as exc:  # extension not installed / no permission
        log.warning("pgvector unavailable, using in-process vector search fallback: %s", exc)
        VectorState.pgvector = False
    return VectorState.pgvector


class EmbeddingType(TypeDecorator):
    """Stores embeddings as pgvector `vector` when available, otherwise as JSON arrays."""

    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql" and VectorState.pgvector:
            from pgvector.sqlalchemy import Vector

            return dialect.type_descriptor(Vector())
        return dialect.type_descriptor(JSON())

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return [float(v) for v in value]

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return [float(v) for v in value]


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def db_healthy() -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
