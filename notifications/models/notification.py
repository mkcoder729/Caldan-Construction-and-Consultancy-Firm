from django.db import models
from django.conf import settings
from django.utils import timezone


class Notification(models.Model):
    """In-app notification displayed in the dashboard."""

    class Priority(models.TextChoices):
        LOW = 'LOW', 'Low'
        MEDIUM = 'MEDIUM', 'Medium'
        HIGH = 'HIGH', 'High'
        URGENT = 'URGENT', 'Urgent'

    class Type(models.TextChoices):
        STOCK_ALERT = 'STOCK_ALERT', 'Stock Alert'
        ORDER_CONFIRMED = 'ORDER_CONFIRMED', 'Order Confirmed'
        ORDER_STATUS = 'ORDER_STATUS', 'Order Status Update'
        PROJECT_UPDATE = 'PROJECT_UPDATE', 'Project Update'
        PAYMENT_RECEIVED = 'PAYMENT_RECEIVED', 'Payment Received'
        ADMIN_INVITATION = 'ADMIN_INVITATION', 'Admin Invitation'
        SYSTEM = 'SYSTEM', 'System'
        REMINDER = 'REMINDER', 'Reminder'
        AUDIT = 'AUDIT', 'Audit Report'
        # Compassionate Ministry — added 2026-08-10 so bell notifications
        # are filterable by their compassion source event.
        COMPASSION_DONATION = 'COMPASSION_DONATION', 'Compassion Donation'
        COMPASSION_INKIND = 'COMPASSION_INKIND', 'Compassion In-Kind Pledge'
        COMPASSION_CALL = 'COMPASSION_CALL', 'Compassion Call Request'

    # Recipient
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications'
    )

    # Content
    title = models.CharField(max_length=200)
    message = models.TextField()
    type = models.CharField(max_length=20, choices=Type.choices, db_index=True)

    # Priority
    priority = models.CharField(max_length=10, choices=Priority.choices, default=Priority.MEDIUM)

    # Link (click to navigate)
    action_url = models.CharField(max_length=500, blank=True, default='')

    # Icon (Font Awesome)
    icon = models.CharField(max_length=50, default='fa-bell')

    # Read status
    is_read = models.BooleanField(default=False, db_index=True)
    read_at = models.DateTimeField(null=True, blank=True)

    # Metadata
    metadata = models.JSONField(default=dict, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'notifications'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read', 'created_at']),
            models.Index(fields=['type', 'created_at']),
            models.Index(fields=['priority']),
        ]

    def __str__(self):
        return f"[{self.get_priority_display()}] {self.title} - {self.user.email}"

    def mark_as_read(self):
        """Mark notification as read."""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])

    def mark_as_unread(self):
        """Mark notification as unread."""
        self.is_read = False
        self.read_at = None
        self.save(update_fields=['is_read', 'read_at'])