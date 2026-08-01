"""
skills/artifact_skill.py — Artifact generation skill.

No retrieval — uses conversation context only.
Detects whether to generate Markdown or HTML based on the user request.
"""

import structlog

from backend.artifacts.validator import validate_artifact
from backend.context.context_builder import ContextBuilder
from backend.llm_service.llm_service import LLMService
from backend.prompts.artifact_prompts import (
    ARTIFACT_SYSTEM_PROMPT,
    build_artifact_prompt,
    detect_artifact_type,
)
from backend.skills.base import Skill, SkillOutput

logger = structlog.get_logger(__name__)


def _detect_requested_type(query: str) -> str:
    """Detect whether the user wants HTML or Markdown artifact."""
    q = query.lower()
    html_signals = [
        "html", "css", "webpage", "web page", "ui", "component",
        "dashboard", "landing page", "interface", "button", "card",
    ]
    if any(s in q for s in html_signals):
        return "html"
    return "markdown"


class ArtifactSkill(Skill):
    """Generates typed document artifacts (Markdown or HTML/CSS)."""

    name = "artifact"

    def __init__(self, llm_service: LLMService) -> None:
        self._llm = llm_service
        self._context_builder = ContextBuilder(llm_service)

    async def run(self, user_query: str, history: list[dict]) -> SkillOutput:
        logger.info("artifact_skill_run", query_len=len(user_query))

        # 1. Determine artifact type from request
        requested_type = _detect_requested_type(user_query)

        # 2. Build conversation context (no retrieval)
        context_summary = self._build_context_summary(history)
        user_prompt = build_artifact_prompt(
            request=user_query,
            context=context_summary,
            artifact_type=requested_type,
        )

        context = await self._context_builder.build(
            history=[],  # Don't include history in messages — it's in the prompt
            source_attribution=None,
            user_query=user_prompt,
            system_prompt=ARTIFACT_SYSTEM_PROMPT,
        )

        # 3. Generate artifact
        raw_content = await self._llm.generate(
            messages=context.messages,
            system_prompt=ARTIFACT_SYSTEM_PROMPT,
            max_tokens=4096,
        )

        # 4. Detect final type and sanitize
        actual_type = detect_artifact_type(raw_content)
        sanitized_content = validate_artifact(raw_content, actual_type)

        title = self._generate_title(user_query, actual_type)
        logger.info("artifact_skill_complete", type=actual_type, content_len=len(sanitized_content))

        return SkillOutput(
            content=f"I've generated a {actual_type} artifact for you.",
            sources=None,
            artifact_content=sanitized_content,
            artifact_type=actual_type,
            artifact_title=title,
        )

    def _build_context_summary(self, history: list[dict]) -> str:
        """Summarise recent history for the artifact prompt."""
        if not history:
            return "(No prior conversation context)"
        recent = history[-4:]  # Last 4 turns
        lines = []
        for turn in recent:
            role = turn.get("role", "").upper()
            content = turn.get("content", "")[:400]
            lines.append(f"{role}: {content}")
        return "\n".join(lines)

    def _generate_title(self, query: str, artifact_type: str) -> str:
        """Generate a short title for the artifact."""
        words = query.strip().split()[:6]
        base = " ".join(words)
        return f"{artifact_type.title()}: {base}"
