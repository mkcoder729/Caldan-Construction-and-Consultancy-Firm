"""
One-off brand rename for HTML templates.

Replaces 'Caldan Construction' with 'Caldan Construction and Consultancy Firm'
only in user-facing contexts — i.e. NOT inside HTML comments and NOT inside
<script>...</script> blocks where it appears as a JS string (rare).

Skips:
- HTML comments (`<!-- ... -->`)
- Lines that look like a CSS/JS file-header comment block (top of _css_inline/_js_inline)

Run:  python scripts/rename_brand_html.py
"""
import re
from pathlib import Path

OLD = "Caldan Construction"
NEW = "Caldan Construction and Consultancy Firm"

ROOT = Path(__file__).resolve().parent.parent

COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)


def transform(text: str) -> tuple[str, int]:
    """Replace OLD with NEW outside of HTML comments. Returns (new_text, count)."""
    count = 0

    def _repl_in_chunk(chunk: str) -> str:
        nonlocal count
        n = chunk.count(OLD)
        if n:
            count += n
        return chunk.replace(OLD, NEW)

    # Split out comments, replace only the non-comment pieces, then stitch back.
    parts = []
    last = 0
    for m in COMMENT_RE.finditer(text):
        parts.append(_repl_in_chunk(text[last:m.start()]))
        parts.append(m.group(0))  # leave comments untouched
        last = m.end()
    parts.append(_repl_in_chunk(text[last:]))
    return "".join(parts), count


def main() -> int:
    total_files = 0
    total_changes = 0
    for html in ROOT.rglob("*.html"):
        text = html.read_text(encoding="utf-8")
        new_text, changes = transform(text)
        if changes:
            html.write_text(new_text, encoding="utf-8")
            total_files += 1
            total_changes += changes
            print(f"  {changes:>3}  {html.relative_to(ROOT)}")
    print()
    print(f"Done. {total_changes} replacements across {total_files} files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())