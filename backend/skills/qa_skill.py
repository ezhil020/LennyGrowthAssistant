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
        logger.info("qa_skill_run", query_len=len(user_query))

        # 1. Retrieve relevant chunks
        attribution = await self._retrieval.retrieve(user_query)

        relevant_chunks = [
            c for c in attribution.chunks if c.similarity_score >= MIN_RELEVANCE_SCORE
        ]
        filtered_attribution = SourceAttribution(
            chunks=relevant_chunks, retrieval_mode=attribution.retrieval_mode
        )

        # 3. Build prompt context
        context = await self._context_builder.build(
            history=history,
            source_attribution=filtered_attribution,
            user_query=user_query,
            system_prompt=QA_SYSTEM_PROMPT,
        )

        # 4. Generate grounded answer
        response = await self._llm.generate(
            messages=context.messages,
            system_prompt=context.system_prompt,
            max_tokens=2048,
        )

        logger.info("qa_skill_complete", response_len=len(response))
        return SkillOutput(content=response, sources=filtered_attribution)
