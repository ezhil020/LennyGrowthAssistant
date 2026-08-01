"""
skills/registry.py — Centralized Skill Registry.

Skills self-register at import time. Router calls SkillRegistry.resolve(name).
Adding a new skill: create the module + call register() — zero router changes.
"""

import structlog

from backend.skills.base import Skill

logger = structlog.get_logger(__name__)


class SkillRegistry:
    _skills: dict[str, Skill] = {}

    @classmethod
    def register(cls, skill: Skill) -> None:
        cls._skills[skill.name] = skill
        logger.info("skill_registered", skill=skill.name)

    @classmethod
    def resolve(cls, name: str) -> Skill:
        skill = cls._skills.get(name)
        if skill is None:
            available = list(cls._skills.keys())
            raise ValueError(
                f"Unknown skill: '{name}'. Available skills: {available}"
            )
        return skill

    @classmethod
    def all_names(cls) -> list[str]:
        return list(cls._skills.keys())


def build_registry(llm_service, retrieval_service) -> SkillRegistry:
    """Construct and register all skills with their dependencies.

    Called once per request (skills are not singletons due to per-request DI).
    """
    from backend.skills.qa_skill import QASkill
    from backend.skills.ship30_skill import Ship30Skill
    from backend.skills.artifact_skill import ArtifactSkill

    registry = SkillRegistry()
    # Clear and re-register (stateless per request)
    SkillRegistry._skills = {}

    SkillRegistry.register(QASkill(llm_service=llm_service, retrieval_service=retrieval_service))
    SkillRegistry.register(Ship30Skill(llm_service=llm_service, retrieval_service=retrieval_service))
    SkillRegistry.register(ArtifactSkill(llm_service=llm_service, retrieval_service=retrieval_service))

    return registry
