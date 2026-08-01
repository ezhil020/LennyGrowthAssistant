"""
context/summarizer.py — Summarises older conversation turns when context window fills up.

Called by ContextBuilder when message history exceeds CONTEXT_WINDOW_THRESHOLD.
The summary is injected as a synthetic system message at the start of the context.
"""

import structlog

from backend.llm_service.llm_service import LLMService
from backend.prompts.summarization_prompts import (
    SUMMARIZATION_SYSTEM_PROMPT,
    build_summarization_prompt,
)

logger = structlog.get_logger(__name__)


class ConversationSummarizer:
    def __init__(self, llm_service: LLMService) -> None:
        self._llm = llm_service

    async def summarise(self, turns: list[dict]) -> str:
        """Generate a compact summary of the given conversation turns.

        Args:
            turns: List of {"role": str, "content": str} message dicts.

        Returns:
            A plain-text summary string.
        """
        if not turns:
            return ""

        prompt = build_summarization_prompt(turns)
        summary = await self._llm.generate(
            messages=[{"role": "user", "content": prompt}],
            system_prompt=SUMMARIZATION_SYSTEM_PROMPT,
            max_tokens=512,
        )
        logger.info(
            "conversation_summarised",
            turns_condensed=len(turns),
            summary_len=len(summary),
        )
        return summary.strip()
