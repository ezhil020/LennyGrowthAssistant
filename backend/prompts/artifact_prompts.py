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


ARTIFACT_AUTO_PREFIX = """Generate an artifact based on the following context and request.

REQUEST: {request}

CONTEXT (Conversation + Optional Retrieved Transcripts):
{context}

CRITICAL RULES FOR FORMAT DETECTION:
You must determine whether to output a Markdown document or an HTML/CSS webpage based on the user's explicit intent in the REQUEST.
- Use HTML/CSS if the user explicitly asks for: html, css, UI, component, dashboard, webpage, interactive element, or visual layout.
- Use Markdown if the user asks for: markdown, document, checklist, essay, summary, notes, or just general text formatting.
- If ambiguous, default to Markdown.

If outputting Markdown:
- Use proper Markdown headings (# H1, ## H2), tables, and lists.
- Do NOT wrap the entire response in ```markdown code fences.

If outputting HTML:
- Output complete, self-contained HTML starting with <!DOCTYPE html>
- All CSS must be inline in <style> tags. No external stylesheets or CDNs.
- Do NOT wrap the response in ```html code fences.

Produce ONLY the raw artifact content. Start immediately with the content."""


def build_artifact_prompt(request: str, context: str) -> str:
    """Build the user-turn prompt for artifact generation."""
    return ARTIFACT_AUTO_PREFIX.format(request=request, context=context)


def detect_artifact_type(content: str) -> str:
    """Detect whether generated content is HTML or Markdown."""
    stripped = content.strip().lower()
    if stripped.startswith("<!doctype html") or stripped.startswith("<html"):
        return "html"
    return "markdown"
