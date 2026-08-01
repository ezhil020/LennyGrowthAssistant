"""
prompts/artifact_prompts.py — Artifact generation prompts (Markdown + HTML variants).
"""

ARTIFACT_SYSTEM_PROMPT = """You are the Lenny Growth Assistant generating a document artifact.

Produce ONLY the artifact content — no preamble, no explanation, no ```code fences``` wrapper.

For MARKDOWN artifacts:
  - Use proper Markdown heading hierarchy (# H1, ## H2, etc.)
  - Use tables, bullet lists, bold/italic for structure
  - Make it a professional, standalone document

For HTML artifacts:
  - Produce complete, self-contained HTML with inline <style> tags
  - Use a clean, modern visual design with tasteful colours and spacing
  - Ensure it renders correctly in a browser iframe
  - No external CDN links — embed everything inline
  - Include responsive design where appropriate

Output ONLY the raw artifact content. Start immediately with the content."""


ARTIFACT_MARKDOWN_PREFIX = """Generate a well-structured Markdown document artifact based on \
the following conversation context and request.

REQUEST: {request}

CONVERSATION CONTEXT:
{context}

Produce only the Markdown content — no preamble."""


ARTIFACT_HTML_PREFIX = """Generate a complete, self-contained HTML/CSS artifact based on \
the following conversation context and request.

REQUEST: {request}

CONVERSATION CONTEXT:
{context}

Rules:
- Complete HTML document with <!DOCTYPE html> and <html> tags
- All CSS inline in <style> tags — no external stylesheets
- No external JavaScript libraries — vanilla JS only if needed
- Modern, clean visual design
- Produce ONLY the HTML content. Start with <!DOCTYPE html>."""


def build_artifact_prompt(request: str, context: str, artifact_type: str) -> str:
    """Build the user-turn prompt for artifact generation."""
    if artifact_type == "html":
        return ARTIFACT_HTML_PREFIX.format(request=request, context=context)
    return ARTIFACT_MARKDOWN_PREFIX.format(request=request, context=context)


def detect_artifact_type(content: str) -> str:
    """Detect whether generated content is HTML or Markdown."""
    stripped = content.strip().lower()
    if stripped.startswith("<!doctype html") or stripped.startswith("<html"):
        return "html"
    return "markdown"
