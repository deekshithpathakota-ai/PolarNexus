"""Knowledge entities: documents, chunks, datasets, media, expeditions, stations, researchers, topics."""
from datetime import date, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, EmbeddingType


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Document(TimestampMixin, Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(300))
    doc_type: Mapped[str] = mapped_column(String(48), index=True)
    abstract: Mapped[str] = mapped_column(Text, default="")
    content: Mapped[str] = mapped_column(Text, default="")
    authors: Mapped[list] = mapped_column(JSON, default=list)
    institution: Mapped[str] = mapped_column(String(255), default="")
    region: Mapped[str] = mapped_column(String(48), index=True)
    year: Mapped[int] = mapped_column(Integer, index=True)
    language: Mapped[str] = mapped_column(String(32), default="English")
    keywords: Mapped[list] = mapped_column(JSON, default=list)
    source: Mapped[str] = mapped_column(String(255), default="")
    file_name: Mapped[str] = mapped_column(String(255), default="")
    file_path: Mapped[str] = mapped_column(String(500), default="")
    page_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(24), default="indexed", index=True)  # processing|indexed|failed|archived
    visibility: Mapped[str] = mapped_column(String(16), default="public", index=True)  # public|internal
    is_demo: Mapped[bool] = mapped_column(Boolean, default=True)
    views: Mapped[int] = mapped_column(Integer, default=0)
    uploaded_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    chunks: Mapped[list["DocumentChunk"]] = relationship(
        back_populates="document", cascade="all, delete-orphan", order_by="DocumentChunk.chunk_index"
    )


class DocumentChunk(Base):
    """Retrievable passage. Also used for dataset/media/expedition/station descriptions so that
    every resource type participates in semantic search."""

    __tablename__ = "document_chunks"
    __table_args__ = (Index("ix_chunks_resource", "resource_type", "resource_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    resource_type: Mapped[str] = mapped_column(String(24))
    resource_id: Mapped[int] = mapped_column(Integer)
    document_id: Mapped[int | None] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), nullable=True, index=True
    )
    chunk_index: Mapped[int] = mapped_column(Integer, default=0)
    section: Mapped[str] = mapped_column(String(128), default="")
    page: Mapped[int] = mapped_column(Integer, default=1)
    text: Mapped[str] = mapped_column(Text)
    embedding = mapped_column(EmbeddingType, nullable=True)
    embedding_model: Mapped[str] = mapped_column(String(64), default="", index=True)

    document: Mapped[Document | None] = relationship(back_populates="chunks")


class EmbeddingModelStore(Base):
    """Persists the fitted local (offline) embedding model so vectors stay stable across restarts."""

    __tablename__ = "embedding_models"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True)
    dim: Mapped[int] = mapped_column(Integer)
    blob: Mapped[bytes] = mapped_column(LargeBinary)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Dataset(TimestampMixin, Base):
    __tablename__ = "datasets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(300))
    description: Mapped[str] = mapped_column(Text)
    region: Mapped[str] = mapped_column(String(48), index=True)
    data_type: Mapped[str] = mapped_column(String(48), default="Time series")
    temporal_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    temporal_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    spatial_coverage: Mapped[str] = mapped_column(String(255), default="")
    variables: Mapped[list] = mapped_column(JSON, default=list)  # [{name, unit, description}]
    source: Mapped[str] = mapped_column(String(255), default="")
    format: Mapped[str] = mapped_column(String(32), default="CSV")
    license: Mapped[str] = mapped_column(String(64), default="")
    size_label: Mapped[str] = mapped_column(String(32), default="")
    record_count: Mapped[int] = mapped_column(Integer, default=0)
    year: Mapped[int] = mapped_column(Integer, index=True)
    keywords: Mapped[list] = mapped_column(JSON, default=list)
    visibility: Mapped[str] = mapped_column(String(16), default="public")
    status: Mapped[str] = mapped_column(String(24), default="indexed")
    is_demo: Mapped[bool] = mapped_column(Boolean, default=True)
    views: Mapped[int] = mapped_column(Integer, default=0)

    records: Mapped[list["DatasetRecord"]] = relationship(
        back_populates="dataset", cascade="all, delete-orphan", order_by="DatasetRecord.id"
    )


