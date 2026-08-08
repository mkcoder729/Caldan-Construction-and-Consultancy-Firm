"""
ScheduleCall model — requests for a callback (large gifts, partnerships,
in-kind logistics, or just 'I want to talk first before donating').

Same shape as Donation and InKindDonation; admin workflow is just
NEW → CONTACTED → COMPLETED.
"""

from django.db import models
from django.utils import timezone


class ScheduleCall(models.Model):
    """A request for a callback from the Caldan Compassionate Ministry team."""

    class Topic(models.TextChoices):
        LARGE_DONATION = "LARGE_DONATION", "Large donation"
        PARTNERSHIP = "PARTNERSHIP", "Partnership / sponsorship"
        INKIND_LOGISTICS = "INKIND_LOGISTICS", "In-kind logistics"
        GENERAL = "GENERAL", "General / something else"

    class Status(models.TextChoices):
        NEW = "NEW", "New"
        CONTACTED = "CONTACTED", "Contacted"
        COMPLETED = "COMPLETED", "Completed"
        CANCELLED = "CANCELLED", "Cancelled"

    # ───── Contact info ─────
    name = models.CharField(max_length=150, verbose_name="Full name")
    email = models.EmailField(verbose_name="Email address")
    phone = models.CharField(max_length=15, verbose_name="Phone number")

    # ───── Topic / message ─────
    topic = models.CharField(
        max_length=20,
        choices=Topic.choices,
        default=Topic.GENERAL,
        db_index=True,
        verbose_name="Topic",
    )
    preferred_time = models.CharField(
        max_length=200,
        verbose_name="Preferred time",
        help_text="Free-text window, e.g. 'Mon–Fri 9am–12pm'",
    )
    message = models.TextField(blank=True, default="", verbose_name="Message")

    # ───── Workflow ─────
    status = models.CharField(
        max_length=12,
        choices=Status.choices,
        default=Status.NEW,
        db_index=True,
        verbose_name="Status",
    )
    status_changed_at = models.DateTimeField(null=True, blank=True)

    # ───── Audit metadata ─────
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=300, blank=True, default="")

    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "compassion_schedule_calls"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "-created_at"]),
            models.Index(fields=["topic", "-created_at"]),
            models.Index(fields=["email", "-created_at"]),
        ]
        verbose_name = "Schedule Call Request"
        verbose_name_plural = "Schedule Call Requests"

    def __str__(self) -> str:
        return f"{self.name} — {self.get_topic_display()} — {self.get_status_display()}"

    def advance_to(self, new_status: str) -> None:
        if new_status not in self.Status.values:
            raise ValueError(f"Invalid status: {new_status}")
        if self.status == new_status:
            return
        self.status = new_status
        self.status_changed_at = timezone.now()
        self.save(update_fields=["status", "status_changed_at", "updated_at"])
