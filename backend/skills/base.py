"""
skills/base.py — Skill abstract base class.

Every skill implements this interface. Skills are provider-agnostic —
they call LLMService, never providers directly.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from backend.models.source import SourceAttribution


@dataclass
class SkillOutput:
    """Structured output returned by any skill."""
    content: str                              # Text shown in the chat message
    sources: SourceAttribution | None         # Source attribution (QA + Ship30 only)
    artifact_content: str | None = None       # Raw artifact content (if produced)
    artifact_type: str | None = None          # "markdown" | "html" | None
    artifact_title: str | None = None         # Optional title for the artifact


class Skill(ABC):
    """Common interface for all skills."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique skill identifier (e.g. 'qa', 'ship30', 'artifact')."""
        ...

    @abstractmethod
    async def run(
        self,
        user_query: str,
        history: list[dict],
    ) -> SkillOutput:
        """Execute the skill and return structured output.

        Args:
            user_query: The current user message.
            history: Prior conversation turns as {"role", "content"} dicts.

        Returns:
            SkillOutput with content, optional sources, optional artifact.
        """
        ...