class DatasetRecord(Base):
    __tablename__ = "dataset_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    dataset_id: Mapped[int] = mapped_column(ForeignKey("datasets.id", ondelete="CASCADE"), index=True)
    observed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    values: Mapped[dict] = mapped_column(JSON, default=dict)

    dataset: Mapped[Dataset] = relationship(back_populates="records")


class Media(TimestampMixin, Base):
    __tablename__ = "media"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(300))
    description: Mapped[str] = mapped_column(Text)
    media_type: Mapped[str] = mapped_column(String(24), index=True)  # image|video|infographic
    category: Mapped[str] = mapped_column(String(48), index=True)
    region: Mapped[str] = mapped_column(String(48), index=True)
    year: Mapped[int] = mapped_column(Integer, index=True)
    credit: Mapped[str] = mapped_column(String(255), default="")
    license: Mapped[str] = mapped_column(String(128), default="")
    tags: Mapped[list] = mapped_column(JSON, default=list)
    scene: Mapped[str] = mapped_column(String(32), default="ice")  # artwork variant for the prototype renderer
    duration: Mapped[str] = mapped_column(String(16), default="")
    file_path: Mapped[str] = mapped_column(String(500), default="")
    visibility: Mapped[str] = mapped_column(String(16), default="public")
    is_demo: Mapped[bool] = mapped_column(Boolean, default=True)
    views: Mapped[int] = mapped_column(Integer, default=0)
    # ---- ingestion fields (added in v2; all nullable/defaulted so existing rows stay valid)
    status: Mapped[str] = mapped_column(String(24), default="indexed", server_default="indexed")  # indexed|archived
    filename: Mapped[str] = mapped_column(String(255), default="", server_default="")
    mime_type: Mapped[str] = mapped_column(String(64), default="", server_default="")
    size_bytes: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    thumbnail_path: Mapped[str] = mapped_column(String(500), default="", server_default="")
    captured_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    location: Mapped[str] = mapped_column(String(255), default="", server_default="")
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    exif: Mapped[dict] = mapped_column(JSON, default=dict, nullable=True)
    transcript: Mapped[str] = mapped_column(Text, default="", server_default="")
    transcript_source: Mapped[str] = mapped_column(String(48), default="", server_default="")  # stt|uploaded|""
    processing_status: Mapped[str] = mapped_column(String(32), default="ready", server_default="ready", index=True)
    processing_steps: Mapped[list] = mapped_column(JSON, default=list, nullable=True)
    processing_error: Mapped[str] = mapped_column(Text, default="", server_default="")
    uploaded_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)


class InstitutionalActivity(TimestampMixin, Base):
    """Workshops, seminars, outreach events, announcements, achievements… (SIH26063 institutional activities)."""

    __tablename__ = "institutional_activities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(300))
    description: Mapped[str] = mapped_column(Text, default="")
    activity_type: Mapped[str] = mapped_column(String(48), index=True)
    date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    location: Mapped[str] = mapped_column(String(255), default="")
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    region: Mapped[str] = mapped_column(String(48), default="India", index=True)
    organisation: Mapped[str] = mapped_column(String(255), default="", index=True)
    department: Mapped[str] = mapped_column(String(255), default="")
    audience: Mapped[str] = mapped_column(String(120), default="")
    outcomes: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(24), default="completed", index=True)  # upcoming|ongoing|completed|cancelled|archived
    visibility: Mapped[str] = mapped_column(String(16), default="public", index=True)
    featured: Mapped[bool] = mapped_column(Boolean, default=False)
    cover_scene: Mapped[str] = mapped_column(String(32), default="station")  # prototype artwork variant
    cover_media_id: Mapped[int | None] = mapped_column(ForeignKey("media.id", ondelete="SET NULL"), nullable=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=True)
    views: Mapped[int] = mapped_column(Integer, default=0)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)


