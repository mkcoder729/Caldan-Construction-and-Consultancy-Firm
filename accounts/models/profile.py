from django.db import models
from django.conf import settings


class Profile(models.Model):
    """User profile model for extended user data."""

    class Theme(models.TextChoices):
        LIGHT = 'light', 'Light'
        DARK = 'dark', 'Dark'
        DEVICE = 'device', 'Device Default'

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile'
    )

    # Theme preference
    theme = models.CharField(max_length=10, choices=Theme.choices, default=Theme.LIGHT)

    # Permissions (JSON field for admin permissions)
    permissions = models.JSONField(default=dict, blank=True)

    # Notification preferences
    preferences = models.JSONField(default=dict, blank=True)

    # Avatar
    avatar = models.ImageField(upload_to='profiles/avatars/', blank=True, null=True)

    # Bio
    bio = models.TextField(blank=True, default='')

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'profiles'

    def __str__(self):
        return f"Profile for {self.user.email}"

    def get_permission(self, permission_name, default=False):
        """Get a specific permission value."""
        return self.permissions.get(permission_name, default)

    def set_permission(self, permission_name, value):
        """Set a specific permission value."""
        self.permissions[permission_name] = value
        self.save(update_fields=['permissions'])

    def get_preference(self, key, default=None):
        """Get a specific preference value."""
        return self.preferences.get(key, default)

    def set_preference(self, key, value):
        """Set a specific preference value."""
        self.preferences[key] = value
        self.save(update_fields=['preferences'])