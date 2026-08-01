import pytest
from backend.router.intent_router import _deterministic_classify
from backend.artifacts.validator import validate_markdown, validate_html, ArtifactValidationError

def test_deterministic_router():
    assert _deterministic_classify("Write a Ship30 post about growth") == "ship30"
    assert _deterministic_classify("Convert that to an essay") == "ship30"
    assert _deterministic_classify("now make that a post") == "ship30"
    
    assert _deterministic_classify("Generate an HTML dashboard") == "artifact"
    assert _deterministic_classify("Create a UI for these metrics") == "artifact"
    assert _deterministic_classify("Make an html component") == "artifact"
    
    assert _deterministic_classify("What did Lenny say about retention?") is None
    assert _deterministic_classify("Hello, how are you?") is None

def test_markdown_sanitization():
    unsafe = "# Hello\n<script>alert(1)</script>\n<p>Safe HTML</p>"
    safe = validate_markdown(unsafe)
    assert "<script>" not in safe
    assert "<p>Safe HTML</p>" in safe
    assert "alert(1)" not in safe

def test_html_sanitization():
    unsafe = """
    <html>
      <head>
        <script src="https://evil.com/xss.js"></script>
        <link rel="stylesheet" href="https://evil.com/style.css">
      </head>
      <body onload="fetch('https://evil.com')">
        <h1>Dashboard</h1>
        <script>console.log('inline is allowed')</script>
      </body>
    </html>
    """
    safe = validate_html(unsafe)
    assert "evil.com/xss.js" not in safe
    assert "evil.com/style.css" not in safe
    assert "onload" not in safe
    assert "<h1>Dashboard</h1>" in safe
    assert "inline is allowed" in safe

def test_empty_artifact_validation():
    with pytest.raises(ArtifactValidationError):
        validate_markdown("   ")
    with pytest.raises(ArtifactValidationError):
        validate_html("")
