from django.db import models
from django.conf import settings


class EmailLog(models.Model):
    """Audit log for all emails sent through the platform."""

    class Status(models.TextChoices):
        SENT = 'SENT', 'Successfully Sent'
        FAILED = 'FAILED', 'Failed to Send'
        BOUNCED = 'BOUNCED', 'Bounced'
        DEV_MODE = 'DEV_MODE', 'Development Mode (Not Sent)'

    # Recipient
    to_email = models.EmailField()
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='email_logs',
    )

    # Content
    subject = models.CharField(max_length=200)
    email_type = models.CharField(max_length=50, db_index=True)

    # Delivery
    status = models.CharField(max_length=10, choices=Status.choices, default='SENT', db_index=True)
    email_id = models.CharField(max_length=100, blank=True, default='')
    error_message = models.TextField(blank=True, default='')

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'email_logs'
        verbose_name = 'Email Log'
        verbose_name_plural = 'Email Logs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['email_type', 'created_at']),
        ]

    def __str__(self):
        return f"Email to {self.to_email} - {self.subject[:50]}"