"""
services/artifact_service.py — Artifact CRUD, versioning, validation.
"""

import structlog

from backend.artifacts.validator import validate_artifact
from backend.models.orm import Artifact
from backend.repositories.artifact_repo import ArtifactRepository

logger = structlog.get_logger(__name__)


class ArtifactService:
    def __init__(self, artifact_repo: ArtifactRepository) -> None:
        self._artifacts = artifact_repo

    async def create(
        self,
        message_id: str,
        session_id: str,
        artifact_type: str,
        content: str,
        title: str | None = None,
    ) -> Artifact:
        sanitized = validate_artifact(content, artifact_type)
        artifact = await self._artifacts.create(
            message_id=message_id,
            session_id=session_id,
            type=artifact_type,
            content=sanitized,
            title=title,
            version=1,
        )
        logger.info("artifact_created", artifact_id=artifact.id, type=artifact_type)
        return artifact

    async def get(self, artifact_id: str) -> Artifact:
        artifact = await self._artifacts.get(artifact_id)
        if artifact is None:
            raise ValueError(f"Artifact not found: {artifact_id}")
        return artifact

    async def update(
        self,
        artifact_id: str,
        content: str,
        title: str | None = None,
    ) -> Artifact:
        artifact = await self._artifacts.get(artifact_id)
        if artifact is None:
            raise ValueError(f"Artifact not found: {artifact_id}")

        sanitized = validate_artifact(content, artifact.type)
        updated = await self._artifacts.update_content(artifact_id, sanitized, title)
        logger.info("artifact_updated", artifact_id=artifact_id, version=updated.version)
        return updated
