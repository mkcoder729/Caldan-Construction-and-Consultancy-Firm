"""
Verify: every PDF template renders without error via Django's template loader
(parse-time AND render-time), and the standalone reports include a Cloudinary
logo URL in the source.

Render-time checks catch the class of bug where a template uses a custom filter
without `{% load pdf_filters %}` — Django only raises TemplateSyntaxError at
the point the filter is invoked, not at parse time. _base_report.html loads
pdf_filters defensively so future PDFs are covered too.
"""
import os
import sys
import re
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'calsite.settings')
django.setup()

PDF_TEMPLATES = [
    # templates that extend _base_report.html
    'pdf/_base_report.html',
    'pdf/blog_report.html',
    'pdf/clients_report.html',
    'pdf/expenses_report.html',
    'pdf/inventory_full_report.html',
    'pdf/notifications_report.html',
    'pdf/orders_report.html',
    'pdf/payments_report.html',
    'pdf/projects_full_report.html',
    'pdf/services_report.html',
    'pdf/team_report.html',
    # standalone reports — must include the Cloudinary logo URL inline
    'pdf/audit_report.html',
    'pdf/financial_report.html',
    'pdf/inventory_report.html',
    'pdf/order_invoice.html',
    'pdf/project_report.html',
    'pdf/receipt.html',
    # empty-shell templates
    'pdf/quote_pdf.html',
    'pdf/report_template.html',
]

CLOUDINARY_LOGO = 'https://res.cloudinary.com/nifbnyz2/image/upload/w_400,c_scale/v1786023287/caldan/caldan/logo.png'

# Templates that extend _base_report.html get the logo from the base — they don't need to include it inline.
def _extends_base(tpl_path):
    full = os.path.join('templates', tpl_path)
    if not os.path.exists(full):
        return False
    with open(full, 'r', encoding='utf-8') as f:
        head = f.read(512)
    return '{% extends "pdf/_base_report.html" %}' in head

EXTENDERS = {tpl for tpl in PDF_TEMPLATES if _extends_base(tpl)}


class Stub:
    """A permissive attribute stub that returns safe defaults for any access.

    Returns a real datetime for date-like attribute names (so Django's `|date`
    filter doesn't blow up on empty strings), short strings for known
    attributes, and a new Stub for any other unknown access (so chains like
    `log.user.email` work even when `log.user` is itself a Stub).
    """
    DATE_ATTRS = {'created_at', 'updated_at', 'deleted_at', 'last_login',
                  'date_joined', 'start_date', 'end_date', 'paid_at',
                  'order_date', 'expires_at', 'completed_at', 'started_at',
                  'target_date', 'due_date', 'published_at', 'generated_at',
                  'week_ending', 'payment_date', 'expense_date', 'created',
                  'modified', 'scheduled_for', 'date', 'from_date', 'to_date',
                  'date_from', 'date_to'}
    def __init__(self, **kw):
        for k, v in kw.items():
            setattr(self, k, v)
    def __getattr__(self, name):
        if name in self.DATE_ATTRS:
            from datetime import datetime
            return datetime(2026, 8, 1, 12, 0, 0)
        return ''
    def __getitem__(self, name):
        return Stub()
    def __iter__(self):
        return iter([])
    def __len__(self):
        return 0
    def __str__(self):
        return ''
    def __bool__(self):
        return True
    def __call__(self, *args, **kwargs):
        return Stub()


def _user_stub():
    return Stub(
        email='admin@example.com',
        full_name='Admin User',
        get_full_name=lambda: 'Admin User',
    )


def _log_stub():
    return Stub(
        user=_user_stub(),
        action='login_success',
        entity_type='User',
        entity_id=1,
        ip_address='127.0.0.1',
        user_agent='Mozilla/5.0',
        user_role='admin',
        hash_current='abc123',
        hash_previous='def456',
        get_action_display=lambda: 'Login Success',
    )


def ctx_audit():
    """Context for the audit PDF — the only template that uses custom filters."""
    return {
        'brand_name': 'Caldan Construction and Consultancy Firm',
        'tagline': "Building Kenya's Future, One Project at a Time.",
        'generated_at': '2026-08-01 12:00:00',
        'report_subtitle': '',
        'total_records': 5,
        'total_actions': 5,
        'unique_users': 3,
        'security_events': 1,
        'security_events_list': [_log_stub()],
        'action_breakdown': [
            {'action': 'login_success', 'count': 12},
            {'action': 'project_created', 'count': 7},
        ],
        'user_activity': [
            {'user_full_name': 'Admin User', 'user_email': 'admin@example.com', 'count': 8},
        ],
        'logs': [_log_stub() for _ in range(3)],
        'previous_hash': '0000000000000000000000000000000000000000000000000000000000000000',
        'current_hash': '1111111111111111111111111111111111111111111111111111111111111111',
        'period_start': '2026-07-01',
        'period_end': '2026-08-01',
    }


def ctx_minimal():
    """Minimal context for templates that extend _base_report.html.

    The base template needs brand_name, tagline, generated_at, and the meta-row
    keys. Child templates that iterate over data can use Stubs via get_template
    permissions — we just need to get past render.
    """
    return {
        'brand_name': 'Caldan Construction and Consultancy Firm',
        'tagline': "Building Kenya's Future, One Project at a Time.",
        'generated_at': '2026-08-01 12:00:00',
        'report_subtitle': 'Sample Report',
        'total_records': 0,
        'total_actions': 0,
        'unique_users': 0,
        'security_events': 0,
        'security_events_list': [],
        'action_breakdown': [],
        'user_activity': [],
        'logs': [],
        'previous_hash': '',
        'current_hash': '',
        'period_start': '',
        'period_end': '',
        # Common keys other extenders iterate over
        'projects': [],
        'clients': [],
        'orders': [],
        'payments': [],
        'expenses': [],
        'inventory': [],
        'team_members': [],
        'posts': [],
        'notifications': [],
        'services': [],
        'milestones': [],
        'materials': [],
        'order': Stub(),
        'project': Stub(),
        'report': Stub(),
    }


