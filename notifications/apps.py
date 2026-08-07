"""
Notifications app configuration for Caldan Construction.

Wires up the post-save signal handlers that auto-create in-app
notifications (and email/SMS via the router) when key business
events occur — order placed, payment received, low stock.
"""

from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'notifications'
    verbose_name = 'Notifications & Alerts'

    def ready(self):
        """
        Import signal handlers. Importing the module connects the
        @receiver-decorated functions to Django's signal dispatcher.
        """
        # Importing the module is enough — signal registration happens
        # at import time via the @receiver decorator.
        try:
            from notifications import signals  # noqa: F401
        except ImportError:
            # Don't crash startup if a model is missing during a partial
            # bootstrap. The signals are best-effort.
            pass
