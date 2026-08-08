"""
CompassionAppConfig — registers the 'compassion' app and wires signals.
"""

from django.apps import AppConfig


class CompassionConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "compassion"
    verbose_name = "Caldan Compassionate Ministry"

    def ready(self) -> None:
        # Import signal handlers so they wire up at startup. Local import to
        # avoid circular import issues during app loading.
        try:
            from . import signals  # noqa: F401
        except Exception:  # pragma: no cover
            # Don't crash the app if signals can't load — log and move on.
            import logging
            logging.getLogger(__name__).warning(
                "compassion.signals could not be imported; cache invalidation may not run."
            )
