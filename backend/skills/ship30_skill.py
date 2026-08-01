"""
skills/ship30_skill.py — Ship30for30 content generation skill.

Owns retrieval internally. Generates a ~1,250-word essay in Ship30for30 style,
then produces it as a Markdown artifact.
"""

import structlog

from backend.context.context_builder import ContextBuilder
from backend.llm_service.llm_service import LLMService
from backend.prompts.qa_prompts import build_retrieval_context
from backend.prompts.ship30_prompts import SHIP30_SYSTEM_PROMPT, build_ship30_user_prompt
from backend.retrieval.retrieval_service import RetrievalService
from backend.skills.base import Skill, SkillOutput

logger = structlog.get_logger(__name__)


class Ship30Skill(Skill):
    """Generates a Ship30for30-style essay grounded in Lenny's transcript content."""

    name = "ship30"

    def __init__(
        self,
        llm_service: LLMService,
        retrieval_service: RetrievalService,
    ) -> None:
        self._llm = llm_service
        self._retrieval = retrieval_service
        self._context_builder = ContextBuilder(llm_service)

    async def run(self, user_query: str, history: list[dict]) -> SkillOutput:
        logger.info("ship30_skill_run", query_len=len(user_query))

        # 1. Extract topic — use the query directly (may be "now make that a post"
        #    so resolve against last assistant message if needed)
        topic = self._resolve_topic(user_query, history)

        # 2. Retrieve relevant chunks
        attribution = await self._retrieval.retrieve(topic)

        # 3. Build retrieval context block
        chunk_dicts = [
            {
                "episode_title": c.episode_title,
                "similarity_score": c.similarity_score,
                "chunk_text": c.chunk_text,
            }
            for c in attribution.chunks
        ]
        retrieval_context = build_retrieval_context(chunk_dicts)

        # 4. Build the user prompt
        user_prompt = build_ship30_user_prompt(topic=topic, retrieval_context=retrieval_context)

        # 5. Manage conversation context
        context = await self._context_builder.build(
            history=history,
            source_attribution=None,  # We handle retrieval context in user_prompt directly
            user_query=user_prompt,
            system_prompt=SHIP30_SYSTEM_PROMPT,
        )

        # 6. Generate essay — larger token budget for ~1,250 words
        essay = await self._llm.generate(
            messages=context.messages,
            system_prompt=SHIP30_SYSTEM_PROMPT,
            max_tokens=2000,
        )

        word_count = len(essay.split())
        logger.info("ship30_skill_complete", word_count=word_count)

        # 7. Produce essay inline + as a Markdown artifact
        return SkillOutput(
            content=f"Here's your Ship30for30 essay ({word_count} words):",
            sources=attribution,
            artifact_content=essay,
            artifact_type="markdown",
            artifact_title=f"Ship30: {topic[:60]}",
        )

    def _resolve_topic(self, query: str, history: list[dict]) -> str:
        """Resolve the essay topic from the query, falling back to prior assistant answer."""
        vague_patterns = [
            "make that a post", "write that as", "turn that into",
            "ship30 for that", "now make", "convert that",
        ]
        query_lower = query.lower()
        is_vague = any(p in query_lower for p in vague_patterns)

        if is_vague and history:
            # Resolve "that" against the last assistant message
            for turn in reversed(history):
                if turn.get("role") == "assistant":
                    content = turn.get("content", "")
                    # Use first 200 chars of the prior answer as the topic
                    return content[:200].strip()

        return query
