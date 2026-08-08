"""Check for unquoted reserved words in SQL files."""
import re

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
    issues = []
    for word in reserved:
        # Find unquoted instances of this word
        for m in re.finditer(r'(?<![`a-zA-Z0-9_])' + word + r'(?![`a-zA-Z0-9_])', content, flags=re.IGNORECASE):
            offset = m.start()
            # Skip if it's inside a comment line
            line_start = content.rfind('\n', 0, offset) + 1
            line = content[line_start:content.find('\n', offset)]
            if line.lstrip().startswith('--'):
                continue
            # Skip if it's a string literal
            ctx = content[max(0, offset-15):offset+15]
            if "'" in ctx[:15] and "'" not in ctx[15:]:
                # could be inside string, skip
                pass
            issues.append((word, offset, line[:100]))
    if issues:
        print(f'=== {fn}: {len(issues)} potential issues ===')
        for word, off, line in issues[:5]:
            print(f'  {word!r}: {line.strip()}')
