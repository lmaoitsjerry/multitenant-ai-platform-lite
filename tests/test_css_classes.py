"""Test 6: Helpdesk Loading Dots Visible"""
import os


def test_bg_theme_muted_exists_in_css():
    """bg-theme-muted CSS class must exist for helpdesk loading dots."""
    filepath = os.path.join("frontend", "tenant-dashboard", "src", "index.css")
    with open(filepath, "r", encoding="utf-8") as f:
        css = f.read()

    assert ".bg-theme-muted" in css, \
        "bg-theme-muted class missing from index.css — loading dots will be invisible"

    assert "var(--color-text-muted)" in css, \
        "bg-theme-muted should use var(--color-text-muted) for the background color"


def test_bg_theme_muted_is_proper_css_rule():
    """The CSS rule should be syntactically complete."""
    filepath = os.path.join("frontend", "tenant-dashboard", "src", "index.css")
    with open(filepath, "r", encoding="utf-8") as f:
        css = f.read()

    # Should contain the full rule
    assert ".bg-theme-muted { background-color: var(--color-text-muted); }" in css or \
           ".bg-theme-muted {background-color: var(--color-text-muted);}" in css or \
           ".bg-theme-muted {\n  background-color: var(--color-text-muted);\n}" in css, \
        "bg-theme-muted should be a complete CSS rule with background-color"
