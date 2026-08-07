"""
TeamMember model for team profiles.
Caldan Construction - "Building Kenya's Future, One Project at a Time."
"""

from django.db import models
from django.utils import timezone
from django.core.validators import URLValidator


class TeamMember(models.Model):
    """
    Team member profile model.
    Stores individual team member information for public display.
    """

    class Role(models.TextChoices):
        DIRECTOR = 'DIRECTOR', 'Director'
        MANAGER = 'MANAGER', 'Manager'
        ENGINEER = 'ENGINEER', 'Engineer'
        SUPERVISOR = 'SUPERVISOR', 'Supervisor'
        ADMIN = 'ADMIN', 'Administration'
        OTHER = 'OTHER', 'Other'

    # Basic Information
    name = models.CharField(
        max_length=150,
        db_index=True,
        help_text='Full name of the team member'
    )

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        db_index=True,
        help_text='Primary role in the company'
    )

    title = models.CharField(
        max_length=100,
        blank=True,
        default='',
        help_text='Job title (e.g., Lead Architect)'
    )

    bio = models.TextField(
        blank=True,
        default='',
        help_text='Biography or description of the team member'
    )

    # Photo
    photo = models.ImageField(
        upload_to='team/',
        blank=True,
        null=True,
        help_text='Profile photo (recommended: square, max 5MB)'
    )

    # Contact (optional, for internal use)
    email = models.EmailField(
        blank=True,
        default='',
        help_text='Email address (optional, for internal use)'
    )

    phone = models.CharField(
        max_length=15,
        blank=True,
        default='',
        help_text='Phone number (optional, for internal use)'
    )

    # Display Settings
    display_order = models.PositiveSmallIntegerField(
        default=0,
        db_index=True,
        help_text='Lower numbers appear first'
    )

    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text='Whether this member is active and visible'
    )

    is_featured = models.BooleanField(
        default=False,
        db_index=True,
        help_text='Whether this member appears on the public About page'
    )

    # Social Links
    linkedin = models.URLField(
        blank=True,
        default='',
        validators=[URLValidator()],
        help_text='LinkedIn profile URL'
    )

    twitter = models.URLField(
        blank=True,
        default='',
        validators=[URLValidator()],
        help_text='Twitter/X profile URL'
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'team_members'
        ordering = ['display_order', 'name']
        indexes = [
            models.Index(fields=['role', 'is_active']),
            models.Index(fields=['is_featured', 'is_active']),
            models.Index(fields=['display_order']),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_role_display()})"

    @property
    def display_name(self):
        """Get the display name with role."""
        return f"{self.name} - {self.get_role_display()}"

    @property
    def has_social_links(self):
        """Check if the member has any social links."""
        return bool(self.linkedin or self.twitter)

    @property
    def has_contact_info(self):
        """Check if the member has any contact info."""
        return bool(self.email or self.phone)

    def get_photo_url(self):
        """Get the photo URL or None."""
        if self.photo:
            return self.photo.url
        return None