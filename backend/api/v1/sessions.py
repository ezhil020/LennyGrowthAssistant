"""api/v1/sessions.py — Session management endpoints."""

from fastapi import APIRouter, Depends

from backend.models.schemas import (
    SessionCreate,
    SessionDetailResponse,
    SessionListResponse,
    SessionResponse,
    MessageResponse,
)
from backend.models.source import SourceAttribution
from backend.services.dependencies import get_session_service
from backend.services.session_service import SessionService

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("", response_model=SessionResponse, status_code=201)
async def create_session(
    body: SessionCreate,
    svc: SessionService = Depends(get_session_service),
):
    session = await svc.create_session(
        llm_provider=body.llm_provider,
        embedding_model=body.embedding_model,
    )
    return session


@router.get("", response_model=SessionListResponse)
async def list_sessions(svc: SessionService = Depends(get_session_service)):
    sessions = await svc.list_sessions()
    return {"sessions": sessions}


@router.get("/{session_id}", response_model=SessionDetailResponse)
async def get_session(
    session_id: str,
    svc: SessionService = Depends(get_session_service),
):
    session, messages = await svc.get_session_with_messages(session_id)

    msg_responses = []
    for msg in messages:
        sources = None
        if msg.sources_json:
            try:
                sources = SourceAttribution(**msg.sources_json)
            except Exception:
                pass
        msg_responses.append(
            MessageResponse(
                id=msg.id,
                session_id=msg.session_id,
                role=msg.role,
                content=msg.content,
                skill_used=msg.skill_used,
                routing_intent=msg.routing_intent,
                sources=sources,
                created_at=msg.created_at,
            )
        )

    return SessionDetailResponse(session=session, messages=msg_responses)
