"""Pydantic request/response schemas."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=200)


class DemoLoginRequest(BaseModel):
    role: Literal["public", "researcher", "editor", "admin"]


class UserOut(BaseModel):
    id: int
    email: str
    name: str
    role: str
    role_label: str
    institution: str
    permissions: list[str]
    is_demo: bool


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class AskRequest(BaseModel):
    question: str = Field(min_length=2, max_length=1000)
    document_slug: str | None = Field(default=None, max_length=160)
    mode: Literal["hybrid", "keyword", "semantic"] = "hybrid"
    # v3 educational modes; omitted = the original behaviour
    audience: Literal["researcher", "teacher", "student", "public"] | None = None

    @field_validator("question")
    @classmethod
    def strip_q(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2:
            raise ValueError("Please enter a question.")
        return v


class SummaryRequest(BaseModel):
    document_slug: str = Field(max_length=160)
    kind: Literal["executive", "research", "student", "100-word", "key-findings", "methodology", "impact"]


class FeedbackRequest(BaseModel):
    query_id: int
    feedback: Literal["up", "down"]


class SemanticSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    page: int = Field(default=1, ge=1, le=500)
    page_size: int = Field(default=12, ge=1, le=60)


class GenerateRequest(BaseModel):
    format: Literal["website", "linkedin", "instagram", "student", "public", "media",
                    "summary", "newsletter", "expedition_update", "highlight"]
    resource_type: Literal["document", "dataset", "topic", "chunks", "expedition", "station", "researcher", "activity"] = "document"
    resource_slug: str | None = Field(default=None, max_length=160)
    chunk_ids: list[int] | None = Field(default=None, max_length=12)
    audience: Literal["researchers", "students", "teachers", "general_public", "media", "policy"] | None = None


class TranslateRequest(BaseModel):
    language: Literal["Hindi", "Telugu"]


class ContentUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=300)
    body: str | None = Field(default=None, min_length=10, max_length=20000)


class ReviewAction(BaseModel):
    content_id: int | None = None
    action: Literal["approve", "reject", "request_changes", "publish", "comment"] | None = None
    comment: str = Field(default="", max_length=4000)
    channels: list[Literal["website", "linkedin", "instagram", "newsletter", "education_portal"]] = Field(default_factory=lambda: ["website"])
    acknowledge_warnings: bool = False


class DocumentCreate(BaseModel):
    title: str = Field(min_length=3, max_length=300)
    doc_type: Literal["Research Paper", "Technical Report", "Expedition Report", "Educational Resource", "News / Outreach"]
    abstract: str = Field(min_length=20, max_length=5000)
    content: str = Field(default="", max_length=200000)
    authors: list[str] = Field(default_factory=list, max_length=30)
    institution: str = Field(default="", max_length=255)
    region: Literal["Antarctic", "Arctic", "Southern Ocean", "Himalaya", "India"]
    year: int = Field(ge=1900, le=2100)
    keywords: list[str] = Field(default_factory=list, max_length=30)
    topics: list[str] = Field(default_factory=list, max_length=10)
    visibility: Literal["public", "internal"] = "public"
    language: str = Field(default="English", max_length=32)


class MetadataUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=300)
    abstract: str | None = Field(default=None, max_length=5000)
    description: str | None = Field(default=None, max_length=5000)
    region: Literal["Antarctic", "Arctic", "Southern Ocean", "Himalaya", "India"] | None = None
    year: int | None = Field(default=None, ge=1900, le=2100)
    keywords: list[str] | None = Field(default=None, max_length=30)
    topics: list[str] | None = Field(default=None, max_length=10)
    visibility: Literal["public", "internal"] | None = None
    status: Literal["indexed", "archived"] | None = None
    doc_type: str | None = Field(default=None, max_length=48)


class UserCreate(BaseModel):
    email: EmailStr
    name: str = Field(min_length=2, max_length=128)
    role: Literal["public", "researcher", "editor", "admin"]
    institution: str = Field(default="", max_length=255)
    password: str = Field(min_length=10, max_length=200)


class UserUpdate(BaseModel):
    role: Literal["public", "researcher", "editor", "admin"] | None = None
    is_active: bool | None = None
    name: str | None = Field(default=None, min_length=2, max_length=128)


class TopicCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    category: str = Field(min_length=2, max_length=48)
    description: str = Field(default="", max_length=1000)


class SavedCreate(BaseModel):
    item_type: Literal["document", "dataset", "media", "expedition", "station", "researcher", "search"]
    item_slug: str = Field(default="", max_length=300)
    label: str = Field(min_length=1, max_length=300)
    query: dict = Field(default_factory=dict)
