"""
ScheduledExport model for automated report generation.
Caldan Construction - "Building Kenya's Future, One Project at a Time."
"""

from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.exceptions import ValidationError


class ScheduledExport(models.Model):
    """
    Model for scheduling automated report exports.
    Supports daily, weekly, and monthly schedules.
    """

    class ReportType(models.TextChoices):
        PROJECT = 'PROJECT', 'Project Report'
        INVENTORY = 'INVENTORY', 'Inventory Report'
        FINANCIAL = 'FINANCIAL', 'Financial Report'
        ORDERS = 'ORDERS', 'Orders Report'
        CLIENTS = 'CLIENTS', 'Clients Report'
        AUDIT = 'AUDIT', 'Audit Report'

    class Format(models.TextChoices):
        CSV = 'CSV', 'CSV'
        EXCEL = 'EXCEL', 'Excel (.xlsx)'
        PDF = 'PDF', 'PDF'

    class Schedule(models.TextChoices):
        DAILY = 'DAILY', 'Daily'
        WEEKLY = 'WEEKLY', 'Weekly'
        MONTHLY = 'MONTHLY', 'Monthly'

    # Identity
    name = models.CharField(
        max_length=100,
        help_text='A descriptive name for this scheduled export'
    )

    # Report configuration
    report_type = models.CharField(
        max_length=20,
        choices=ReportType.choices,
        db_index=True
    )

    format = models.CharField(
        max_length=10,
        choices=Format.choices,
        default=Format.PDF
    )

    # Schedule
    schedule = models.CharField(
        max_length=10,
        choices=Schedule.choices,
        default=Schedule.WEEKLY
    )

    # Filters (stored as JSON)
    filters = models.JSONField(
        default=dict,
        blank=True,
        help_text='Report filter parameters'
    )

    # Scheduling
    last_run = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When this export was last executed'
    )

    next_run = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When this export is scheduled to run next'
    )

    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text='Whether this schedule is active'
    )

    # Delivery (future: email, cloud storage)
    delivery_email = models.EmailField(
        blank=True,
        default='',
        help_text='Email to send the export to'
    )

    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='scheduled_exports'
    )

    class Meta:
        db_table = 'scheduled_exports'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['is_active', 'next_run']),
            models.Index(fields=['report_type']),
        ]

    def __str__(self):
        return f"{self.name} ({self.report_type})"

    def save(self, *args, **kwargs):
        """Calculate next_run on save if not set."""
        if not self.next_run:
            self.next_run = self.calculate_next_run()
        super().save(*args, **kwargs)

    def calculate_next_run(self):
        """Calculate the next run time based on schedule."""
        now = timezone.now()

        if self.schedule == self.Schedule.DAILY:
            # Tomorrow at 6:00 AM
            next_run = now.replace(hour=6, minute=0, second=0, microsecond=0)
            if next_run <= now:
                next_run = next_run + timezone.timedelta(days=1)

        elif self.schedule == self.Schedule.WEEKLY:
            # Next Monday at 6:00 AM
            days_ahead = 0 - now.weekday()
            if days_ahead <= 0:
                days_ahead += 7
            next_run = (now + timezone.timedelta(days=days_ahead)).replace(
                hour=6, minute=0, second=0, microsecond=0
            )

        elif self.schedule == self.Schedule.MONTHLY:
            # First day of next month at 6:00 AM
            if now.month == 12:
                next_run = now.replace(year=now.year + 1, month=1, day=1, hour=6, minute=0, second=0, microsecond=0)
            else:
                next_run = now.replace(month=now.month + 1, day=1, hour=6, minute=0, second=0, microsecond=0)

        else:
            next_run = now + timezone.timedelta(days=7)

        return next_run

    def mark_run(self):
        """Update last_run and recalculate next_run."""
        self.last_run = timezone.now()
        self.next_run = self.calculate_next_run()
        self.save(update_fields=['last_run', 'next_run'])