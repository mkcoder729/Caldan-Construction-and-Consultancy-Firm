from django.db import models
from django.utils import timezone


class ContactSubmission(models.Model):
    """
    Contact form submission from the public website.

    Stores all contact form submissions with timestamps and reply tracking.
    """

    name = models.CharField(max_length=150, verbose_name="Full Name")
    email = models.EmailField(verbose_name="Email Address")
    phone = models.CharField(max_length=15, verbose_name="Phone Number")
    subject = models.CharField(max_length=200, verbose_name="Subject")
    message = models.TextField(verbose_name="Message")

    is_replied = models.BooleanField(default=False, verbose_name="Replied", db_index=True)
    replied_at = models.DateTimeField(null=True, blank=True, verbose_name="Replied At")

    created_at = models.DateTimeField(default=timezone.now, verbose_name="Submitted At", db_index=True)
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated At")

    class Meta:
        db_table = "website_contact_submissions"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["email", "-created_at"]),
            models.Index(fields=["is_replied", "-created_at"]),
        ]
        verbose_name = "Contact Submission"
        verbose_name_plural = "Contact Submissions"

    def __str__(self) -> str:
        return f"{self.name} <{self.email}> - {self.subject[:50]}"

    def mark_replied(self) -> None:
        """Mark this submission as replied to."""
        self.is_replied = True
        self.replied_at = timezone.now()
        self.save(update_fields=["is_replied", "replied_at"])