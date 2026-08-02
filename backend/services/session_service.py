"""
services/session_service.py — Session lifecycle management.
"""

import structlog

from backend.llm_service.llm_service import LLMService
from backend.models.orm import Message, Session
from backend.repositories.message_repo import MessageRepository
from backend.repositories.session_repo import SessionRepository

logger = structlog.get_logger(__name__)


class SessionService:
    def __init__(
        self,
        session_repo: SessionRepository,
        message_repo: MessageRepository,
        llm_service: LLMService,
    ) -> None:
        self._sessions = session_repo
        self._messages = message_repo
        self._llm = llm_service

    async def create_session(self, llm_provider: str, embedding_model: str) -> Session:
        session = await self._sessions.create(
            llm_provider=llm_provider,
            embedding_model=embedding_model,
        )
        logger.info("session_created", session_id=session.id)
        return session

    async def list_sessions(self) -> list[Session]:
        return await self._sessions.list_all()

    async def get_session_with_messages(self, session_id: str) -> tuple[Session, list[Message]]:
        session = await self._sessions.get(session_id)
        if session is None:
            raise ValueError(f"Session not found: {session_id}")
        messages = await self._messages.get_session_messages(session_id)
        return session, messages

    async def generate_title(self, session_id: str, first_message: str) -> str:
        """Generate a human-readable title from the first user message."""
        try:
            title = await self._llm.generate(
                messages=[
                    {
                        "role": "user",
                        "content": (
                            f"Generate a short, descriptive title (max 8 words) for a conversation "
                            f"that starts with this message: \"{first_message[:200]}\"\n"
                            "Output only the title, no quotes, no explanation."
                        ),
                    }
                ],
                system_prompt="You generate concise chat session titles.",
                max_tokens=30,
            )
            title = title.strip().strip('"').strip("'")[:255]
        except Exception as e:
            logger.warning("title_generation_failed", error=str(e))
            title = first_message[:60].strip()

        await self._sessions.update_title(session_id, title)
        logger.info("session_title_set", session_id=session_id, title=title)
        return title

    async def get_history_as_dicts(self, session_id: str) -> list[dict]:
        """Return message history as list of {"role", "content"} dicts."""
        messages = await self._messages.get_session_messages(session_id)
        return [{"role": m.role, "content": m.content} for m in messages]

    async def delete_session(self, session_id: str) -> bool:
        """Delete a session by ID."""
        deleted = await self._sessions.delete(session_id)
        if deleted:
            logger.info("session_deleted", session_id=session_id)
        return deleted
