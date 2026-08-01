"""services/dependencies.py — FastAPI Depends for all services."""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.llm_service.dependencies import get_llm_service
from backend.llm_service.llm_service import LLMService
from backend.repositories.dependencies import (
    get_artifact_repo,
    get_chunk_repo,
    get_message_repo,
    get_session_repo,
)
from backend.repositories.artifact_repo import ArtifactRepository
from backend.repositories.chunk_repo import ChunkRepository
from backend.repositories.message_repo import MessageRepository
from backend.repositories.session_repo import SessionRepository
from backend.retrieval.retrieval_service import RetrievalService, get_retrieval_service
from backend.services.artifact_service import ArtifactService
from backend.services.chat_service import ChatService
from backend.services.provider_service import ProviderService
from backend.services.session_service import SessionService


async def get_session_service(
    session_repo: SessionRepository = Depends(get_session_repo),
    message_repo: MessageRepository = Depends(get_message_repo),
    llm_service: LLMService = Depends(get_llm_service),
) -> SessionService:
    return SessionService(session_repo, message_repo, llm_service)


async def get_artifact_service(
    artifact_repo: ArtifactRepository = Depends(get_artifact_repo),
) -> ArtifactService:
    return ArtifactService(artifact_repo)


async def get_provider_service() -> ProviderService:
    return ProviderService()


async def get_chat_service(
    llm_service: LLMService = Depends(get_llm_service),
    retrieval_service: RetrievalService = Depends(get_retrieval_service),
    session_repo: SessionRepository = Depends(get_session_repo),
    message_repo: MessageRepository = Depends(get_message_repo),
    artifact_repo: ArtifactRepository = Depends(get_artifact_repo),
) -> ChatService:
    return ChatService(
        llm_service=llm_service,
        retrieval_service=retrieval_service,
        session_repo=session_repo,
        message_repo=message_repo,
        artifact_repo=artifact_repo,
    )
