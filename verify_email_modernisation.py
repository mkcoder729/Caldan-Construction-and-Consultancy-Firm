"""
Verify: all 27 email templates render successfully via EmailService.send_template,
each carries the Cloudinary logo.png (NOT theme variants), and the base
template contains a dark-mode media query.

Slim Salvins-pattern base: {% block content %} with optional {% block badge %}
and {% block footer_extra %}.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'calsite.settings')
django.setup()

from datetime import datetime
from django.template.loader import render_to_string
from notifications.services.email_service import EmailService


class Stub:
    """Attribute stub. No date() method so Django's date filter isn't shadowed."""
    def __init__(self, **kw):
        for k, v in kw.items():
            setattr(self, k, v)
    def __getattr__(self, name):
        return ''
    def __getitem__(self, name):
        if name in self.__dict__:
            return self.__dict__[name]
        if isinstance(name, str) and name.isdigit() and name in self.__dict__:
            return self.__dict__[name]
        return Stub()
    def __str__(self): return ''
    def __bool__(self): return True
    def __iter__(self): return iter([])
    def __len__(self): return 0
    def get_status_display(self): return 'In Progress'
    def get_category_display(self): return 'Insights'
    def get_unit_display(self): return 'units'
    def get_type_display(self): return 'Type'
    def get_role_display(self): return 'Platform Admin'
    def full_name(self): return ''
    def truncatechars(self, n): return 'name'


def D(s, with_time=False):
    try:
        if with_time:
            return datetime.strptime(s + ' 12:00:00', '%Y-%m-%d %H:%M:%S')
        return datetime.strptime(s, '%Y-%m-%d').date()
    except (TypeError, ValueError):
        return s


def base_ctx():
    return {
        'brand_name': 'Caldan Construction and Consultancy Firm',
        'tagline': "Building Kenya's Future, One Project at a Time.",
        'current_year': 2026,
        'support_email': 'info.caldanconstruction@gmail.com',
        'site_url': 'http://localhost:8000',
        'logo_url': EmailService.LOGO_URL,
        'unsubscribe_url': 'http://localhost:8000/newsletter/unsubscribe/verify@example.com/',
    }


def ctx_welcome_admin():
    c = {'user': Stub(email='admin@example.com', full_name='Admin', get_full_name=lambda: 'Admin')}
    c.update(base_ctx()); return c

def ctx_weekly_report():
    c = {'report': Stub(week_ending=D('2026-08-01'), active_projects=12, new_orders=4, revenue=120000, highlights=['Highlight A', 'Highlight B'], totals={'Metric': 'Value'})}
    c.update(base_ctx()); return c

def ctx_backup_completed():
    c = {'backup_name': 'backup-2026-08-01', 'backup_size': '12 MB', 'storage_location': 'media/backups/', 'started_at': D('2026-08-01', with_time=True), 'completed_at': D('2026-08-01', with_time=True), 'duration': '00:02:30', 'action_url': '/dashboard/admin/reports/'}
    c.update(base_ctx()); return c

def ctx_order_status_update():
    c = {'order': Stub(order_number='ORD-001', client_name='Customer', status='SHIPPED', get_status_display=lambda: 'SHIPPED', tracking_number='TRK-123', estimated_delivery=D('2026-08-10'), items=Stub(all=[Stub(quantity=2, product=Stub(name='Item'), total_price=2000)]), total=2000), 'updated_at': D('2026-08-01', with_time=True)}
    c.update(base_ctx()); return c

def ctx_quote_received():
    c = {'name': 'John', 'email': 'john@example.com', 'phone': '+254700000000', 'project_type': 'Construction', 'budget': 'KES 1M-3M', 'details': 'Build a 4-bed house', 'action_url': '/dashboard/quotes/1/'}
    c.update(base_ctx()); return c

def ctx_quote_user_reply():
    c = {'name': 'John', 'project_type': 'Construction', 'timeline': '3-6 months', 'details': 'Build a 4-bed house', 'schedule_call': False, 'preferred_call_time': ''}
    c.update(base_ctx()); return c

def ctx_weekly_project_report():
    c = {'report': Stub(generated_at=D('2026-08-01', with_time=True), total_projects=8, by_status={'Active': 5, 'Completed': 3}, projects=[])}
    c.update(base_ctx()); return c

def ctx_stock_alert():
    c = {'material': Stub(name='Cement', category=Stub(name='Building'), supplier=Stub(name='Supplier X'), get_unit_display=lambda: 'bags'), 'current_quantity': 5, 'minimum_threshold': 20}
    c.update(base_ctx()); return c

def ctx_tracking_code():
    c = {'order': Stub(order_number='ORD-001'), 'code': '123456', 'client_name': 'Customer', 'tracking_link': 'https://caldanconstruction.com/track', 'expiry_minutes': 10}
    c.update(base_ctx()); return c

def ctx_daily_summary():
    c = {'date': D('2026-08-01'), 'stats': {'Orders': 4, 'Revenue': 'KES 120K'}}
    c.update(base_ctx()); return c

def ctx_newsletter_confirmation():
    c = {'email': 'sub@example.com', 'subscriber': Stub(email='sub@example.com')}
    c.update(base_ctx()); return c

def ctx_milestone_overdue():
    c = {'milestone': Stub(title='Foundation', target_date=D('2026-07-01'), get_status_display=lambda: 'Pending'), 'project': Stub(name='House Build', id=1), 'overdue_days': 5}
    c.update(base_ctx()); return c

def ctx_contact_user_reply():
    c = {'name': 'John', 'subject': 'Question', 'message': 'Hi, when can you start?'}
    c.update(base_ctx()); return c

def ctx_contact_received():
    c = {'name': 'John', 'email': 'john@example.com', 'phone': '+254700000000', 'message': 'Hi, when can you start?', 'action_url': '/dashboard/contact/'}
    c.update(base_ctx()); return c

def ctx_admin_invitation():
    c = {'invitation': Stub(email='new@example.com', role='Platform Admin', full_name='New Admin', phone='+254700000000', expires_at=D('2026-08-02', with_time=True), personal_message='Welcome aboard'), 'created_by': Stub(full_name='Admin', email='admin@example.com'), 'invitation_link': 'https://site.com/accept/abc', 'expiry_hours': 48, 'temp_password': 'Temp1234!', 'permissions': []}
    c.update(base_ctx()); return c

def ctx_admin_invitation_sent():
    c = {'invitation': Stub(email='new@example.com', full_name='New Admin', role='Platform Admin', expires_at=D('2026-08-02', with_time=True), created_at=D('2026-08-01', with_time=True)), 'inviter': Stub(full_name='Admin'), 'channels_sent': ['Email'], 'channels_failed': [], 'manage_url': '/dashboard/admins/', 'expiry_hours': 48}
    c.update(base_ctx()); return c

def ctx_schedule_call_requested():
    c = {'name': 'John', 'phone': '+254700000000', 'email': 'john@example.com', 'preferred_call_time': 'Mon-Fri 9-12', 'project_type': 'Construction', 'budget_range': '1M-3M', 'timeline': '3-6 months', 'details': 'Build a 4-bed house', 'quote_id': 1, 'action_url': '/dashboard/quotes/1/'}
    c.update(base_ctx()); return c

def ctx_password_reset():
    c = {'email': 'user@example.com', 'uid': 'abc', 'token': 'def', 'protocol': 'https', 'domain': 'caldanconstruction.com', 'user': Stub()}
    c.update(base_ctx()); return c

def ctx_notification():
    c = {'title': 'New', 'message': 'Something happened', 'priority': 'high', 'notification_type': 'order', 'metadata': {'Order': 'ORD-001'}}
    c.update(base_ctx()); return c

def ctx_account_activation_reminder():
    c = {}
    c.update(base_ctx()); return c

def ctx_daily_stock_summary():
    c = {'date': D('2026-08-01'), 'summary': Stub(total_materials=20, low_stock_count=3, out_of_stock_count=1, total_value=200000, low_stock=[Stub(name='Cement', current_quantity=5, unit='bags', minimum_threshold=20)])}
    c.update(base_ctx()); return c

def ctx_newsletter_email():
    c = {'post': Stub(title='Hello', excerpt='Excerpt', content='Body', featured_image=Stub(url='https://x/y.png'), published_at=D('2026-08-01'), created_at=D('2026-08-01'), get_category_display=lambda: 'Insights', slug='hello'), 'post_url': 'http://localhost:8000/blog/hello/', 'email': 'sub@example.com', 'unsubscribe_url': 'http://localhost:8000/newsletter/unsubscribe/sub@example.com/'}
    c.update(base_ctx()); return c

def ctx_order_confirmation():
    c = {'order': Stub(order_number='ORD-001', client_name='Customer', created_at=D('2026-08-01', with_time=True), get_status_display=lambda: 'PROCESSING', subtotal=2000, delivery_fee=200, total=2200, delivery_address='123 Main', delivery_town='Nairobi', delivery_county='Nairobi', delivery_notes='', items=Stub(all=[Stub(quantity=2, product=Stub(name='Item'), total_price=2000)]))}
    c.update(base_ctx()); return c

def ctx_payment_receipt():
    c = {'order': Stub(order_number='ORD-001', paid_at=D('2026-08-01', with_time=True), created_at=D('2026-08-01', with_time=True), paystack_reference='PAY-REF', total=2200, items=Stub(all=[Stub(quantity=2, product=Stub(name='Item'), total_price=2000)]))}
    c.update(base_ctx()); return c

def ctx_otp_email():
    c = {'user': Stub(email='user@example.com', full_name='User', get_full_name=lambda: 'User'), 'otp_code': '123456', 'expiry_minutes': 5, 'device_info': 'Chrome', 'ip_address': '127.0.0.1'}
    c.update(base_ctx()); return c

def ctx_admin_order_alert():
    c = {'order': Stub(order_number='ORD-001', client_name='Customer', client_email='c@x.com', client_phone='+254', delivery_address='123 Main', delivery_town='Nairobi', delivery_county='Nairobi', delivery_notes='', created_at=D('2026-08-01', with_time=True), total=2200, items=Stub(all=[Stub(quantity=2, product=Stub(name='Item'), total_price=2000)]), pk=1)}
    c.update(base_ctx()); return c

def ctx_bi_weekly_audit():
    c = {'period_start': D('2026-07-15'), 'period_end': D('2026-08-01'), 'total_actions': 120, 'unique_users': 4, 'report_pdf_url': None}
    c.update(base_ctx()); return c


EMAIL_TEMPLATES = [
    ('email/welcome_admin.html', ctx_welcome_admin),
    ('email/weekly_report.html', ctx_weekly_report),
    ('email/backup_completed.html', ctx_backup_completed),
    ('email/order_status_update.html', ctx_order_status_update),
    ('email/quote_received.html', ctx_quote_received),
    ('email/quote_user_reply.html', ctx_quote_user_reply),
    ('email/weekly_project_report.html', ctx_weekly_project_report),
    ('email/stock_alert.html', ctx_stock_alert),
    ('email/tracking_code.html', ctx_tracking_code),
    ('email/daily_summary.html', ctx_daily_summary),
    ('email/newsletter_confirmation.html', ctx_newsletter_confirmation),
    ('email/milestone_overdue.html', ctx_milestone_overdue),
    ('email/contact_user_reply.html', ctx_contact_user_reply),
    ('email/contact_received.html', ctx_contact_received),
    ('email/admin_invitation.html', ctx_admin_invitation),
    ('email/admin_invitation_sent.html', ctx_admin_invitation_sent),
    ('email/schedule_call_requested.html', ctx_schedule_call_requested),
    ('email/password_reset.html', ctx_password_reset),
    ('email/notification.html', ctx_notification),
    ('email/account_activation_reminder.html', ctx_account_activation_reminder),
    ('email/daily_stock_summary.html', ctx_daily_stock_summary),
    ('email/newsletter_email.html', ctx_newsletter_email),
    ('email/order_confirmation.html', ctx_order_confirmation),
    ('email/payment_receipt.html', ctx_payment_receipt),
    ('email/otp_email.html', ctx_otp_email),
    ('email/admin_order_alert.html', ctx_admin_order_alert),
    ('email/bi_weekly_audit.html', ctx_bi_weekly_audit),
]


def main():
    failures = []
    successes = 0

    print('=== Email template render check (Salvins-pattern base) ===\n')
    for tpl_path, ctx_factory in EMAIL_TEMPLATES:
        ctx = ctx_factory()
        try:
            html = render_to_string(tpl_path, ctx)
        except Exception as exc:
            failures.append(f'  X {tpl_path}: render failed: {exc}')
            continue

        successes += 1

        # Must contain logo.png URL
        if EmailService.LOGO_URL not in html:
            failures.append(f'  X {tpl_path}: missing logo.png URL ({EmailService.LOGO_URL})')

        # Must NOT contain theme variants (user's key complaint)
        if 'logo_light.png' in html or 'logo_dark.png' in html:
            failures.append(f'  X {tpl_path}: still using logo_light/dark variant — must use logo.png only')

        # Must contain brand palette
        if '#0D2B36' not in html and '#0d2b36' not in html and 'brand-navy' not in html:
            failures.append(f'  X {tpl_path}: missing brand navy in rendered HTML')

        # Must reference Caldan
        if 'Caldan' not in html:
            failures.append(f'  X {tpl_path}: missing Caldan branding')

        # Must have a button/link CTA
        if '.button' not in html and 'cta' not in html.lower() and '<a href' not in html:
            failures.append(f'  X {tpl_path}: no CTA link found')

        # Check single-line comments in source
        with open('templates/' + tpl_path, 'r', encoding='utf-8') as f:
            src = f.read()
        for i, ln in enumerate(src.splitlines(), 1):
            stripped = ln.strip()
            if stripped == '{#' or stripped == '#}':
                failures.append(f'  X {tpl_path}:line {i}: orphan {stripped} comment marker')
                break

    # Marketing templates must include unsubscribe link
    for tpl_path in ['email/newsletter_email.html', 'email/newsletter_confirmation.html']:
        with open('templates/' + tpl_path, 'r', encoding='utf-8') as f:
            src = f.read()
        if 'unsubscribe' not in src.lower():
            failures.append(f'  X {tpl_path}: marketing template missing unsubscribe link')

    # Verify _base.html contains dark-mode media query
    base = open('templates/email/_base.html').read()
    if 'prefers-color-scheme: dark' in base:
        print('OK _base.html contains @media (prefers-color-scheme: dark)')
    else:
        print('  X _base.html missing dark-mode media query')

    # Verify base no longer hardcodes both light + dark variants
    if 'logo_light.png' in base or 'logo_dark.png' in base:
        print('  X _base.html still references logo_light/dark variants')
    else:
        print('OK _base.html uses logo.png only (no theme variants)')

    # Verify base uses Salvins-style slim container
    if '.email-container' in base and 'max-width: 600px' in base:
        print('OK _base.html uses slim 600px email-container pattern')
    else:
        print('  X _base.html does not match expected slim container pattern')

    # Verify base_email.html was deleted
    if not os.path.exists('templates/email/base_email.html'):
        print('OK obsolete base_email.html deleted')
    else:
        print('  X obsolete base_email.html still exists')

    print(f'\n{successes}/{len(EMAIL_TEMPLATES)} templates rendered successfully.')
    if failures:
        print('\nFAILURES:')
        for f in failures:
            print(f)
    else:
        print('OK All checks passed.')


main()
