from django.db import models
from django.conf import settings


class SMSLog(models.Model):
    """Audit log for all SMS messages sent."""

    class Status(models.TextChoices):
        SENT = 'SENT', 'Successfully Sent'
        FAILED = 'FAILED', 'Failed to Send'
        DEV_MODE = 'DEV_MODE', 'Development Mode'

    recipient_phone = models.CharField(max_length=15)
    message = models.TextField()
    status = models.CharField(max_length=10, choices=Status.choices, default='SENT', db_index=True)
    provider = models.CharField(max_length=50, blank=True, default='')
    provider_response = models.TextField(blank=True, default='')
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sms_logs',
    )
    notification_type = models.CharField(max_length=50, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'sms_logs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['notification_type', 'created_at']),
        ]

    def __str__(self):
        return f"SMS to {self.recipient_phone} - {self.status}"