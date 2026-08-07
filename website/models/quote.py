from django.db import models
from django.utils import timezone
from services.models import Service


class QuoteRequest(models.Model):
    """
    Quote request form submission from the public website.

    Captures detailed project information for construction quotes.
    """

    class BudgetRange(models.TextChoices):
        UNDER_100K = "UNDER_100K", "Under KSh 100,000"
        _100K_500K = "_100K_500K", "KSh 100,000 - 500,000"
        _500K_1M = "_500K_1M", "KSh 500,000 - 1,000,000"
        _1M_5M = "_1M_5M", "KSh 1,000,000 - 5,000,000"
        _5M_10M = "_5M_10M", "KSh 5,000,000 - 10,000,000"
        OVER_10M = "OVER_10M", "Over KSh 10,000,000"
        NOT_SURE = "NOT_SURE", "Not Sure"

    class Timeline(models.TextChoices):
        URGENT = "URGENT", "Urgent (Within 1 month)"
        SOON = "SOON", "Soon (1-3 months)"
        MEDIUM = "MEDIUM", "Medium term (3-6 months)"
        LONG = "LONG", "Long term (6+ months)"
        NOT_SURE = "NOT_SURE", "Not Sure"

    name = models.CharField(max_length=150, verbose_name="Full Name")
    email = models.EmailField(verbose_name="Email Address")
    phone = models.CharField(max_length=15, verbose_name="Phone Number")

    project_type = models.CharField(
        max_length=20,
        choices=Service.Category.choices,
        verbose_name="Project Type"
    )
    budget_range = models.CharField(
        max_length=20,
        choices=BudgetRange.choices,
        default=BudgetRange.NOT_SURE,
        verbose_name="Budget Range"
    )
    timeline = models.CharField(
        max_length=20,
        choices=Timeline.choices,
        default=Timeline.NOT_SURE,
        verbose_name="Timeline"
    )
    details = models.TextField(verbose_name="Project Details")

    # Schedule a call (optional) — captured by the public form so the
    # requester can ask for a phone walkthrough instead of email-only.
    schedule_call_requested = models.BooleanField(
        default=False,
        verbose_name="Schedule a call",
    )
    preferred_call_time = models.CharField(
        max_length=120,
        blank=True,
        default="",
        verbose_name="Preferred call time",
        help_text="Free-text window when the requester is available.",
    )

    is_replied = models.BooleanField(default=False, verbose_name="Replied", db_index=True)
    replied_at = models.DateTimeField(null=True, blank=True, verbose_name="Replied At")

    created_at = models.DateTimeField(default=timezone.now, verbose_name="Submitted At", db_index=True)
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated At")

    class Meta:
        db_table = "website_quote_requests"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["email", "-created_at"]),
            models.Index(fields=["project_type", "-created_at"]),
            models.Index(fields=["is_replied", "-created_at"]),
        ]
        verbose_name = "Quote Request"
        verbose_name_plural = "Quote Requests"

    def __str__(self) -> str:
        return f"{self.name} <{self.email}> - {self.get_project_type_display()}"

    def mark_replied(self) -> None:
        """Mark this quote request as replied to."""
        self.is_replied = True
        self.replied_at = timezone.now()
        self.save(update_fields=["is_replied", "replied_at"])