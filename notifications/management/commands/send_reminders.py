"""
Management command: send_reminders.

Runs the daily reminder sweep (low-stock alerts, pending-order
reminders). Equivalent to invoking the `send_daily_reminders`
Celery task synchronously — useful for cron jobs that don't have
Celery Beat available, or for ad-hoc local testing.
"""

from django.core.management.base import BaseCommand

from notifications.services.reminder_service import ReminderService


class Command(BaseCommand):
    help = "Run the daily reminder sweep (low-stock, pending orders)."

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Running daily reminder checks..."))
        results = ReminderService.run_daily_checks()
        self.stdout.write(self.style.SUCCESS(f"Done: {results}"))