# Each template gets the context that most closely matches what its service-layer
# caller actually feeds in. Audit gets the rich context; everything else gets the
# minimal one (which is enough to exercise render-time filter loading).
RENDER_CONTEXTS = {
    'pdf/audit_report.html': ctx_audit,
    'pdf/_base_report.html': ctx_minimal,
    'pdf/blog_report.html': ctx_minimal,
    'pdf/clients_report.html': ctx_minimal,
    'pdf/expenses_report.html': ctx_minimal,
    'pdf/inventory_full_report.html': ctx_minimal,
    'pdf/notifications_report.html': ctx_minimal,
    'pdf/orders_report.html': ctx_minimal,
    'pdf/payments_report.html': ctx_minimal,
    'pdf/projects_full_report.html': ctx_minimal,
    'pdf/services_report.html': ctx_minimal,
    'pdf/team_report.html': ctx_minimal,
    'pdf/report_template.html': ctx_minimal,
    'pdf/financial_report.html': ctx_minimal,
    'pdf/inventory_report.html': ctx_minimal,
    'pdf/order_invoice.html': ctx_minimal,
    'pdf/project_report.html': ctx_minimal,
    'pdf/receipt.html': ctx_minimal,
    'pdf/quote_pdf.html': ctx_minimal,
}


def main():
    failures = []
    render_successes = 0

    # 1. Source-level checks (logo, brand tokens, non-empty, no hard-coded brand text)
    for tpl_path in PDF_TEMPLATES:
        full_path = os.path.join('templates', tpl_path)
        if not os.path.exists(full_path):
            failures.append(f'  ✗ {tpl_path}: file missing')
            continue
        size = os.path.getsize(full_path)
        with open(full_path, 'r', encoding='utf-8') as f:
            src = f.read()
        if size == 0:
            failures.append(f'  ✗ {tpl_path}: empty file (0 bytes)')
            continue
        # Standalone templates must include the Cloudinary logo URL inline
        if tpl_path not in EXTENDERS:
            if CLOUDINARY_LOGO not in src:
                failures.append(f'  ✗ {tpl_path}: missing Cloudinary logo URL')
        # All standalone templates must NOT have hard-coded "CALDAN CONSTRUCTION" plain text
        if 'CALDAN CONSTRUCTION' in src and 'brand_name' not in src:
            failures.append(f'  ✗ {tpl_path}: hard-coded "CALDAN CONSTRUCTION" not using brand_name variable')

    # Spot-check _base_report.html has logo + tokens
    base_src = open('templates/pdf/_base_report.html').read()
    if CLOUDINARY_LOGO not in base_src:
        failures.append('  ✗ _base_report.html: missing Cloudinary logo')
    for token in ['#0D2B36', '#D4AF37', '#0F2A35']:  # 0F2A35 is the new title-block color
        if token not in base_src:
            failures.append(f'  ✗ _base_report.html: missing brand token {token}')

    # Spot-check _base_report.html defensively loads pdf_filters
    if '{% load pdf_filters %}' not in base_src:
        failures.append('  ✗ _base_report.html: missing {% load pdf_filters %} — templates using custom filters will break')

    # Spot-check quote_pdf.html has its essentials
    quote_src = open('templates/pdf/quote_pdf.html').read()
    for must in ['Quote', 'Caldan', 'brand_name', '@page', CLOUDINARY_LOGO]:
        if must not in quote_src:
            failures.append(f'  ✗ quote_pdf.html: missing {must}')

    # 2. Parse-time check via get_template() — catches template syntax errors
    from django.template.loader import get_template
    for tpl_path in PDF_TEMPLATES:
        try:
            get_template(tpl_path)
        except Exception as exc:
            failures.append(f'  ✗ {tpl_path}: parse error — {exc}')

    # 3. Render-time check via render_to_string() — catches filter-not-loaded regressions
    # This is the bit that would have caught the original bug: `|underscore_to_space`
    # only raises TemplateSyntaxError when the template is actually rendered, not when
    # it's parsed.
    from django.template.loader import render_to_string
    for tpl_path, ctx_factory in RENDER_CONTEXTS.items():
        try:
            html = render_to_string(tpl_path, ctx_factory())
        except Exception as exc:
            failures.append(f'  ✗ {tpl_path}: render failed — {exc}')
            continue
        render_successes += 1

    # 4. Adversarial — confirm the audit template actually USES a custom filter
    # (so the verifier can't be silently weakened by removing the filter call)
    audit_src = open('templates/pdf/audit_report.html').read()
    if 'underscore_to_space' not in audit_src:
        failures.append('  ✗ audit_report.html: no longer uses |underscore_to_space — defensive load cannot be verified')
    if '{% load pdf_filters %}' not in audit_src:
        failures.append('  ✗ audit_report.html: missing {% load pdf_filters %} — this is the original bug')

    print(f'Render-time: {render_successes}/{len(RENDER_CONTEXTS)} PDF templates rendered cleanly.')
    if failures:
        print('\nFAILURES:')
        for f in failures:
            print(f.replace('✗', 'X').replace('✓', 'OK'))
        sys.exit(1)
    print(f'OK All {len(RENDER_CONTEXTS)} PDF templates render. Source + parse + render checks pass. Brand tokens present.')


main()
