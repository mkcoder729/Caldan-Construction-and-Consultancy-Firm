"""
Fix Django email templates that have {% comment %} before {% extends %}.
Django requires extends to be the first tag.
"""
import os
import re

EMAIL_DIR = 'templates/email'
# Match: optional leading whitespace + {% comment %}...{% endcomment %}
# then optional whitespace/newlines + {% extends "..." %}
# Move extends to come before the comment.
PATTERN = re.compile(
    r'^([ \t]*\{[%] comment [%]\}[\s\S]*?\{[%] endcomment [%]\})\s*\n\s*'
    r'([ \t]*\{[%] extends [^}]+[%]\})',
    re.MULTILINE
)


def repl(m):
    return m.group(2) + '\n' + m.group(1) + '\n'


fixed = 0
for fn in sorted(os.listdir(EMAIL_DIR)):
    if not fn.endswith('.html') or fn.startswith('_'):
        continue
    path = os.path.join(EMAIL_DIR, fn)
    with open(path, 'r', encoding='utf-8') as f:
        text = f.read()
    new_text, count = PATTERN.subn(repl, text, count=1)
    if count:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(new_text)
        print(f'fixed: {fn}')
        fixed += 1
print(f'Total fixed: {fixed}')