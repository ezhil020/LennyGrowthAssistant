"""repositories/session_repo.py — Session CRUD."""

from sqlalchemy import select

from backend.models.orm import Session
from backend.repositories.base import BaseRepository


class SessionRepository(BaseRepository[Session]):
    model = Session

    async def list_all(self) -> list[Session]:
        result = await self.db.execute(
            select(Session).order_by(Session.created_at.desc())
        )
        return list(result.scalars().all())

    async def update_title(self, session_id: str, title: str) -> Session | None:
        session = await self.get(session_id)
        if session is None:
            return None
        session.title = title[:255]
        await self.db.flush()
        await self.db.refresh(session)
        return session
