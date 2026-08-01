"""
prompts/summarization_prompts.py — Conversation summarization prompt.

Used by the ContextBuilder when session history exceeds the context window threshold.
"""

SUMMARIZATION_SYSTEM_PROMPT = """You are a conversation summariser. \
Condense the provided conversation turns into a compact summary \
that preserves all key facts, decisions, and context needed to continue the conversation.

Rules:
- Keep the summary under 300 words
- Preserve specific facts, names, episode titles, and data points mentioned
- Note which skills were used (Q&A answers, Ship30 essays, artifacts generated)
- Write in third person: "The user asked about...", "The assistant explained..."
- Output ONLY the summary text — no preamble, no labels"""


def build_summarization_prompt(turns: list[dict]) -> str:
    """Build the prompt for summarising a list of conversation turns."""
    lines = ["Summarise the following conversation turns:\n"]
    for turn in turns:
        role = turn.get("role", "").upper()
        content = turn.get("content", "")
        lines.append(f"{role}: {content}\n")
    lines.append("\nProvide a concise summary:")
    return "\n".join(lines)
