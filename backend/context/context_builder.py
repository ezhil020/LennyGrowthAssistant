"""
context/context_builder.py — Assembles the final prompt payload for the LLM.

Responsibilities:
  1. Convert DB message history to chat messages list
  2. Check total token budget against provider context limit
  3. If over threshold: summarise oldest turns, replace with summary
  4. Prepend retrieved source chunks (formatted with labels)
  5. Return a PromptContext ready for LLMService.generate()
"""

from dataclasses import dataclass, field

import structlog

from backend.config import settings
from backend.llm_service.token_counter import count_messages_tokens, count_tokens
from backend.models.source import SourceAttribution
from backend.prompts.qa_prompts import build_retrieval_context

logger = structlog.get_logger(__name__)


@dataclass
class PromptContext:
    """Fully assembled prompt context ready for LLMService."""
    messages: list[dict]             # [{"role": str, "content": str}, ...]
    system_prompt: str = ""
    source_attribution: SourceAttribution | None = None


class ContextBuilder:
    """Assembles the prompt context from history + retrieved chunks + current query."""

    def __init__(self, llm_service=None) -> None:
        # llm_service is injected for summarization; can be None if no summarization needed
        self._llm_service = llm_service
        self._max_tokens = settings.active_provider_max_tokens
        self._threshold = settings.context_window_threshold

    async def build(
        self,
        history: list[dict],
        source_attribution: SourceAttribution | None,
        user_query: str,
        system_prompt: str = "",
    ) -> PromptContext:
        """Build the full prompt context.

        Args:
            history: Prior turns as list of {"role", "content"} dicts.
            source_attribution: Retrieved chunks (None for artifact skill).
            user_query: Current user message.
            system_prompt: Skill-specific system prompt.

        Returns:
            PromptContext ready for LLMService.
        """
        # 1. Build retrieval context block
        retrieval_block = ""
        if source_attribution and source_attribution.chunks:
            chunk_dicts = [
                {
                    "episode_title": c.episode_title,
                    "similarity_score": c.similarity_score,
                    "chunk_text": c.chunk_text,
                }
                for c in source_attribution.chunks
            ]
            retrieval_block = build_retrieval_context(chunk_dicts)

        # 2. Append retrieval block to system prompt
        final_system_prompt = system_prompt
        if retrieval_block:
            final_system_prompt = f"{system_prompt}\n\n{retrieval_block}"
            
        user_content = user_query

        # 3. Manage history within token budget
        managed_history = await self._manage_context(history, user_content, final_system_prompt)

        # 4. Append current user message
        messages = managed_history + [{"role": "user", "content": user_content}]

        return PromptContext(
            messages=messages,
            system_prompt=final_system_prompt,
            source_attribution=source_attribution,
        )

    async def _manage_context(
        self,
        history: list[dict],
        upcoming_content: str,
        system_prompt: str,
    ) -> list[dict]:
        """Trim or summarise history to stay within the context window."""
        if not history:
            return []

        budget = int(self._max_tokens * self._threshold)
        system_tokens = count_tokens(system_prompt)
        upcoming_tokens = count_tokens(upcoming_content)
        available = budget - system_tokens - upcoming_tokens

        # Check if history fits within budget
        history_tokens = count_messages_tokens(history)
        if history_tokens <= available:
            return history

        # Need to trim — summarise oldest turns first
        logger.info(
            "context_overflow",
            history_tokens=history_tokens,
            available=available,
            action="summarising",
        )

        # Split: summarise older half, keep recent half verbatim
        split = len(history) // 2
        old_turns = history[:split]
        recent_turns = history[split:]

        if self._llm_service:
            from backend.context.summarizer import ConversationSummarizer
            summarizer = ConversationSummarizer(self._llm_service)
            summary_text = await summarizer.summarise(old_turns)
            summary_message = {
                "role": "user",
                "content": f"[Earlier conversation summary: {summary_text}]",
            }
            return [summary_message] + recent_turns
        else:
            # No LLM for summarization — just keep recent turns
            return recent_turns
