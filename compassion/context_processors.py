"""
Context processor that injects the 6 compassion impact counters into
every public template.

Mirrors the trust_counter / project_stats / services_preview pattern
in website/context_processors.py — try cache.get → fall through to
DB on miss → cache.set with TTL → return 0 on any exception.

The cache key prefix `compassion:stats:` is busted by signals on
every Donation / InKindDonation / ScheduleCall / OutreachStory save.
"""

import logging
from decimal import Decimal

from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

CACHE_KEY_PREFIX = "compassion:stats"
DEFAULT_TTL = getattr(settings, "CACHE_TTL_COMPASSION_STATS", 300)


def _get(key: str):
    try:
        return cache.get(key)
    except Exception as exc:
        logger.warning("compassion_stats cache.get(%s) failed: %s", key, exc)
        return None


def _set(key: str, value, ttl: int = DEFAULT_TTL):
    try:
        cache.set(key, value, ttl)
    except Exception as exc:
        logger.warning("compassion_stats cache.set(%s) failed: %s", key, exc)


def compassion_stats(request):
    """Inject the 6 dynamic counters.

    Returns:
        dict with keys:
            compassion_people_served, compassion_meals_distributed,
            compassion_hospitals_visited, compassion_prison_visits,
            compassion_donations_total_ksh, compassion_donations_count
    """
    out = {
        "compassion_people_served": 0,
        "compassion_meals_distributed": 0,
        "compassion_hospitals_visited": 0,
        "compassion_prison_visits": 0,
        "compassion_donations_total_ksh": Decimal("0.00"),
        "compassion_donations_count": 0,
    }

    # Local import to avoid app-loading-order surprises at startup.
    try:
        from .services.stats_service import StatsService
        stats = StatsService.get_all_stats()
        out.update(stats)
    except Exception as exc:
        logger.exception("compassion_stats failed: %s", exc)
        # fall through with defaults

    return out
