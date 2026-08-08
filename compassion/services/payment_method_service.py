"""
PaymentMethodService — read-mostly wrapper around the admin-managed
PaymentMethod rows. Caches the active list for the public page.
"""

import logging

from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

CACHE_KEY = "compassion:payment_methods:active"
DEFAULT_TTL = getattr(settings, "CACHE_TTL_COMPASSION_STATS", 300)


class PaymentMethodService:
    @classmethod
    def get_active(cls):
        """Return queryset of active payment methods, ordered for display."""
        from compassion.models import PaymentMethod
        try:
            cached = cache.get(CACHE_KEY)
        except Exception as exc:
            logger.warning("PaymentMethodService cache.get failed: %s", exc)
            cached = None
        if cached is not None:
            return cached
        try:
            qs = list(
                PaymentMethod.objects.filter(is_active=True).order_by(
                    "display_order", "method", "label"
                )
            )
            try:
                cache.set(CACHE_KEY, qs, DEFAULT_TTL)
            except Exception:
                pass
            return qs
        except Exception as exc:
            logger.exception("PaymentMethodService.get_active failed: %s", exc)
            return []