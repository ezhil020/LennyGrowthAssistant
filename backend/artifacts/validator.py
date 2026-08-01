"""
artifacts/validator.py — Markdown and HTML artifact validation and sanitization.

Markdown: strips unsafe inline HTML via bleach.
HTML: validates structure, strips dangerous elements (script srcs, event handlers)
     while preserving self-contained inline scripts for interactive artifacts.
"""

import re

import structlog

logger = structlog.get_logger(__name__)

# Allowed HTML tags for markdown rendering (bleach)
MARKDOWN_ALLOWED_TAGS = [
    "p", "br", "strong", "em", "b", "i", "u", "s",
    "h1", "h2", "h3", "h4", "h5", "h6",
    "ul", "ol", "li", "blockquote", "pre", "code",
    "table", "thead", "tbody", "tr", "th", "td",
    "a", "img", "hr", "div", "span",
]

MARKDOWN_ALLOWED_ATTRS = {
    "a": ["href", "title"],
    "img": ["src", "alt", "title", "width", "height"],
    "code": ["class"],
    "span": ["class"],
    "div": ["class"],
}


class ArtifactValidationError(Exception):
    """Raised when an artifact fails validation."""
    pass


def validate_markdown(content: str) -> str:
    """Sanitize markdown content by stripping unsafe inline HTML.

    Returns:
        Sanitized markdown string.
    """
    try:
        import bleach
        # Only sanitize if there's actual HTML in the markdown
        if "<" in content:
            content = bleach.clean(
                content,
                tags=MARKDOWN_ALLOWED_TAGS,
                attributes=MARKDOWN_ALLOWED_ATTRS,
                strip=True,
            )
    except ImportError:
        logger.warning("bleach_not_installed", message="Skipping markdown sanitization")

    if not content.strip():
        raise ArtifactValidationError("Markdown artifact content is empty after sanitization.")

    return content


def validate_html(content: str) -> str:
    """Validate and sanitize HTML artifact content.

    Strips:
      - External script src attributes (only inline scripts allowed)
      - External stylesheet links
      - On* event handlers that load external resources
      - Meta refresh redirects

    Preserves:
      - Inline <script> blocks (required for interactive artifacts)
      - Inline <style> blocks
      - All structural HTML

    Returns:
        Sanitized HTML string.
    """
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(content, "lxml")

        # Remove scripts with external src (allow inline scripts)
        for tag in soup.find_all("script", src=True):
            logger.info("artifact_sanitize_external_script", src=tag.get("src"))
            tag.decompose()

        # Remove external stylesheet links
        for tag in soup.find_all("link", rel="stylesheet"):
            logger.info("artifact_sanitize_external_css", href=tag.get("href"))
            tag.decompose()

        # Remove meta refresh (prevents redirects)
        for tag in soup.find_all("meta", attrs={"http-equiv": re.compile("refresh", re.I)}):
            tag.decompose()

        # Strip dangerous on* attributes that load external resources
        for tag in soup.find_all(True):
            dangerous_attrs = [
                attr for attr in list(tag.attrs)
                if attr.lower().startswith("on") and (
                    "fetch(" in str(tag.attrs[attr]).lower()
                    or "xmlhttprequest" in str(tag.attrs[attr]).lower()
                    or "src=" in str(tag.attrs[attr]).lower()
                )
            ]
            for attr in dangerous_attrs:
                del tag.attrs[attr]

        sanitized = str(soup)

    except ImportError:
        logger.warning("beautifulsoup4_not_installed", message="Skipping HTML sanitization")
        sanitized = content

    if not sanitized.strip():
        raise ArtifactValidationError("HTML artifact content is empty after sanitization.")

    return sanitized


def validate_artifact(content: str, artifact_type: str) -> str:
    """Validate and sanitize an artifact based on its type.

    Args:
        content: Raw generated artifact content.
        artifact_type: "markdown" or "html"

    Returns:
        Sanitized content.

    Raises:
        ArtifactValidationError: If the artifact is empty or invalid.
    """
    if not content or not content.strip():
        raise ArtifactValidationError(f"Empty {artifact_type} artifact received.")

    if artifact_type == "html":
        return validate_html(content)
    elif artifact_type == "markdown":
        return validate_markdown(content)
    else:
        raise ArtifactValidationError(f"Unknown artifact type: '{artifact_type}'")
