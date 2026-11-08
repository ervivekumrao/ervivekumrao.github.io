"""Utility functions for string formatting, HTML escaping, and markdown processing."""
from __future__ import annotations
import html
import sys

try:
    import markdown as _md
except ImportError:  # optional dependency
    _md = None


def esc(v) -> str:
    """Escapes special characters in text for safe HTML embedding."""
    return html.escape("" if v is None else str(v), quote=True)


def human_size(n: int) -> str:
    """Converts a size in bytes into a human-readable megabyte string."""
    return f"{n / 1_048_576:.1f} MB"


def md_to_html(text: str) -> str:
    """Converts Markdown text into HTML, using markdown library if installed."""
    if _md:
        return _md.markdown(text, extensions=["extra"])
    if text.strip().startswith("<"):
        return text
    return f"<pre>{esc(text)}</pre>"


def get_project_titles(p: dict) -> tuple[str, str]:
    """Resolves the main title and subtitle for a project dict."""
    explicit_sub = p.get("subtitle")
    raw_name = p.get("name", "")

    if " — " in raw_name:
        main_title, name_sub = raw_name.split(" — ", 1)
    elif " – " in raw_name:
        main_title, name_sub = raw_name.split(" – ", 1)
    else:
        main_title, name_sub = raw_name, ""

    subtitle = explicit_sub if explicit_sub is not None else name_sub
    return main_title, subtitle


def get_project_category_badge(p: dict) -> str:
    """Resolves the category display badge for a project dict."""
    if p.get("category_badge"):
        return p["category_badge"]

    pid = p.get("id", "")
    if pid == "agenticinventory":
        return "⚡ Microservices & AI"
    elif pid == "spindb":
        return "🛠️ Developer CLI"
    elif pid == "jitforge":
        return "⚡ JVM JIT Engine"
    elif pid == "tomcatvault":
        return "🔒 Cryptographic Vault"

    ptype = p.get("type", "app")
    if ptype == "app":
        return "📱 Android App"
    elif ptype == "library":
        return "📦 Android SDK"

    return "⚙️ System Tool"


