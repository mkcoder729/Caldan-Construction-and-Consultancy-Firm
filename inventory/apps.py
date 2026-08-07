"""
Inventory App Configuration.

Registers the inventory app and loads signals on startup.
"""

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class InventoryConfig(AppConfig):
    """Configuration for the inventory app."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'inventory'
    verbose_name = _('Inventory Management')

    def ready(self):
        """
        Import signals when app is ready.

        This ensures all signal handlers are registered when the app starts.
        """
        import inventory.signals

        # Validate configuration
        from django.conf import settings
        if not hasattr(settings, 'CLOUDINARY_STORAGE'):
            import logging
            logger = logging.getLogger('caldan.inventory')
            logger.warning(
                'Cloudinary storage not configured. Receipt uploads will use local storage.'
            )

        if not hasattr(settings, 'REDIS_URL'):
            logger = logging.getLogger('caldan.inventory')
            logger.warning(
                'Redis not configured. Background tasks may not work properly.'
            )