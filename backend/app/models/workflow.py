"""Outreach workflow: generated content, citations, reviews, ingestion jobs, notifications, saved items."""
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class GeneratedContent(Base):
    __tablename__ = "generated_content"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(300))
    format: Mapped[str] = mapped_column(String(32), index=True)  # website|linkedin|instagram|student|public|media
    body: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(24), default="draft", index=True)
    generation_mode: Mapped[str] = mapped_column(String(24), default="template")  # llm|template|curated_demo|manual
    evidence_check: Mapped[dict] = mapped_column(JSON, default=dict)
    resource_type: Mapped[str] = mapped_column(String(24), default="document")
    resource_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    resource_title: Mapped[str] = mapped_column(String(300), default="")
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewer_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    channels: Mapped[list] = mapped_column(JSON, default=list)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    audience: Mapped[str] = mapped_column(String(32), default="", server_default="")
    language: Mapped[str] = mapped_column(String(32), default="English", server_default="English")
    translated_from: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    citations: Mapped[list["Citation"]] = relationship(
        back_populates="content", cascade="all, delete-orphan", order_by="Citation.position"
    )
    reviews: Mapped[list["Review"]] = relationship(
        back_populates="content", cascade="all, delete-orphan", order_by="Review.created_at"
    )


class Citation(Base):
    __tablename__ = "citations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    content_id: Mapped[int] = mapped_column(ForeignKey("generated_content.id", ondelete="CASCADE"), index=True)
    chunk_id: Mapped[int | None] = mapped_column(ForeignKey("document_chunks.id", ondelete="SET NULL"), nullable=True)
    position: Mapped[int] = mapped_column(Integer, default=1)
    resource_type: Mapped[str] = mapped_column(String(24))
    resource_id: Mapped[int] = mapped_column(Integer)
    resource_slug: Mapped[str] = mapped_column(String(160), default="")
    label: Mapped[str] = mapped_column(String(300))
    section: Mapped[str] = mapped_column(String(128), default="")
    page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    quote: Mapped[str] = mapped_column(Text, default="")

    content: Mapped[GeneratedContent] = relationship(back_populates="citations")


class Review(Base):
    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    content_id: Mapped[int] = mapped_column(ForeignKey("generated_content.id", ondelete="CASCADE"), index=True)
    reviewer_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewer_name: Mapped[str] = mapped_column(String(128), default="")
    action: Mapped[str] = mapped_column(String(32))  # submitted|approved|rejected|changes_requested|published|edited
    comment: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    content: Mapped[GeneratedContent] = relationship(back_populates="reviews")


class IngestionJob(Base):
    __tablename__ = "ingestion_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[int | None] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), nullable=True)
    file_name: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(24), default="queued")
    steps: Mapped[list] = mapped_column(JSON, default=list)
    error: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    role: Mapped[str] = mapped_column(String(32), default="", index=True)  # broadcast to a role when user_id is null
    kind: Mapped[str] = mapped_column(String(32), default="info")
    title: Mapped[str] = mapped_column(String(255))
    body: Mapped[str] = mapped_column(Text, default="")
    link: Mapped[str] = mapped_column(String(255), default="")
    read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SavedItem(Base):
    __tablename__ = "saved_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    item_type: Mapped[str] = mapped_column(String(24))  # document|dataset|media|expedition|station|search
    item_slug: Mapped[str] = mapped_column(String(300), default="")
    label: Mapped[str] = mapped_column(String(300))
    query: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
