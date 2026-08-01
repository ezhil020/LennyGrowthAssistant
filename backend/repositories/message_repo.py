"""repositories/message_repo.py — Message CRUD."""

from sqlalchemy import select

from backend.models.orm import Message
from backend.repositories.base import BaseRepository


class MessageRepository(BaseRepository[Message]):
    model = Message

    async def get_session_messages(self, session_id: str) -> list[Message]:
        result = await self.db.execute(
            select(Message)
            .where(Message.session_id == session_id)
            .order_by(Message.created_at.asc())
        )
        return list(result.scalars().all())

    async def get_recent_messages(
        self, session_id: str, limit: int = 20
    ) -> list[Message]:
        result = await self.db.execute(
            select(Message)
            .where(Message.session_id == session_id)
            .order_by(Message.created_at.desc())
            .limit(limit)
        )
        msgs = list(result.scalars().all())
        return list(reversed(msgs))  # Return chronological order