class Provenance(Base):
    """Where a knowledge object came from and how far it has been verified. One row per resource;
    kept in its own table so every resource type (and outreach content) shares one model."""

    __tablename__ = "provenance"
    __table_args__ = (UniqueConstraint("resource_type", "resource_id", name="uq_provenance_resource"),
                      Index("ix_provenance_status", "verification_status"))

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    resource_type: Mapped[str] = mapped_column(String(24))
    resource_id: Mapped[int] = mapped_column(Integer)
    source_organisation: Mapped[str] = mapped_column(String(255), default="")
    source_type: Mapped[str] = mapped_column(String(64), default="")
    source_url: Mapped[str] = mapped_column(String(500), default="")
    original_identifier: Mapped[str] = mapped_column(String(255), default="")
    license: Mapped[str] = mapped_column(String(255), default="")
    publication_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    collection_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    imported_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    verification_status: Mapped[str] = mapped_column(String(24), default="unverified")
    verified_by: Mapped[str] = mapped_column(String(255), default="")
    data_quality: Mapped[str] = mapped_column(String(120), default="")
    provenance_notes: Mapped[str] = mapped_column(Text, default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Expedition(TimestampMixin, Base):
    __tablename__ = "expeditions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    number: Mapped[int] = mapped_column(Integer, default=0)
    program: Mapped[str] = mapped_column(String(48), index=True)  # Antarctic|Arctic|Southern Ocean|Himalayan
    region: Mapped[str] = mapped_column(String(48), index=True)
    season: Mapped[str] = mapped_column(String(32))
    year: Mapped[int] = mapped_column(Integer, index=True)
    objective: Mapped[str] = mapped_column(Text)
    themes: Mapped[list] = mapped_column(JSON, default=list)
    participants: Mapped[int] = mapped_column(Integer, default=0)
    leader: Mapped[str] = mapped_column(String(128), default="")
    vessel: Mapped[str] = mapped_column(String(128), default="")
    highlights: Mapped[list] = mapped_column(JSON, default=list)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    verified_note: Mapped[str] = mapped_column(String(500), default="")
    is_demo: Mapped[bool] = mapped_column(Boolean, default=True)
    views: Mapped[int] = mapped_column(Integer, default=0)


class Station(TimestampMixin, Base):
    __tablename__ = "stations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160))
    kind: Mapped[str] = mapped_column(String(48), default="Research station")
    region: Mapped[str] = mapped_column(String(48), index=True)
    country: Mapped[str] = mapped_column(String(64), default="India")
    location_name: Mapped[str] = mapped_column(String(255), default="")
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    established: Mapped[str] = mapped_column(String(32), default="")
    status: Mapped[str] = mapped_column(String(64), default="Operational")
    themes: Mapped[list] = mapped_column(JSON, default=list)
    description: Mapped[str] = mapped_column(Text)
    facts_source: Mapped[str] = mapped_column(String(500), default="")
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    views: Mapped[int] = mapped_column(Integer, default=0)


class Researcher(TimestampMixin, Base):
    __tablename__ = "researchers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160))
    title: Mapped[str] = mapped_column(String(160), default="")
    institution: Mapped[str] = mapped_column(String(255), default="")
    expertise: Mapped[list] = mapped_column(JSON, default=list)
    bio: Mapped[str] = mapped_column(Text, default="")
    is_demo: Mapped[bool] = mapped_column(Boolean, default=True)


class Topic(Base):
    __tablename__ = "topics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    category: Mapped[str] = mapped_column(String(48), index=True)
    description: Mapped[str] = mapped_column(Text, default="")


class ResourceTopic(Base):
    __tablename__ = "resource_topics"
    __table_args__ = (
        UniqueConstraint("resource_type", "resource_id", "topic_id", name="uq_resource_topic"),
        Index("ix_rt_resource", "resource_type", "resource_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    resource_type: Mapped[str] = mapped_column(String(24))
    resource_id: Mapped[int] = mapped_column(Integer)
    topic_id: Mapped[int] = mapped_column(ForeignKey("topics.id", ondelete="CASCADE"), index=True)


class ResourceLink(Base):
    """Typed, bidirectional-readable relationship between any two knowledge entities."""

    __tablename__ = "resource_links"
    __table_args__ = (
        UniqueConstraint("source_type", "source_id", "target_type", "target_id", "relation", name="uq_link"),
        Index("ix_link_source", "source_type", "source_id"),
        Index("ix_link_target", "target_type", "target_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_type: Mapped[str] = mapped_column(String(24))
    source_id: Mapped[int] = mapped_column(Integer)
    target_type: Mapped[str] = mapped_column(String(24))
    target_id: Mapped[int] = mapped_column(Integer)
    relation: Mapped[str] = mapped_column(String(48), default="related")
