"""Auto-backtick reserved words used as column names."""
import re

# Words that MySQL 8 reserves and that are used as column names in this project
reserved = ['type', 'status', 'key', 'order', 'group', 'select', 'table', 'index']

files = [
    'sql_section_01_services.txt',
    'sql_section_02_team_members.txt',
    'sql_section_03_projects.txt',
    'sql_section_04_project_service_links.txt',
    'sql_section_05_project_milestones.txt',
    'sql_section_06_clients.txt',
    'sql_section_07_blog_posts.txt',
    'sql_section_08_testimonials.txt',
    'sql_section_09_products_construction.txt',
    'sql_section_10_products_general_store.txt',
]

for fn in files:
    with open(fn, encoding='utf-8') as f:
        content = f.read()
    original = content

    # Strip comment lines for analysis (but we apply changes to original content)
    # We need to backtick only occurrences OUTSIDE of comments and string literals.

    out = []
    i = 0
    n = len(content)
    in_single_quote = False
    in_double_quote = False
    line_start = True
    in_comment = False
    while i < n:
        ch = content[i]
        next_ch = content[i+1] if i+1 < n else ''

        # Handle line comments
        if line_start and ch == '-' and next_ch == '-':
            # Comment until end of line
            end = content.find('\n', i)
            if end < 0:
                end = n
            out.append(content[i:end])
            i = end
            continue
        line_start = (ch == '\n')

        # Handle string literals
        if not in_comment:
            if ch == "'" and not in_double_quote:
                # Find end of single-quoted string (handle '' escape)
                in_single_quote = not in_single_quote
                out.append(ch)
                i += 1
                continue
            if ch == '"' and not in_single_quote:
                in_double_quote = not in_double_quote
                out.append(ch)
                i += 1
                continue

        if in_single_quote or in_double_quote:
            out.append(ch)
            i += 1
            continue

        # Outside any string/comment — check if we hit a reserved word
        matched_word = None
        for word in reserved:
            wlen = len(word)
            if content[i:i+wlen].lower() == word and i + wlen < n:
                after = content[i+wlen]
                before = content[i-1] if i > 0 else ' '
                if not before.isalnum() and before != '_' and before != '`' and not after.isalnum() and after != '_' and after != '`':
                    matched_word = (word, wlen)
                    break

        if matched_word:
            word, wlen = matched_word
            # Only backtick if it's used as an identifier (column/table name)
            # Heuristic: skip if next non-space char is '(' (function call)
            j = i + wlen
            while j < n and content[j] == ' ':
                j += 1
            if j < n and content[j] == '(':
                out.append(content[i:i+wlen])
                i += wlen
                continue
            # Skip 'ON DUPLICATE KEY UPDATE' — 'KEY' is part of syntax
            if word == 'key':
                # Look back for 'DUPLICATE'
                if content[max(0, i-10):i].upper().rfind('DUPLICATE') >= 0:
                    out.append(content[i:i+wlen])
                    i += wlen
                    continue
            # Backtick it
            out.append('`')
            out.append(content[i:i+wlen])
            out.append('`')
            i += wlen
        else:
            out.append(ch)
            i += 1

    new_content = ''.join(out)

    if new_content != original:
        with open(fn, 'w', encoding='utf-8') as f:
            f.write(new_content)
        # Show diff summary
        added_backticks = new_content.count('`') - original.count('`')
        print(f'{fn}: added {added_backticks} backticks')
    else:
        print(f'{fn}: no changes')