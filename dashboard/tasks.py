"""
Dashboard Celery tasks
Background tasks for dashboard analytics and reporting.
"""

from celery import shared_task
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import logging

from dashboard.services.stats_service import StatsService
from dashboard.services.activity_service import ActivityService

logger = logging.getLogger('caldan.dashboard')


@shared_task
def refresh_dashboard_stats():
    """
    Refresh cached dashboard statistics.
    Runs every hour to keep stats fresh.
    """
    logger.info("Refreshing dashboard statistics...")
    try:
        stats = StatsService.get_overview_stats()
        chart_data = StatsService.get_chart_data(months=6)
        order_chart = StatsService.get_order_status_chart()

        logger.info(f"Dashboard stats refreshed: {len(stats.get('projects', {}))} projects")
        return {
            'success': True,
            'timestamp': timezone.now().isoformat(),
            'stats': stats,
            'chart_data': chart_data,
            'order_chart': order_chart,
        }
    except Exception as e:
        logger.error(f"Failed to refresh dashboard stats: {str(e)}")
        return {'success': False, 'error': str(e)}


@shared_task
def cleanup_old_activity():
    """
    Clean up activity feed older than 30 days.
    Runs daily to keep database size manageable.
    """
    from accounts.models import AuditLog

    cutoff_date = timezone.now() - timedelta(days=30)
    deleted_count, _ = AuditLog.objects.filter(created_at__lt=cutoff_date).delete()

    logger.info(f"Cleaned up {deleted_count} old activity logs")
    return {'deleted_count': deleted_count}


@shared_task
def generate_daily_summary():
    """
    Generate daily summary email for admins with an attached PDF report.
    Runs daily at 6:00 AM.

    Per the platform rule "all admin-facing email goes to ADMIN_EMAIL"
    we send a single email to the shared admin inbox (defaults to
    info.caldanconstruction@gmail.com). The PDF is generated once and
    attached to that email.
    """
    from django.contrib.auth import get_user_model
    from notifications.services.email_service import EmailService

    User = get_user_model()
    admins = User.objects.filter(is_staff=True, is_active=True)

    stats = StatsService.get_overview_stats()

    # Build a richer report dict so the PDF has more than the dashboard stats.
    from reports.services.pdf_service import PDFService
    today = timezone.now().date()
    report = {
        'generated_at': today.isoformat(),
        'stats': stats,
    }

    # Generate one PDF for the email (faster than per-admin and matches
    # the platform rule of a single ADMIN_EMAIL recipient).
    pdf_filename = f"daily_summary_{today.strftime('%Y%m%d')}.pdf"
    pdf_bytes = b''
    try:
        pdf_path = PDFService.generate_pdf_to_file(
            template_name='pdf/notifications_report.html',
            context={
                'report': report,
                'brand_name': 'Caldan Construction and Consultancy Firm',
                'tagline': "Building Kenya's Future, One Project at a Time.",
                'generated_at': timezone.now(),
            },
            filename=pdf_filename.replace('.pdf', ''),
        )
        with open(pdf_path, 'rb') as fh:
            pdf_bytes = fh.read()
    except Exception as pdf_err:
        logger.warning(f"PDF generation skipped for daily summary: {pdf_err}")

    attachments = [{'filename': pdf_filename, 'content': pdf_bytes}] if pdf_bytes else None

    admin_email = getattr(settings, 'ADMIN_EMAIL', '') or 'info.caldanconstruction@gmail.com'
    sent_count = 0
    try:
        success = EmailService.send_template(
            to_email=admin_email,
            subject=f'Caldan Construction and Consultancy Firm - Daily Summary {today}',
            template_name='email/daily_summary.html',
            context={
                'user': admins.first(),
                'stats': stats,
                'date': today,
                'dashboard_url': '/dashboard/',
            },
            user=admins.first(),
            email_type='DAILY_SUMMARY',
            attachments=attachments,
        )
        if success:
            sent_count = 1
    except Exception as exc:
        logger.error(f"Failed to send daily summary to {admin_email}: {exc}")

    logger.info(f"Daily summary sent to {sent_count} admins")
    return {'sent_count': sent_count, 'total_admins': admins.count(), 'pdf_attached': bool(pdf_bytes)}