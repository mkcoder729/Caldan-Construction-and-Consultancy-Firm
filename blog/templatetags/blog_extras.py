"""
Templatetags for blog content rendering.

`render_blog_content` converts the markdown subset used by the blog editor
(## / ### headings, **bold**, *italic*, [text](url), blockquotes, ordered
and unordered lists, paragraphs, inline code, and horizontal rules)
into clean HTML. We hand-roll this rather than depend on a 3rd-party
markdown library so that the production deployment stays slim.
"""

import re
from django import template
from django.utils.safestring import mark_safe

register = template.Library()


# --- Inline patterns ----------------------------------------------------

_INLINE_PATTERNS = [
    # Inline code first so its contents are not reformatted
    (re.compile(r"`([^`]+)`"), r"<code>\1</code>"),
    # Bold (must run before italic so ** is not consumed as two *'s)
    (re.compile(r"\*\*([^*]+)\*\*"), r"<strong>\1</strong>"),
    # Italic — single underscore or asterisk
    (re.compile(r"(?<!\*)\*([^*\n]+)\*(?!\*)"), r"<em>\1</em>"),
    (re.compile(r"(?<!_)_([^_\n]+)_(?!_)"), r"<em>\1</em>"),
    # Links: [text](url)
    (
        re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)"),
        r'<a href="\2" rel="noopener noreferrer">\1</a>',
    ),
]


def _apply_inline(text: str) -> str:
    """Apply inline markdown substitutions, but leave block structures alone."""
    # Escape HTML in the raw text first so users cannot inject script tags.
    text = (
        text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#39;")
    )
    for pattern, replacement in _INLINE_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


# --- Block-level conversion ---------------------------------------------

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
_OL_RE = re.compile(r"^\s*\d+\.\s+(.*)$")
_UL_RE = re.compile(r"^\s*[-*]\s+(.*)$")
_HR_RE = re.compile(r"^\s*([-*_])\s*\1\s*\1[\s\S]*$")


def _slugify_heading(text: str, used: dict) -> str:
    """Lower-case, strip punctuation, ensure unique within the page."""
    base = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    if not base:
        base = "section"
    count = used.get(base, 0)
    used[base] = count + 1
    return base if count == 0 else f"{base}-{count}"


def render_blog_content(value: str) -> str:
    """Convert blog markdown body to safe HTML.

    Supports:
        - `#`, `##`, `###`, `####` headings (h2/h3/h4 emitted; h1 reserved)
        - `**bold**`, `*italic*`, `_italic_`, `` `code` ``, `[text](url)`
        - `- item` and `* item` unordered lists
        - `1. item` ordered lists
        - `> quote` blockquotes
        - `---` horizontal rules
        - Blank-line separated paragraphs
    """
    if not value:
        return ""

    # Normalise line endings.
    text = value.replace("\r\n", "\n").replace("\r", "\n")
    lines = text.split("\n")

    out: list[str] = []
    i = 0
    paragraph: list[str] = []
    list_stack: list[str] = []  # 'ul' or 'ol'
    slug_used: dict[str, int] = {}

    def flush_paragraph() -> None:
        if paragraph:
            joined = " ".join(p.strip() for p in paragraph if p.strip())
            if joined:
                out.append(f"<p>{_apply_inline(joined)}</p>")
            paragraph.clear()

    def close_lists() -> None:
        while list_stack:
            out.append(f"</{list_stack.pop()}>")

    while i < len(lines):
        raw = lines[i]
        line = raw.rstrip()

        # Blank line — paragraph break.
        if not line.strip():
            flush_paragraph()
            close_lists()
            i += 1
            continue

        # Heading.
        m = _HEADING_RE.match(line)
        if m:
            flush_paragraph()
            close_lists()
            level = len(m.group(1))
            # Restrict to h2..h4 visually.
            tag = {1: "h2", 2: "h2", 3: "h3", 4: "h4"}.get(level, "h4")
            heading_text = m.group(2).strip()
            slug = _slugify_heading(heading_text, slug_used)
            out.append(f'<{tag} id="{slug}">{_apply_inline(heading_text)}</{tag}>')
            i += 1
            continue

        # Horizontal rule.
        if _HR_RE.match(line.strip()) and len(line.strip()) >= 3:
            flush_paragraph()
            close_lists()
            out.append("<hr>")
            i += 1
            continue

        # Blockquote (gather contiguous `>` lines).
        if line.lstrip().startswith(">"):
            flush_paragraph()
            close_lists()
            quote_lines = []
            while i < len(lines) and lines[i].lstrip().startswith(">"):
                quote_lines.append(lines[i].lstrip()[1:].lstrip())
                i += 1
            body = " ".join(q for q in quote_lines if q).strip()
            if body:
                out.append(f"<blockquote><p>{_apply_inline(body)}</p></blockquote>")
            continue

        # Unordered list.
        m = _UL_RE.match(line)
        if m:
            flush_paragraph()
            if list_stack and list_stack[-1] != "ul":
                close_lists()
            if not list_stack:
                out.append("<ul>")
                list_stack.append("ul")
            out.append(f"<li>{_apply_inline(m.group(1).strip())}</li>")
            i += 1
            continue

        # Ordered list.
        m = _OL_RE.match(line)
        if m:
            flush_paragraph()
            if list_stack and list_stack[-1] != "ol":
                close_lists()
            if not list_stack:
                out.append("<ol>")
                list_stack.append("ol")
            out.append(f"<li>{_apply_inline(m.group(1).strip())}</li>")
            i += 1
            continue

        # Anything else accumulates into a paragraph.
        if list_stack:
            close_lists()
        paragraph.append(line)
        i += 1

    flush_paragraph()
    close_lists()
    return mark_safe("".join(out))


@register.filter(name="render_blog")
def render_blog(value: str) -> str:
    """Template filter alias: `{{ post.content|render_blog }}`."""
    return render_blog_content(value)
