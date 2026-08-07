# Projects App Config - Caldan Construction
# "Building Kenya's Future, One Project at a Time."

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class ProjectConfig(AppConfig):
    """Configuration for the Projects app."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'projects'
    verbose_name = _('Projects')

    def ready(self):
        """Import signals when app is ready."""
        try:
            import projects.signals  # noqa: F401
        except ImportError:
            pass