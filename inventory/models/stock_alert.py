"""
Stock Alert Model - Tracks low stock notifications.

Automatically created when a material falls below its minimum threshold.
Tracks resolution and integrates with notification system.
"""

from django.db import models
from django.conf import settings
from django.utils import timezone


class StockAlert(models.Model):
    """Low stock alert for materials."""

    class Status(models.TextChoices):
        OPEN = 'OPEN', 'Open'
        RESOLVED = 'RESOLVED', 'Resolved'
        IGNORED = 'IGNORED', 'Ignored'

    # =====================================================================
    # RELATIONSHIPS
    # =====================================================================
    material = models.ForeignKey(
        'inventory.Material',
        on_delete=models.CASCADE,
        related_name='stock_alerts',
        help_text="Material that triggered this alert"
    )

    # =====================================================================
    # ALERT DETAILS
    # =====================================================================
    message = models.TextField(
        help_text="Alert message (auto-generated)"
    )
    threshold_quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Threshold that triggered this alert"
    )
    current_quantity_at_alert = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Current quantity when alert was created"
    )

    # =====================================================================
    # STATUS
    # =====================================================================
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.OPEN,
        db_index=True,
        help_text="Alert status"
    )

    # =====================================================================
    # RESOLUTION
    # =====================================================================
    resolved_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this alert was resolved"
    )
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resolved_alerts',
        help_text="Admin who resolved this alert"
    )
    resolution_notes = models.TextField(
        blank=True,
        default='',
        help_text="Notes about how this alert was resolved"
    )

    # =====================================================================
    # TIMESTAMPS
    # =====================================================================
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'stock_alerts'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', '-created_at'], name='alert_status_created_idx'),
            models.Index(fields=['material', 'status'], name='alert_material_status_idx'),
        ]

    def __str__(self):
        return f"[{self.status}] {self.material.name} - {self.message[:50]}"

    # =====================================================================
    # CORE METHODS
    # =====================================================================

    def resolve(self, user, notes=""):
        """Resolve this alert."""
        if self.status == self.Status.OPEN:
            self.status = self.Status.RESOLVED
            self.resolved_at = timezone.now()
            self.resolved_by = user
            if notes:
                self.resolution_notes = notes
            self.save()

    def ignore(self, user, notes=""):
        """Ignore this alert."""
        if self.status == self.Status.OPEN:
            self.status = self.Status.IGNORED
            self.resolved_at = timezone.now()
            self.resolved_by = user
            if notes:
                self.resolution_notes = notes
            self.save()

    @property
    def is_open(self) -> bool:
        """Check if alert is still open."""
        return self.status == self.Status.OPEN

    @property
    def is_resolved(self) -> bool:
        """Check if alert is resolved."""
        return self.status == self.Status.RESOLVED

    @classmethod
    def resolve_all_for_material(cls, material, user):
        """Resolve all open alerts for a material."""
        updated = cls.objects.filter(
            material=material,
            status=cls.Status.OPEN
        ).update(
            status=cls.Status.RESOLVED,
            resolved_at=timezone.now(),
            resolved_by=user,
        )
        return updated