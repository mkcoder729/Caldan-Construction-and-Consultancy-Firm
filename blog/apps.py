from django.apps import AppConfig


class BlogConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'blog'

    def ready(self):
        # Import signal handlers so they register with Django's
        # signal dispatcher (fires when BlogPost is published).
        try:
            from blog import signals  # noqa: F401
        except Exception:
            pass
