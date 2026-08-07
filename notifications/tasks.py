"""
Celery tasks for the notifications app.

These wrap the service-layer functions so they can be scheduled
through Celery Beat (see calsite/celery.py / settings.py).
"""

import logging

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger('caldan.notifications.tasks')


@shared_task(
    name='notifications.send_daily_reminders',
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def send_daily_reminders(self):
    """
    Daily reminder sweep — runs low-stock and pending-order checks.
    """
    try:
        from notifications.services.reminder_service import ReminderService
        results = ReminderService.run_daily_checks()
        logger.info(f"Daily reminders completed: {results}")
        return results
    except Exception as exc:
        logger.exception("send_daily_reminders failed: %s", exc)
        raise self.retry(exc=exc)


@shared_task(
    name='notifications.send_weekly_audit',
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def send_weekly_audit(self):
    """
    Bi-weekly audit report — generated and emailed to admins.
    """
    try:
        from notifications.services.reminder_service import ReminderService
        summary = ReminderService.send_bi_weekly_audit()
        logger.info(f"Weekly audit dispatched: {summary}")
        return summary
    except Exception as exc:
        logger.exception("send_weekly_audit failed: %s", exc)
        raise self.retry(exc=exc)


@shared_task(
    name='notifications.cleanup_old_email_logs',
    bind=True,
)
def cleanup_old_email_logs(self, retention_days: int = 90):
    """
    Delete email log rows older than `retention_days`.

    Keeps the EmailLog table from growing unbounded. 90 days is a
    reasonable default; tune via the `AUDIT_LOG_RETENTION_DAYS`
    setting in production.
    """
    try:
        from notifications.models import EmailLog
        from django.conf import settings

        days = retention_days or getattr(settings, 'AUDIT_LOG_RETENTION_DAYS', 365)
        cutoff = timezone.now() - timezone.timedelta(days=days)
        deleted, _ = EmailLog.objects.filter(created_at__lt=cutoff).delete()
        logger.info(f"Cleaned up {deleted} email logs older than {days} days.")
        return {'deleted': deleted, 'cutoff': cutoff.isoformat()}
    except Exception as exc:
        logger.exception("cleanup_old_email_logs failed: %s", exc)
        return {'error': str(exc)}
