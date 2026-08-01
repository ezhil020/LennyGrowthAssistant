"""
llm_service/token_counter.py — Model-aware token counting.

Uses tiktoken for approximate counts. Falls back to word-based
estimation for models without a known tokenizer.
"""

import structlog

logger = structlog.get_logger(__name__)

# Approximate tokens per word fallback
_TOKENS_PER_WORD = 1.4


def count_tokens(text: str, model: str = "cl100k_base") -> int:
    """Count tokens in a string for the given model encoding.

    Returns:
        Approximate token count.
    """
    try:
        import tiktoken
        try:
            enc = tiktoken.encoding_for_model(model)
        except KeyError:
            enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
    except Exception:
        # Fallback: word count * average tokens per word
        return int(len(text.split()) * _TOKENS_PER_WORD)


def count_messages_tokens(messages: list[dict], model: str = "cl100k_base") -> int:
    """Count total tokens across a list of chat messages."""
    total = 0
    for msg in messages:
        total += count_tokens(msg.get("content", ""), model)
        total += 4  # per-message overhead (role, separators)
    return total
