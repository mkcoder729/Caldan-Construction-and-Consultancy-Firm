from django.apps import AppConfig


class WebsiteConfig(AppConfig):
    """Website app configuration for Caldan Construction public site."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "website"
    verbose_name = "Website"

    def ready(self) -> None:
        """Import signals when app is ready."""
        # No signals yet - reserved for future use
        pass