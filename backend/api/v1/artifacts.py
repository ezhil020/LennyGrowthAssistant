"""api/v1/artifacts.py — Artifact retrieval and update endpoints."""

from fastapi import APIRouter, Depends

from backend.models.schemas import ArtifactResponse, ArtifactUpdateRequest
from backend.services.artifact_service import ArtifactService
from backend.services.dependencies import get_artifact_service

router = APIRouter(prefix="/artifacts", tags=["artifacts"])


@router.get("/{artifact_id}", response_model=ArtifactResponse)
async def get_artifact(
    artifact_id: str,
    svc: ArtifactService = Depends(get_artifact_service),
):
    artifact = await svc.get(artifact_id)
    return artifact


@router.patch("/{artifact_id}", response_model=ArtifactResponse)
async def update_artifact(
    artifact_id: str,
    body: ArtifactUpdateRequest,
    svc: ArtifactService = Depends(get_artifact_service),
):
    """Revise an artifact — increments version number."""
    updated = await svc.update(artifact_id, body.content, body.title)
    return updated
