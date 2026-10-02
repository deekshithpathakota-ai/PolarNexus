"""v3 entities: research stories, outreach campaigns, version history, visual embeddings, dataset upload staging.

All tables are new (created by `create_all`); nothing here alters an existing table.
"""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import JSON, Boolean, Date, DateTime, Float, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, EmbeddingType


class ResearchStory(Base):
    """A connected, evidence-grounded narrative: topic → paper → dataset → expedition → place → media → people."""

    __tablename__ = "research_stories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(300))
    # [{"type": "document", "id": 1, "role": "Research paper", "note": ""}] in story order
    items: Mapped[list] = mapped_column(JSON, default=list)
    seed_type: Mapped[str] = mapped_column(String(24), default="")
    seed_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # cached grounded summaries: {"scientific": {...}, "public": {...}, "student": {...}}
    summaries: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(24), default="draft", index=True)  # draft|published|archived
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    views: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    audiences: Mapped[list] = mapped_column(JSON, default=list)
    topics: Mapped[list] = mapped_column(JSON, default=list)  # topic slugs
    channels: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(24), default="draft", index=True)  # draft|scheduled|published|archived
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    items: Mapped[list["CampaignItem"]] = relationship(back_populates="campaign", cascade="all, delete-orphan",
                                                       order_by="CampaignItem.scheduled_for")


class CampaignItem(Base):
    """One planned piece of outreach on the content calendar. Publishing always goes through the review workflow."""

    __tablename__ = "campaign_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id", ondelete="CASCADE"), index=True)
    content_id: Mapped[int | None] = mapped_column(ForeignKey("generated_content.id", ondelete="SET NULL"), nullable=True)
    title: Mapped[str] = mapped_column(String(300))
    content_type: Mapped[str] = mapped_column(String(48), default="")
    channel: Mapped[str] = mapped_column(String(32), default="website")
    audience: Mapped[str] = mapped_column(String(32), default="")
    scheduled_for: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(24), default="planned")  # planned|scheduled|published|cancelled
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    campaign: Mapped[Campaign] = relationship(back_populates="items")


class ResourceVersion(Base):
    """Append-only version history. Rows are never updated or deleted by the application."""

    __tablename__ = "resource_versions"
    __table_args__ = (Index("ix_versions_resource", "resource_type", "resource_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    resource_type: Mapped[str] = mapped_column(String(24))
    resource_id: Mapped[int] = mapped_column(Integer)
    version: Mapped[int] = mapped_column(Integer)
    change: Mapped[str] = mapped_column(String(300))
    status: Mapped[str] = mapped_column(String(32), default="")
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    user_name: Mapped[str] = mapped_column(String(160), default="")
    snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class VisualEmbedding(Base):
    """CLIP image embedding of a photograph or of one representative video frame (frame_seconds set)."""

    __tablename__ = "visual_embeddings"
    __table_args__ = (Index("ix_visual_media", "media_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    media_id: Mapped[int] = mapped_column(ForeignKey("media.id", ondelete="CASCADE"))
    frame_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    frame_path: Mapped[str] = mapped_column(String(500), default="")
    model: Mapped[str] = mapped_column(String(96), index=True)
    embedding = mapped_column(EmbeddingType, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DatasetUpload(Base):
    """Staged CSV/JSON upload awaiting user confirmation (analysis is stored so confirmation is deterministic)."""

    __tablename__ = "dataset_uploads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    token: Mapped[str] = mapped_column(String(48), unique=True, index=True)
    filename: Mapped[str] = mapped_column(String(255))
    file_key: Mapped[str] = mapped_column(String(500))
    file_format: Mapped[str] = mapped_column(String(16))
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    content_hash: Mapped[str] = mapped_column(String(64), default="", index=True)
    analysis: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(24), default="analyzed")  # analyzed|registering|registered|failed|cancelled
    error: Mapped[str] = mapped_column(Text, default="")
    steps: Mapped[list] = mapped_column(JSON, default=list)
    dataset_id: Mapped[int | None] = mapped_column(ForeignKey("datasets.id", ondelete="SET NULL"), nullable=True)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class OutreachEvent(Base):
    """Engagement on published outreach. `is_demo` rows are seeded demonstration metrics and are always labelled."""

    __tablename__ = "outreach_events"
    __table_args__ = (Index("ix_outreach_events_content", "content_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    content_id: Mapped[int] = mapped_column(ForeignKey("generated_content.id", ondelete="CASCADE"))
    campaign_id: Mapped[int | None] = mapped_column(ForeignKey("campaigns.id", ondelete="SET NULL"), nullable=True)
    event: Mapped[str] = mapped_column(String(24))  # view|click|share|complete
    channel: Mapped[str] = mapped_column(String(32), default="website")
    audience: Mapped[str] = mapped_column(String(32), default="")
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    count: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
