"""
MinistryService — wraps the MinistrySettings singleton with a cached
lookup so we don't hit the DB on every page render.
"""

import logging

from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

CACHE_KEY = "compassion:ministry_settings:solo"
DEFAULT_TTL = getattr(settings, "CACHE_TTL_COMPASSION_STATS", 300)


class MinistryService:
    """Read-mostly wrapper around the MinistrySettings singleton."""

    @classmethod
    def get_solo(cls):
        """Return the singleton MinistrySettings row, creating if missing."""
        from compassion.models import MinistrySettings
        try:
            cached = cache.get(CACHE_KEY)
        except Exception as exc:
            logger.warning("MinistryService cache.get failed: %s", exc)
            cached = None
        if cached is not None:
            return cached
        try:
            obj = MinistrySettings.get_solo()
            try:
                cache.set(CACHE_KEY, obj, DEFAULT_TTL)
            except Exception:
                pass
            return obj
        except Exception as exc:
            logger.exception("MinistryService.get_solo failed: %s", exc)
            # Return an unsaved instance with defaults so templates still
            # render even if the DB is unreachable.
            return MinistrySettings()