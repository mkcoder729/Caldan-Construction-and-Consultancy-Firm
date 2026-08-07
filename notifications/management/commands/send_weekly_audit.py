"""
Management command: send_weekly_audit.

Generates the bi-weekly audit report and emails it to admins.
Mirrors the `send_weekly_audit` Celery task — useful for cron
without Celery Beat, or for ad-hoc local testing.
"""

from django.core.management.base import BaseCommand

from notifications.services.reminder_service import ReminderService


class Command(BaseCommand):
    help = "Generate and email the bi-weekly audit report."

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Generating bi-weekly audit report..."))
        summary = ReminderService.send_bi_weekly_audit()
        self.stdout.write(self.style.SUCCESS(f"Done: {summary}"))
