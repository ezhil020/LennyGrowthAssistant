"""
router/intent_router.py — Two-pass agentic routing.

Pass 1: Deterministic regex/keyword rules (zero LLM cost, O(1))
Pass 2: LLM classification fallback (only if Pass 1 is inconclusive)

All routing decisions are logged with full context for auditability.
"""

import json
import re
import structlog

from backend.llm_service.llm_service import LLMService
from backend.prompts.router_prompts import ROUTER_SYSTEM_PROMPT, build_router_prompt

logger = structlog.get_logger(__name__)

# ── Deterministic rule patterns ───────────────────────────────────────────────

_SHIP30_PATTERNS = [
    r"\bship\s*30\b",
    r"\bwrite\s+(a\s+)?post\b",
    r"\bmake\s+(that\s+)?a\s+post\b",
    r"\bturn\s+(that\s+)?into\s+(an?\s+)?(article|essay|post)\b",
    r"\bformat\s+(as\s+)?(a\s+)?ship30\b",
    r"\bwrite\s+(an?\s+)?essay\b",
    r"\bconvert\s+(that\s+)?to\s+(an?\s+)?(post|article)\b",
    r"\bnow\s+make\s+(that\s+)?a\b",
]

_ARTIFACT_PATTERNS = [
    r"\bgenerate\s+(an?\s+)?artifact\b",
    r"\bcreate\s+(an?\s+)?(html|css|webpage|web\s+page)\b",
    r"\bbuild\s+(an?\s+)?(component|dashboard|page|ui|interface)\b",
    r"\bwrite\s+(an?\s+)?(html|markdown\s+doc(ument)?)\b",
    r"\bmake\s+(an?\s+)?(html|css|landing\s+page)\b",
    r"\bgenerate\s+(an?\s+)?(html|markdown)\b",
]

_COMPILED_SHIP30 = [re.compile(p, re.IGNORECASE) for p in _SHIP30_PATTERNS]
_COMPILED_ARTIFACT = [re.compile(p, re.IGNORECASE) for p in _ARTIFACT_PATTERNS]


def _deterministic_classify(message: str) -> str | None:
    """Run deterministic pattern matching. Returns skill name or None."""
    for pattern in _COMPILED_SHIP30:
        if pattern.search(message):
            return "ship30"
    for pattern in _COMPILED_ARTIFACT:
        if pattern.search(message):
            return "artifact"
    return None


# ── Routing result dataclass ──────────────────────────────────────────────────

class RoutingResult:
    def __init__(
        self,
        skill: str,
        intent: str,
        confidence: float,
        pass_used: str,
        context_signals: list[str],
    ) -> None:
        self.skill = skill
        self.intent = intent
        self.confidence = confidence
        self.pass_used = pass_used
        self.context_signals = context_signals

    def to_log_dict(self) -> dict:
        return {
            "skill_chosen": self.skill,
            "intent": self.intent,
            "confidence": self.confidence,
            "pass_used": self.pass_used,
            "context_signals": self.context_signals,
        }


# ── Intent Router ─────────────────────────────────────────────────────────────

class IntentRouter:
    """Routes user messages to the correct skill using deterministic rules + LLM fallback."""

    def __init__(self, llm_service: LLMService) -> None:
        self._llm = llm_service

    async def classify(
        self,
        message: str,
        history: list[dict],
        request_id: str = "",
    ) -> RoutingResult:
        """Classify the user message and return a RoutingResult.

        Pass 1: Deterministic rules (always runs first — zero cost).
        Pass 2: LLM classification (only if Pass 1 returns None).

        Explicit overrides in the message always win.
        """

        # Pass 1 — deterministic
        deterministic_skill = _deterministic_classify(message)
        if deterministic_skill:
            result = RoutingResult(
                skill=deterministic_skill,
                intent=f"explicit_{deterministic_skill}_request",
                confidence=1.0,
                pass_used="deterministic",
                context_signals=["explicit_keyword_match"],
            )
            logger.info(
                "routing_decision",
                request_id=request_id,
                **result.to_log_dict(),
            )
            return result

        # Pass 2 — LLM classification
        result = await self._llm_classify(message, history)
        logger.info(
            "routing_decision",
            request_id=request_id,
            **result.to_log_dict(),
        )
        return result

    async def _llm_classify(self, message: str, history: list[dict]) -> RoutingResult:
        """Use the LLM to classify intent from message + context."""
        history_dicts = [{"role": t.get("role"), "content": t.get("content", "")} for t in history]
        prompt = build_router_prompt(message, history_dicts)

        try:
            raw = await self._llm.generate(
                messages=[{"role": "user", "content": prompt}],
                system_prompt=ROUTER_SYSTEM_PROMPT,
                max_tokens=256,
            )
            # Parse JSON response
            # Strip markdown code fences if present
            clean = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            data = json.loads(clean)
            return RoutingResult(
                skill=data.get("skill", "qa"),
                intent=data.get("intent", "unknown"),
                confidence=float(data.get("confidence", 0.7)),
                pass_used="llm",
                context_signals=data.get("context_signals", []),
            )
        except Exception as e:
            logger.warning("router_llm_parse_error", error=str(e), fallback="qa")
            # Safe fallback
            return RoutingResult(
                skill="qa",
                intent="classification_failed_fallback",
                confidence=0.5,
                pass_used="fallback",
                context_signals=[f"parse_error: {str(e)[:50]}"],
            )
