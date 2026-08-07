from django.apps import AppConfig


class ServicesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "services"
    verbose_name = "Services"

    def ready(self) -> None:
        # Register signal handlers (cache invalidation for services preview).
        from . import signals  # noqa: F401
