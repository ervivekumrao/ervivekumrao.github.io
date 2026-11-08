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


import re


def _parse_inline_md(text: str) -> str:
    text = esc(text)
    text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
    text = re.sub(r'(\*\*|__)(.*?)\1', r'<strong>\2</strong>', text)
    text = re.sub(r'(\*|_)(.*?)\1', r'<em>\2</em>', text)
    def _link_repl(m):
        label, url = m.group(1), m.group(2)
        target = " target='_blank' rel='noopener noreferrer'" if url.startswith("http") else ""
        return f"<a href='{url}'{target}>{label}</a>"
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', _link_repl, text)
    return text


def md_to_html(text: str) -> str:
    """Converts Markdown text into formatted HTML."""
    if not text:
        return ""

    text = text.strip()
    if text.startswith("<"):
        return text

    if _md:
        try:
            return _md.markdown(text, extensions=["extra"])
        except Exception:
            pass

    lines = text.splitlines()
    html_blocks = []
    in_code_block = False
    code_lines = []
    in_list = False
    list_items = []

    def flush_list():
        nonlocal in_list, list_items
        if in_list and list_items:
            html_blocks.append(f"<ul>{''.join(list_items)}</ul>")
            list_items = []
            in_list = False

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("```"):
            if in_code_block:
                code_content = esc("\n".join(code_lines))
                html_blocks.append(f"<pre><code>{code_content}</code></pre>")
                code_lines = []
                in_code_block = False
            else:
                flush_list()
                in_code_block = True
                code_lines = []
            continue

        if in_code_block:
            code_lines.append(line)
            continue

        if not stripped:
            flush_list()
            continue

        if stripped in ("---", "***", "___"):
            flush_list()
            html_blocks.append("<hr>")
            continue

        if stripped.startswith("# "):
            flush_list()
            html_blocks.append(f"<h1>{_parse_inline_md(stripped[2:])}</h1>")
            continue
        if stripped.startswith("## "):
            flush_list()
            html_blocks.append(f"<h2>{_parse_inline_md(stripped[3:])}</h2>")
            continue
        if stripped.startswith("### "):
            flush_list()
            html_blocks.append(f"<h3>{_parse_inline_md(stripped[4:])}</h3>")
            continue
        if stripped.startswith("#### "):
            flush_list()
            html_blocks.append(f"<h4>{_parse_inline_md(stripped[5:])}</h4>")
            continue

        if stripped.startswith("> "):
            flush_list()
            html_blocks.append(f"<blockquote>{_parse_inline_md(stripped[2:])}</blockquote>")
            continue

        if stripped.startswith("- ") or stripped.startswith("* ") or stripped.startswith("+ "):
            in_list = True
            list_items.append(f"<li>{_parse_inline_md(stripped[2:])}</li>")
            continue

        flush_list()
        html_blocks.append(f"<p>{_parse_inline_md(stripped)}</p>")

    flush_list()
    if in_code_block and code_lines:
        code_content = esc("\n".join(code_lines))
        html_blocks.append(f"<pre><code>{code_content}</code></pre>")

    return "\n".join(html_blocks)


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


