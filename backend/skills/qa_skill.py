"""
skills/qa_skill.py — Q&A skill: retrieval → context → grounded answer.

This skill owns its own retrieval internally.
Produces a grounded answer with full SourceAttribution.
"""

import structlog

from backend.context.context_builder import ContextBuilder
from backend.llm_service.llm_service import LLMService
from backend.models.source import SourceAttribution
from backend.prompts.qa_prompts import QA_SYSTEM_PROMPT
from backend.retrieval.retrieval_service import RetrievalService
from backend.skills.base import Skill, SkillOutput

logger = structlog.get_logger(__name__)

NO_CONTENT_RESPONSE = (
    "I don't have information about that in Lenny's transcripts. "
    "Could you try rephrasing or asking about a topic Lenny has covered in the podcast?"
)
MIN_RELEVANCE_SCORE = 0.15  # Chunks below this are considered irrelevant


class QASkill(Skill):
    """Retrieval-augmented Q&A grounded in Lenny's Podcast transcripts."""

    name = "qa"

    def __init__(
        self,
        llm_service: LLMService,
        retrieval_service: RetrievalService,
    ) -> None:
        self._llm = llm_service
        self._retrieval = retrieval_service
        self._context_builder = ContextBuilder(llm_service)

    async def run(self, user_query: str, history: list[dict]) -> SkillOutput:
        logger.info(
            "qa_skill_start",
            module="qa_skill",
            query=user_query,
            query_len=len(user_query),
            history_turns=len(history),
        )

        # 1. Retrieve relevant chunks
        attribution = await self._retrieval.retrieve(user_query)

        relevant_chunks = [
            c for c in attribution.chunks if c.similarity_score >= MIN_RELEVANCE_SCORE
        ]
        filtered_attribution = SourceAttribution(
            chunks=relevant_chunks, retrieval_mode=attribution.retrieval_mode
        )

        logger.info(
            "qa_skill_retrieval_filtered",
            module="qa_skill",
            query=user_query,
            total_chunks=len(attribution.chunks),
            relevant_chunks=len(relevant_chunks),
            min_relevance_score=MIN_RELEVANCE_SCORE,
            has_context=len(relevant_chunks) > 0,
            relevant_episodes=[
                f"{c.episode_title[:50]} ({c.similarity_score:.2f})"
                for c in relevant_chunks[:5]
            ],
        )

        if not relevant_chunks:
            logger.warning(
                "qa_skill_no_context",
                module="qa_skill",
                query=user_query,
                action="returning_no_content_response",
            )

        # 3. Build prompt context
        context = await self._context_builder.build(
            history=history,
            source_attribution=filtered_attribution,
            user_query=user_query,
            system_prompt=QA_SYSTEM_PROMPT,
        )

        logger.info(
            "qa_skill_prompt_ready",
            module="qa_skill",
            num_messages=len(context.messages),
            system_prompt_len=len(context.system_prompt),
            last_user_message_preview=(
                context.messages[-1]["content"][:200].replace("\n", " ")
                if context.messages else ""
            ),
        )

        # 4. Generate grounded answer
        response = await self._llm.generate(
            messages=context.messages,
            system_prompt=context.system_prompt,
            max_tokens=2048,
        )

        logger.info(
            "qa_skill_complete",
            module="qa_skill",
            response_len=len(response),
            response_preview=response[:200].replace("\n", " "),
        )
        return SkillOutput(content=response, sources=filtered_attribution)
