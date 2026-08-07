"""
User Session model for tracking active sessions.
"""

from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class UserSession(models.Model):
    """
    Track active user sessions for security monitoring.

    Features:
    - Session tracking with device info
    - IP address and user agent logging
    - Session expiry and cleanup
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sessions',
        help_text=_('The user this session belongs to')
    )
    session_key = models.CharField(
        _('session key'),
        max_length=40,
        unique=True,
        db_index=True,
        help_text=_('Django session key')
    )
    ip_address = models.GenericIPAddressField(
        _('IP address'),
        help_text=_('Client IP address')
    )
    user_agent = models.TextField(
        _('user agent'),
        blank=True,
        default='',
        help_text=_('Client user agent string')
    )
    device_name = models.CharField(
        _('device name'),
        max_length=100,
        blank=True,
        default='',
        help_text=_('Human-readable device name')
    )
    is_active = models.BooleanField(
        _('active'),
        default=True,
        db_index=True,
        help_text=_('Whether this session is still active')
    )
    created_at = models.DateTimeField(
        _('created at'),
        default=timezone.now,
        db_index=True,
        help_text=_('Session creation timestamp')
    )
    expires_at = models.DateTimeField(
        _('expires at'),
        help_text=_('Session expiry timestamp')
    )
    last_activity = models.DateTimeField(
        _('last activity'),
        default=timezone.now,
        help_text=_('Last activity timestamp')
    )

    # =====================================================================
    # META
    # =====================================================================
    class Meta:
        db_table = 'user_sessions'
        verbose_name = _('user session')
        verbose_name_plural = _('user sessions')
        ordering = ('-last_activity',)
        indexes = [
            models.Index(fields=['user', '-last_activity'], name='session_user_activity_idx'),
            models.Index(fields=['is_active', '-last_activity'], name='session_active_idx'),
        ]

    def __str__(self):
        """String representation."""
        return f"Session for {self.user.email} ({self.ip_address})"

    # =====================================================================
    # SAVE OVERRIDE
    # =====================================================================

    def save(self, *args, **kwargs):
        """Set default expiry if not provided."""
        if not self.expires_at:
            self.expires_at = timezone.now() + timezone.timedelta(hours=24)
        super().save(*args, **kwargs)

    # =====================================================================
    # VALIDATION METHODS
    # =====================================================================

    def is_expired(self):
        """
        Check if session has expired.

        Returns:
            bool: True if session has expired.
        """
        return timezone.now() > self.expires_at

    def extend(self, hours=24):
        """
        Extend session expiry.

        Args:
            hours (int): Number of hours to extend.
        """
        self.expires_at = timezone.now() + timezone.timedelta(hours=hours)
        self.last_activity = timezone.now()
        self.save(update_fields=['expires_at', 'last_activity'])

    def deactivate(self):
        """Deactivate this session."""
        self.is_active = False
        self.save(update_fields=['is_active'])

    # =====================================================================
    # CLEANUP
    # =====================================================================

    @classmethod
    def cleanup_expired(cls):
        """
        Delete or deactivate expired sessions.

        Returns:
            int: Number of sessions cleaned.
        """
        expired = cls.objects.filter(expires_at__lt=timezone.now())
        count = expired.count()
        expired.delete()
        return count