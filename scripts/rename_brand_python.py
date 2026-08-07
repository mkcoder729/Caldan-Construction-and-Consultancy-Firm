"""
One-off brand rename for Python files (user-facing strings only).

Replaces 'Caldan Construction' with 'Caldan Construction and Consultancy Firm'
inside string literals. Skips:
  - module-level docstrings (triple-quoted at top of file)
  - any line that looks like a comment (starts with optional whitespace + '#')
  - any line that is *only* a triple-quoted string (we leave module docstrings)

We do touch:
  - regular string literals used in subject=..., page_title=..., from_addr=..., etc.

Run:  python scripts/rename_brand_python.py
"""
import re
import tokenize
import io
from pathlib import Path

OLD = "Caldan Construction"
NEW = "Caldan Construction and Consultancy Firm"

ROOT = Path(__file__).resolve().parent.parent


def transform_text(text: str) -> tuple[str, int]:
    """Return (new_text, replacement_count)."""
    count = 0
    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(text).readline))
    except tokenize.TokenizeError:
        return text, 0

    # Walk tokens, only modify STRING tokens that are not docstrings, and are not
    # inside comments (tokenize already filters comments).
    out = []
    last_row = 1
    last_col = 0
    for tok in tokens:
        if tok.type == tokenize.STRING:
            s = tok.string
            # Skip triple-quoted at module level (docstring). tokenize marks the
            # first STRING after the file start as `INDENT` boundary; easier: skip
            # any string whose value starts and ends with triple quotes AND the
            # whole file's first non-blank line is this token.
            # Simpler: never touch triple-quoted strings.
            if s.startswith('"""') or s.startswith("'''"):
                out.append(tok)
                continue
            if OLD in s:
                count += s.count(OLD)
                s = s.replace(OLD, NEW)
                # Preserve prefix (r, b, u, f, rb, etc.) and quotes
                m = re.match(r'^([a-zA-Z]*)(["\'])(.*)\2$', s, re.DOTALL)
                if m:
                    prefix, quote, body = m.group(1), m.group(2), m.group(3)
                    new_tok = tokenize.TokenInfo(
                        type=tok.type,
                        string=f"{prefix}{quote}{body}{quote}",
                        start=tok.start,
                        end=tok.end,
                        line=tok.line,
                    )
                    out.append(new_tok)
                    continue
        out.append(tok)

    return tokenize.untokenize(out), count


def main() -> int:
    total_files = 0
    total_changes = 0
    for py in ROOT.rglob("*.py"):
        # Skip this very script and the venv
        if ".venv" in py.parts or "site-packages" in py.parts:
            continue
        if py.resolve() == Path(__file__).resolve():
            continue
        try:
            text = py.read_text(encoding="utf-8")
        except Exception:
            continue
        new_text, changes = transform_text(text)
        if changes:
            py.write_text(new_text, encoding="utf-8")
            total_files += 1
            total_changes += changes
            print(f"  {changes:>3}  {py.relative_to(ROOT)}")
    print()
    print(f"Done. {total_changes} replacements across {total_files} files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())