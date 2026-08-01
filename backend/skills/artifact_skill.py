"""
skills/artifact_skill.py — Artifact generation skill.

Can use Retrieval-Augmented Generation (RAG) when the request requires it,
or fall back to conversation history if the request is vague (e.g., "turn that into").
"""

import structlog

from backend.artifacts.validator import validate_artifact
from backend.context.context_builder import ContextBuilder
from backend.llm_service.llm_service import LLMService
from backend.prompts.qa_prompts import build_retrieval_context
from backend.prompts.artifact_prompts import (
    ARTIFACT_SYSTEM_PROMPT,
    build_artifact_prompt,
    detect_artifact_type,
)
from backend.retrieval.retrieval_service import RetrievalService
from backend.skills.base import Skill, SkillOutput

logger = structlog.get_logger(__name__)


class ArtifactSkill(Skill):
    """Generates typed document artifacts (Markdown or HTML/CSS)."""

    name = "artifact"

    def __init__(
        self,
        llm_service: LLMService,
        retrieval_service: RetrievalService,
    ) -> None:
        self._llm = llm_service
        self._retrieval = retrieval_service
        self._context_builder = ContextBuilder(llm_service)

    def _is_vague(self, query: str) -> bool:
        """Heuristic to determine if the user query is vague and should rely on chat history."""
        vague_patterns = [
            "make that", "write that", "turn that", "turn this",
            "convert that", "convert this", "for that", "for this"
        ]
        q = query.lower()
        return any(p in q for p in vague_patterns)

    async def run(self, user_query: str, history: list[dict]) -> SkillOutput:
        logger.info("artifact_skill_run", query_len=len(user_query))

        # 1. Determine if we need RAG
        attribution = None
        retrieval_context = ""
        if not self._is_vague(user_query):
            attribution = await self._retrieval.retrieve(user_query)
            if attribution and attribution.chunks:
                chunk_dicts = [
                    {
                        "episode_title": c.episode_title,
                        "similarity_score": c.similarity_score,
                        "chunk_text": c.chunk_text,
                    }
                    for c in attribution.chunks
                ]
                retrieval_context = build_retrieval_context(chunk_dicts)

        # 2. Build conversation context
        chat_summary = self._build_context_summary(history)
        
        # Combine chat summary and retrieval context
        combined_context = f"--- CHAT HISTORY ---\n{chat_summary}\n\n"
        if retrieval_context:
            combined_context += f"{retrieval_context}\n"

        user_prompt = build_artifact_prompt(
            request=user_query,
            context=combined_context,
        )

        context = await self._context_builder.build(
            history=[],  # History is already injected into the prompt
            source_attribution=attribution,
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
