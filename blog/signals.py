"""Blog signal handlers.

When a BlogPost is saved with is_published=True, we fire:

1. Every admin (chief → superuser → platform admin) gets an in-app
   Notification + email (via NotificationRouter -> email/notification.html)
   so the bell lights up and the team knows about the post.
2. Every active newsletter subscriber gets the marketing broadcast via
   EmailService.send_newsletter_post().

This fires on every save where the post is published — first publish,
content edits, image swaps, etc. — so any save you make is reflected in
your subscribers' inboxes.
"""

import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from blog.models.blog_post import BlogPost

logger = logging.getLogger('caldan.blog')


@receiver(post_save, sender=BlogPost)
def blog_post_published(sender, instance, created, update_fields=None, **kwargs):
    """React to a BlogPost save where is_published is True.

    Fires on every save (create, edit, toggle) of a published post. Drafts
    do not broadcast. The admin notification fires alongside the
    subscriber broadcast so the dashboard bell lights up too.
    """
    if not instance.is_published:
        return

    # Admin bell + email (per-admin fan-out)
    try:
        from notifications.services.router_service import NotificationRouter
        NotificationRouter.route_blog_post_published(instance)
    except Exception:
        logger.exception("blog_post_published: failed to route admin notification.")

    # Subscriber broadcast — every active subscriber
    try:
        from website.models.newsletter import NewsletterSubscriber
        subscribers = list(
            NewsletterSubscriber.objects.filter(is_active=True)
            .values_list('email', flat=True)
        )
        if not subscribers:
            logger.info("blog_post_published: no active newsletter subscribers, skipping broadcast.")
            return
        from notifications.services.email_service import EmailService
        result = EmailService.send_newsletter_post(
            blog_post=instance,
            subscribers=subscribers,
            user=None,
        )
        logger.info(
            "blog_post_published: broadcast for '%s' — %s",
            instance.title, result,
        )
    except Exception:
        logger.exception("blog_post_published: failed to send newsletter broadcast.")
