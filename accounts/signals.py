"""
Signals for the accounts app.

This module handles automatic actions like creating user profiles
when a user is created.
"""

import logging
from django.db.models.signals import post_save
from django.dispatch import receiver

from accounts.models import User, Profile

logger = logging.getLogger('caldan')


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Create a UserProfile automatically when a User is created.

    Permissions are NOT initialised here — the chief's choices on the
    invitation form are the authoritative set. If the chief grants a
    permission during invitation, ``accept_invitation`` flips it on;
    everything else stays off, so the sidebar reflects exactly what
    the chief decided. For chief/superuser admins the sidebar short-
    circuits at the context processor so this doesn't matter.
    For all users, this creates the profile with default preferences.
    """
    if created:
        Profile.objects.create(user=instance)
        logger.info(f"Profile created for user: {instance.email}")