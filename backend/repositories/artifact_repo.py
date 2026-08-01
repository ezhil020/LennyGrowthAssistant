"""repositories/artifact_repo.py — Artifact CRUD with versioning."""

from sqlalchemy import select

from backend.models.orm import Artifact
from backend.repositories.base import BaseRepository


class ArtifactRepository(BaseRepository[Artifact]):
    model = Artifact

    async def get_session_artifacts(self, session_id: str) -> list[Artifact]:
        result = await self.db.execute(
            select(Artifact)
            .where(Artifact.session_id == session_id)
            .order_by(Artifact.created_at.asc())
        )
        return list(result.scalars().all())

    async def get_latest_for_session(self, session_id: str) -> Artifact | None:
        result = await self.db.execute(
            select(Artifact)
            .where(Artifact.session_id == session_id)
            .order_by(Artifact.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def update_content(
        self, artifact_id: str, content: str, title: str | None = None
    ) -> Artifact | None:
        artifact = await self.get(artifact_id)
        if artifact is None:
            return None
        artifact.content = content
        artifact.version += 1
        if title is not None:
            artifact.title = title
        await self.db.flush()
        await self.db.refresh(artifact)
        return artifact
