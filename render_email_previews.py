"""
Render every email template to a PNG screenshot via Playwright.
Light-mode + dark-mode variants for each template. Saves to previews/.

Uses the same ctx factories as verify_email_modernisation.py.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'calsite.settings')
django.setup()

import re
from pathlib import Path
from playwright.sync_api import sync_playwright

from verify_email_modernisation import (
    EmailService, EMAIL_TEMPLATES, base_ctx
)

PREVIEW_DIR = Path('previews').resolve()
PREVIEW_DIR.mkdir(exist_ok=True)


def render_one(tpl_path, ctx, dark=False):
    """Render one email template. Returns HTML string."""
    from django.template.loader import render_to_string
    return render_to_string(tpl_path, ctx)


def html_to_png(html, png_path, dark=False):
    """Save HTML rendered at 600px to PNG via Playwright."""
    bg = '#F8FAFC' if not dark else '#0F172A'
    full = f"""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=600">
<style>html,body{{margin:0;padding:0;background:{bg};font-family:'Inter',Arial,sans-serif;}}</style>
</head><body>{html}</body></html>"""
    tmp = png_path.with_suffix('.html').resolve()
    tmp.write_text(full, encoding='utf-8')
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width': 600, 'height': 1200})
        if dark:
            page.emulate_media(color_scheme='dark')
        page.goto(tmp.as_uri(), wait_until='load')
        page.wait_for_timeout(800)
        page.screenshot(path=str(png_path.resolve()), full_page=True)
        browser.close()
    tmp.unlink()


def safe_name(tpl_path):
    return re.sub(r'[/\\]', '_', tpl_path)


def main():
    failures = []
    rendered = 0
    for i, (tpl_path, ctx_factory) in enumerate(EMAIL_TEMPLATES, 1):
        name = safe_name(tpl_path).replace('email_', '').replace('.html', '')
        for mode in ('light', 'dark'):
            try:
                ctx = ctx_factory()
                html = render_one(tpl_path, ctx, dark=(mode == 'dark'))
                png_path = PREVIEW_DIR / f'{i:02d}_{name}_{mode}.png'
                html_to_png(html, png_path, dark=(mode == 'dark'))
                rendered += 1
            except Exception as exc:
                failures.append(f'  X {tpl_path} ({mode}): {exc}')
        print(f'  {i:02d}/{len(EMAIL_TEMPLATES)}  {tpl_path}')

    print(f'\n{rendered} previews rendered.')
    if failures:
        print('\nFailures:')
        for f in failures:
            print(f)


main()
