"""
Admin Invitation model for secure admin account creation.
Invitations are one-time use and expire after 48 hours.
"""

import secrets
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class AdminInvitation(models.Model):
    """
    Secure invitation for admin account creation.

    Features:
    - One-time use token
    - 48-hour expiration
    - Linked to inviter
    - Audit logging on creation/acceptance
    """

    email = models.EmailField(
        _('email'),
        unique=True,
        db_index=True,
        help_text=_('Email address to invite')
    )
    token = models.CharField(
        _('token'),
        max_length=64,
        unique=True,
        db_index=True,
        help_text=_('URL-safe token for invitation')
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sent_invitations',
        help_text=_('Admin who created the invitation')
    )
    created_at = models.DateTimeField(
        _('created at'),
        auto_now_add=True,
        help_text=_('Timestamp when invitation was created')
    )
    expires_at = models.DateTimeField(
        _('expires at'),
        help_text=_('Timestamp when invitation expires (48 hours from creation)')
    )
    accepted_at = models.DateTimeField(
        _('accepted at'),
        null=True,
        blank=True,
        help_text=_('Timestamp when invitation was accepted')
    )
    is_accepted = models.BooleanField(
        _('accepted'),
        default=False,
        db_index=True,
        help_text=_('Whether the invitation has been accepted')
    )
    accepted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='accepted_invitations',
        help_text=_('User who accepted the invitation')
    )

    # =====================================================================
    # RECRUITMENT DETAILS (collected up-front by the inviter)
    # =====================================================================
    full_name = models.CharField(
        _('full name'),
        max_length=150,
        blank=True,
        help_text=_('Optional full name collected when the invitation was sent')
    )
    phone = models.CharField(
        _('phone'),
        max_length=15,
        blank=True,
        help_text=_('Optional phone number for SMS delivery')
    )
    role = models.CharField(
        _('role'),
        max_length=20,
        blank=True,
        help_text=_('Requested admin role (e.g. PLATFORM_ADMIN)')
    )
    permissions_json = models.JSONField(
        _('initial permissions'),
        default=dict,
        blank=True,
        help_text=_('Initial permission toggles the chief wants to grant on acceptance')
    )
    personal_message = models.TextField(
        _('personal message'),
        blank=True,
        help_text=_('Optional note from the inviter shown in the invitation email')
    )

    # Auto-generated login password. Sent in the invitation email and
    # cleared on acceptance so it never lingers in the database after the
    # account has been claimed.
    temp_password = models.CharField(
        _('temporary password'),
        max_length=64,
        blank=True,
        help_text=_('Plaintext temporary password sent in the invitee email. '
                    'Cleared once the invitation is accepted.')
    )

    # =====================================================================
    # DELIVERY TIMESTAMPS (per channel)
    # =====================================================================
    email_sent_at = models.DateTimeField(
        _('email sent at'),
        null=True,
        blank=True,
        help_text=_('Timestamp when the invitation email was successfully sent')
    )
    sms_sent_at = models.DateTimeField(
        _('sms sent at'),
        null=True,
        blank=True,
        help_text=_('Timestamp when the invitation SMS was successfully sent')
    )

    # =====================================================================
    # META
    # =====================================================================
    class Meta:
        db_table = 'admin_invitations'
        verbose_name = _('admin invitation')
        verbose_name_plural = _('admin invitations')
        ordering = ('-created_at',)
        indexes = [
            models.Index(fields=['email', 'is_accepted'], name='inv_email_accepted_idx'),
            models.Index(fields=['-created_at'], name='inv_created_idx'),
        ]

    def __str__(self):
        """String representation."""
        return f"Invitation to {self.email} ({'accepted' if self.is_accepted else 'pending'})"

    # =====================================================================
    # SAVE OVERRIDE
    # =====================================================================

    def save(self, *args, **kwargs):
        """
        Override save to generate token and set expiry.
        """
        if not self.token:
            self.token = secrets.token_urlsafe(32)

        if not self.expires_at:
            self.expires_at = timezone.now() + timezone.timedelta(hours=48)

        super().save(*args, **kwargs)

    # =====================================================================
    # VALIDATION METHODS
    # =====================================================================

    def is_valid(self):
        """
        Check if invitation is still valid.

        Returns:
            bool: True if invitation is pending and not expired.
        """
        return not self.is_accepted and timezone.now() < self.expires_at

    def is_expired(self):
        """
        Check if invitation has expired.

        Returns:
            bool: True if invitation has expired.
        """
        return timezone.now() > self.expires_at

    def accept(self, user):
        """
        Mark invitation as accepted and clear the temporary password so
        it never lingers in the database after the account has been
        claimed.

        Args:
            user: The user who accepted the invitation.
        """
        self.is_accepted = True
        self.accepted_at = timezone.now()
        self.accepted_by = user
        self.temp_password = ''
        self.save(update_fields=['is_accepted', 'accepted_at', 'accepted_by', 'temp_password'])

    def get_absolute_url(self):
        """
        Get the full invitation URL.

        Returns:
            str: Full invitation URL.
        """
        from django.urls import reverse
        return f"/accept-invite/{self.token}/"

    def get_full_url(self, domain='caldanconstruction.com'):
        """
        Get the full invitation URL with domain.

        Args:
            domain (str): The domain to use.

        Returns:
            str: Full invitation URL.
        """
        return f"https://{domain}/accept-invite/{self.token}/"

