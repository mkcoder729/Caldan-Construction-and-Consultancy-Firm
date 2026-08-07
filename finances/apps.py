from django.apps import AppConfig


class FinancesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'finances'
    verbose_name = 'Financial Management'

    def ready(self):
        """Import signals when app is ready."""
        try:
            import finances.signals  # noqa
        except ImportError:
            pass