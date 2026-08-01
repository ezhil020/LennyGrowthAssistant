"""
models/schemas.py — Pydantic v2 request/response schemas for all API endpoints.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from backend.models.source import SourceAttribution


# ── Sessions ─────────────────────────────────────────────────────────────────

class SessionCreate(BaseModel):
    llm_provider: str = "anthropic"
    embedding_model: str = "ollama"


class SessionResponse(BaseModel):
    id: str
    title: str
    created_at: datetime
    llm_provider: str
    embedding_model: str

    model_config = {"from_attributes": True}


class SessionListResponse(BaseModel):
    sessions: list[SessionResponse]


# ── Messages ──────────────────────────────────────────────────────────────────

class MessageResponse(BaseModel):
    id: str
    session_id: str
    role: str
    content: str
    skill_used: str | None
    routing_intent: str | None
    sources: SourceAttribution | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class SessionDetailResponse(BaseModel):
    session: SessionResponse
    messages: list[MessageResponse]


# ── Chat ──────────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=10_000)
    stream: bool = True


# ── Artifacts ────────────────────────────────────────────────────────────────

class ArtifactResponse(BaseModel):
    id: str
    message_id: str
    session_id: str
    type: str                   # "markdown" | "html"
    content: str
    version: int
    title: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ArtifactUpdateRequest(BaseModel):
    content: str = Field(..., min_length=1)
    title: str | None = None


# ── Provider Config ───────────────────────────────────────────────────────────

class ProviderInfo(BaseModel):
    name: str
    is_active: bool
    model: str


class ProvidersResponse(BaseModel):
    providers: list[ProviderInfo]
    active: str


class SetProviderRequest(BaseModel):
    provider: str = Field(..., pattern="^(anthropic|ollama)$")


# ── Health ────────────────────────────────────────────────────────────────────

class HealthCheck(BaseModel):
    status: str                     # "ok" | "degraded" | "error"
    checks: dict[str, str]          # e.g. {"database": "ok", "llm_provider": "error"}


# ── Ingestion ────────────────────────────────────────────────────────────────

class IngestRequest(BaseModel):
    limit: int = Field(default=50, ge=0, le=500)


class IngestResponse(BaseModel):
    status: str
    message: str


# ── SSE events ───────────────────────────────────────────────────────────────

class SSEEvent(BaseModel):
    """Structured SSE event payload sent to the frontend."""
    event: str          # "token" | "done" | "artifact" | "sources" | "error"
    data: Any
