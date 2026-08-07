"""
Signal handlers for the services app.

Currently used to invalidate cached service previews whenever services
are created, updated, or deleted. Keeps the footer/services-grid caches
fresh without relying solely on TTL expiry.
"""

import logging

from django.core.cache import cache
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models.service import Service

logger = logging.getLogger(__name__)

FOOTER_SERVICES_CACHE_KEY = "footer_services_preview"


@receiver(post_save, sender=Service)
@receiver(post_delete, sender=Service)
def invalidate_services_preview_cache(sender, instance, **kwargs):
    """Bust the footer/services preview cache when services change."""
    try:
        cache.delete(FOOTER_SERVICES_CACHE_KEY)
        logger.debug("Invalidated services preview cache")
    except Exception as exc:
        logger.warning("Failed to invalidate services preview cache: %s", exc)
