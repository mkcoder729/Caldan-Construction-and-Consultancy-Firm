"""
Signal handlers that bust the compassion stats cache on every model
change. Wired up in compassion/apps.py → CompassionConfig.ready().
"""

import logging

from django.core.cache import cache
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)


def _bust_all_stats_cache():
    """Drop every cache key under the compassion stats prefix.

    We use cache.delete_pattern on Redis (django-redis supports it),
    and fall back to per-key delete on engines that don't.
    """
    keys = [
        "compassion:stats:people_served_12mo",
        "compassion:stats:meals_distributed",
        "compassion:stats:hospitals_visited",
        "compassion:stats:prison_visits",
        "compassion:stats:donations_total_ksh",
        "compassion:stats:donations_count",
        "compassion:ministry_settings:solo",
        "compassion:payment_methods:active",
    ]
    for k in keys:
        try:
            cache.delete(k)
        except Exception as exc:
            logger.warning("Cache bust failed for %s: %s", k, exc)


# We use dispatch_uid so Django can de-dup signal connections across
# app reloads (manage.py runserver reloads the module on every save).
def _on_any_change(sender, instance, **kwargs):
    _bust_all_stats_cache()


def _on_any_delete(sender, instance, **kwargs):
    _bust_all_stats_cache()


# Wire up handlers — we import the models inside the function so that
# app loading order doesn't break.
def _connect():
    from .models import Donation, InKindDonation, MinistrySettings, OutreachStory, PaymentMethod, ScheduleCall
    models_to_watch = [
        (Donation, "donation"),
        (InKindDonation, "inkind"),
        (ScheduleCall, "schedule_call"),
        (OutreachStory, "outreach_story"),
        (MinistrySettings, "ministry_settings"),
        (PaymentMethod, "payment_method"),
    ]
    for model, slug in models_to_watch:
        post_save.connect(_on_any_change, sender=model, dispatch_uid=f"compassion_stats_save_{slug}")
        post_delete.connect(_on_any_delete, sender=model, dispatch_uid=f"compassion_stats_del_{slug}")


# Connect on import (apps.py:ready() imports this module).
_connect()
