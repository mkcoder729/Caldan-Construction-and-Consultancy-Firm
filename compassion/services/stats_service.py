"""
StatsService — 6 dynamic counters fed by the underlying models, all
cached for `CACHE_TTL_COMPASSION_STATS` seconds. Failures return 0
so the page never breaks (same pattern as website.context_processors.
trust_counter).
"""

import logging
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.core.cache import cache
from django.db.models import Count, Sum
from django.utils import timezone

logger = logging.getLogger(__name__)

CACHE_KEY_PREFIX = "compassion:stats"
DEFAULT_TTL = getattr(settings, "CACHE_TTL_COMPASSION_STATS", 300)


class StatsService:
    """Compute and cache the 6 compassion impact counters."""

    @classmethod
    def _cache_key(cls, name: str) -> str:
        return f"{CACHE_KEY_PREFIX}:{name}"

    @classmethod
    def _get(cls, name: str):
        try:
            return cache.get(cls._cache_key(name))
        except Exception as exc:
            logger.warning("Stats cache.get(%s) failed: %s", name, exc)
            return None

    @classmethod
    def _set(cls, name: str, value) -> None:
        try:
            cache.set(cls._cache_key(name), value, DEFAULT_TTL)
        except Exception as exc:
            logger.warning("Stats cache.set(%s) failed: %s", name, exc)

    # ────────── Individual counters ──────────

    @classmethod
    def people_served_12mo(cls) -> int:
        cached = cls._get("people_served_12mo")
        if cached is not None:
            return cached
        try:
            from compassion.models import OutreachStory
            cutoff = timezone.now().date() - timedelta(days=365)
            total = (
                OutreachStory.objects.filter(is_published=True, event_date__gte=cutoff)
                .aggregate(s=Sum("people_served"))
                .get("s")
                or 0
            )
            total = int(total)
        except Exception as exc:
            logger.exception("people_served_12mo failed: %s", exc)
            total = 0
        cls._set("people_served_12mo", total)
        return total

    @classmethod
    def meals_distributed(cls) -> int:
        """Approximate meals from delivered FOOD in-kind pledges.

        We parse the free-text `quantity_estimate` (e.g. '20kg maize',
        '50 meals', '2 bags') by extracting the leading integer. We
        deliberately keep this lossy — the goal is a directional
        counter, not a precise accounting measure.
        """
        cached = cls._get("meals_distributed")
        if cached is not None:
            return cached
        try:
            from compassion.models import InKindDonation
            pledges = InKindDonation.objects.filter(
                item_type=InKindDonation.ItemType.FOOD,
                status=InKindDonation.Status.DELIVERED,
            ).values_list("quantity_estimate", flat=True)

            total = 0
            import re
            num_re = re.compile(r"(\d+)")
            for raw in pledges:
                if not raw:
                    continue
                match = num_re.search(raw)
                if match:
                    total += int(match.group(1))
        except Exception as exc:
            logger.exception("meals_distributed failed: %s", exc)
            total = 0
        cls._set("meals_distributed", total)
        return total

    @classmethod
    def hospitals_visited(cls) -> int:
        cached = cls._get("hospitals_visited")
        if cached is not None:
            return cached
        try:
            from compassion.models import OutreachStory
            total = (
                OutreachStory.objects.filter(
                    is_published=True,
                    category=OutreachStory.Category.HOSPITAL,
                )
                .exclude(location="")
                .values("location")
                .distinct()
                .count()
            )
        except Exception as exc:
            logger.exception("hospitals_visited failed: %s", exc)
            total = 0
        cls._set("hospitals_visited", total)
        return total

    @classmethod
    def prison_visits(cls) -> int:
        cached = cls._get("prison_visits")
        if cached is not None:
            return cached
        try:
            from compassion.models import OutreachStory
            total = OutreachStory.objects.filter(
                is_published=True,
                category=OutreachStory.Category.PRISON,
            ).count()
        except Exception as exc:
            logger.exception("prison_visits failed: %s", exc)
            total = 0
        cls._set("prison_visits", total)
        return total

    @classmethod
    def donations_total_ksh(cls) -> Decimal:
        cached = cls._get("donations_total_ksh")
        if cached is not None:
            return Decimal(str(cached))
        try:
            from compassion.models import Donation
            total = (
                Donation.objects.filter(status=Donation.Status.SUCCESS)
                .aggregate(s=Sum("amount_ksh"))
                .get("s")
                or Decimal("0.00")
            )
        except Exception as exc:
            logger.exception("donations_total_ksh failed: %s", exc)
            total = Decimal("0.00")
        cls._set("donations_total_ksh", str(total))
        return total

    @classmethod
    def donations_count(cls) -> int:
        cached = cls._get("donations_count")
        if cached is not None:
            return cached
        try:
            from compassion.models import Donation
            total = Donation.objects.filter(status=Donation.Status.SUCCESS).count()
        except Exception as exc:
            logger.exception("donations_count failed: %s", exc)
            total = 0
        cls._set("donations_count", total)
        return total

    # ────────── Aggregate (used by context processor) ──────────

    @classmethod
    def get_all_stats(cls) -> dict:
        """Return all 6 counters in one shot, with internal per-key cache."""
        return {
            "compassion_people_served": cls.people_served_12mo(),
            "compassion_meals_distributed": cls.meals_distributed(),
            "compassion_hospitals_visited": cls.hospitals_visited(),
            "compassion_prison_visits": cls.prison_visits(),
            "compassion_donations_total_ksh": cls.donations_total_ksh(),
            "compassion_donations_count": cls.donations_count(),
        }