from django.db import models
from django.utils import timezone


class NewsletterSubscriber(models.Model):
    """Newsletter subscribers model."""

    email = models.EmailField(unique=True, db_index=True)
    is_active = models.BooleanField(default=True)
    subscribed_at = models.DateTimeField(auto_now_add=True)
    unsubscribed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "newsletter_subscribers"
        ordering = ["-subscribed_at"]
        indexes = [
            models.Index(fields=["email", "is_active"]),
            models.Index(fields=["is_active"]),
        ]
        verbose_name = "Newsletter Subscriber"
        verbose_name_plural = "Newsletter Subscribers"

    def __str__(self):
        return self.email

    def unsubscribe(self):
        """Unsubscribe this user from the newsletter."""
        self.is_active = False
        self.unsubscribed_at = timezone.now()
        self.save(update_fields=["is_active", "unsubscribed_at"])