"""
skills/chat_skill.py — Generic conversational skill without retrieval.
"""

import structlog

from backend.context.context_builder import ContextBuilder
from backend.llm_service.llm_service import LLMService
from backend.prompts.chat_prompts import CHAT_SYSTEM_PROMPT
from backend.skills.base import Skill, SkillOutput

logger = structlog.get_logger(__name__)


class ChatSkill(Skill):
    """Generic conversation without RAG retrieval."""

    name = "chat"

    def __init__(self, llm_service: LLMService) -> None:
        self._llm = llm_service
        self._context_builder = ContextBuilder(llm_service)

    async def run(self, user_query: str, history: list[dict]) -> SkillOutput:
        logger.info("chat_skill_run", query_len=len(user_query))

        # Build prompt context (no source_attribution)
        context = await self._context_builder.build(
            history=history,
            source_attribution=None,
            user_query=user_query,
            system_prompt=CHAT_SYSTEM_PROMPT,
        )

        # Generate grounded answer
        response = await self._llm.generate(
            messages=context.messages,
            system_prompt=context.system_prompt,
            max_tokens=1024,
        )

        logger.info("chat_skill_complete", response_len=len(response))
        return SkillOutput(content=response, sources=None)
