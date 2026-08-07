from django.apps import AppConfig


class ShopConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'shop'
    verbose_name = 'Online Shop'

    def ready(self):
        """Import signals when app is ready."""
        try:
            import shop.signals  # noqa
        except ImportError:
            pass