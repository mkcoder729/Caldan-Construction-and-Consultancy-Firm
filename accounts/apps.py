"""
Accounts app configuration for Caldan Construction.

This module configures the accounts app and handles signal registration
for automatic profile creation and other user-related events.
"""

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class AccountsConfig(AppConfig):
    """
    Accounts app configuration.

    Features:
    - Automatic user profile creation via signals
    - App label for reverse lookups
    - Verbose name for admin interface
    """

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'
    label = 'accounts'
    verbose_name = _('Accounts & Authentication')

    def ready(self):
        """
        Import signals when app is ready.

        This method is called when Django loads the app.
        It ensures that all signal handlers are registered.
        """
        # Import signals to register them with Django's signal dispatcher
        # The signals.py file contains @receiver decorators that connect
        # signals to their handlers when this module is imported
        import accounts.signals  # noqa: F401

        # Initialize Cloudinary SDK from Django settings so CloudinaryField
        # uploads work without per-call configuration.
        try:
            import cloudinary
            from django.conf import settings as _s
            _cfg = getattr(_s, 'CLOUDINARY_STORAGE', {}) or {}
            if _cfg and not cloudinary.config().cloud_name:
                cloudinary.config(
                    cloud_name=_cfg.get('CLOUD_NAME') or _cfg.get('cloud_name'),
                    api_key=_cfg.get('API_KEY') or _cfg.get('api_key'),
                    api_secret=_cfg.get('API_SECRET') or _cfg.get('api_secret'),
                    secure=_cfg.get('SECURE', True),
                )
        except Exception:
            pass