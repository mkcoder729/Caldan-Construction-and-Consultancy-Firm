"""
Diagnose the typing bug: get a logged-in session and check what could prevent typing on a form page.
"""
import os, django, re

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'calsite.settings')
django.setup()

from django.test import Client
from django.conf import settings
from django.contrib.auth import get_user_model

settings.ALLOWED_HOSTS = ['*']

User = get_user_model()
admin = User.objects.filter(is_superuser=True).first() or User.objects.filter(is_staff=True).first()
print('Using admin:', admin)

c = Client()

# Manual session injection (force_login doesn't work fully with axes middleware)
from django.contrib.auth import SESSION_KEY, BACKEND_SESSION_KEY, HASH_SESSION_KEY

session = c.session
session[SESSION_KEY] = admin.id
session[BACKEND_SESSION_KEY] = 'django.contrib.auth.backends.ModelBackend'
session[HASH_SESSION_KEY] = admin.get_session_auth_hash()
session.save()

# Login by visiting login URL to ensure cookies work
r = c.get('/dashboard/', follow=True)
print('GET /dashboard/ →', r.status_code)

# Now hit /clients/create/
r = c.get('/clients/create/')
print('GET /clients/create/ →', r.status_code)
content = r.content.decode('utf-8', errors='replace')

# Find all <input> tags and check for disabled/readonly/tabindex
inputs = re.findall(r'<input[^>]*>', content)
print(f'\nTotal <input> tags: {len(inputs)}')

problematic = []
for inp in inputs[:50]:
    issues = []
    if 'disabled' in inp: issues.append('disabled')
    if 'readonly' in inp: issues.append('readonly')
    if 'tabindex' in inp and 'tabindex="0"' not in inp and 'tabindex="-1"' not in inp: issues.append('suspicious-tabindex')
    if issues:
        problematic.append((inp[:120], issues))

print(f'\nProblematic inputs: {len(problematic)}')
for inp, issues in problematic[:10]:
    print(f'  [{",".join(issues)}] {inp}')

# Search for any overlay/loader on the page
overlay_classes = re.findall(r'class="([^"]*(?:overlay|loader|loading|modal)[^"]*)"', content, re.IGNORECASE)
print(f'\nOverlay/loader classes: {len(overlay_classes)}')
for cls in overlay_classes[:20]:
    print(f'  {cls}')

# Search for any inline style with pointer-events: none
pe = re.findall(r'pointer-events\s*:\s*none', content, re.IGNORECASE)
print(f'\nInline pointer-events:none: {len(pe)}')

# Search for any tabindex on inputs
tabindex_count = sum(1 for inp in inputs if 'tabindex' in inp)
print(f'Inputs with tabindex: {tabindex_count}')

# Save HTML for visual inspection
with open(r'C:\Users\User\Desktop\caldan_site\_probe_clients_create.html', 'w', encoding='utf-8') as f:
    f.write(content)
print(f'\nSaved to _probe_clients_create.html ({len(content)} bytes)')
