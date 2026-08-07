import logging
from django.db.models import Q
from django.utils import timezone
from blog.models.blog_post import BlogPost
from accounts.services.audit_service import AuditService

logger = logging.getLogger("caldan.blog")


class BlogService:
    """
    Service class for blog operations.

    All business logic for blog posts lives here.
    Views are thin — they only handle request/response and call services.
    """

    @classmethod
    def get_published_posts(cls):
        """
        Get all published blog posts ordered by published_at.

        Returns:
            QuerySet: Published BlogPost objects
        """
        return BlogPost.objects.filter(
            is_published=True,
            published_at__isnull=False
        ).order_by("-published_at")

    @classmethod
    def get_published_post_by_slug(cls, slug):
        """
        Get a single published post by slug.

        Args:
            slug (str): Blog post slug

        Returns:
            BlogPost or None: Published post or None if not found
        """
        try:
            return BlogPost.objects.get(
                slug=slug,
                is_published=True,
                published_at__isnull=False
            )
        except BlogPost.DoesNotExist:
            return None

    @classmethod
    def get_recent_posts(cls, limit=5):
        """
        Get recent published posts.

        Args:
            limit (int): Number of posts to return

        Returns:
            QuerySet: Recent published BlogPost objects
        """
        return cls.get_published_posts()[:limit]

    @classmethod
    def get_related_posts(cls, post, limit=3):
        """
        Get related posts based on title similarity.

        Args:
            post (BlogPost): Current post
            limit (int): Number of related posts to return

        Returns:
            QuerySet: Related BlogPost objects
        """
        # Simple related posts: exclude current, find similar by title keywords
        keywords = post.title.split()[:3]
        q_objects = Q()
        for keyword in keywords:
            if len(keyword) > 3:
                q_objects |= Q(title__icontains=keyword)

        related = BlogPost.objects.filter(
            is_published=True,
            published_at__isnull=False
        ).exclude(id=post.id)

        if q_objects:
            related = related.filter(q_objects)

        return related.order_by("-published_at")[:limit]

    @classmethod
    def search_posts(cls, query):
        """
        Search published posts by title or content.

        Args:
            query (str): Search query

        Returns:
            QuerySet: Matching BlogPost objects
        """
        return BlogPost.objects.filter(
            Q(is_published=True, published_at__isnull=False) &
            (Q(title__icontains=query) | Q(content__icontains=query) | Q(excerpt__icontains=query))
        ).order_by("-published_at")

    @classmethod
    def create_post(cls, user, data):
        """
        Create a new blog post.

        Args:
            user (User): User creating the post
            data (dict): Post data

        Returns:
            BlogPost: Created post
        """
        post = BlogPost.objects.create(
            title=data.get("title"),
            slug=data.get("slug") or None,
            excerpt=data.get("excerpt", ""),
            content=data.get("content"),
            image=data.get("image"),
            category=data.get("category") or BlogPost.Category.NEWS,
            is_published=data.get("is_published", False),
        )

        # Log audit
        AuditService.log_action(
            user=user,
            action="BLOG_POST_CREATED",
            entity_type="BlogPost",
            entity_id=post.id,
            details={
                "title": post.title,
                "slug": post.slug,
                "is_published": post.is_published
            }
        )

        logger.info(f"Blog post created: {post.title} by {user.email}")
        return post

    @classmethod
    def update_post(cls, user, post, data):
        """
        Update an existing blog post.

        Args:
            user (User): User updating the post
            post (BlogPost): Post to update
            data (dict): Updated data

        Returns:
            BlogPost: Updated post
        """
        # Track changes for audit
        changes = {}
        for field in ["title", "slug", "excerpt", "content", "category", "is_published"]:
            if field in data and getattr(post, field) != data[field]:
                changes[field] = {
                    "old": str(getattr(post, field)),
                    "new": str(data[field])
                }
                setattr(post, field, data[field])

        if "image" in data:
            changes["image"] = {"updated": True}
            post.image = data["image"]

        # If publishing, set published_at
        if data.get("is_published", False) and not post.published_at:
            post.published_at = timezone.now()
            changes["published_at"] = {"new": post.published_at.isoformat()}

        post.save()

        # Log audit
        AuditService.log_action(
            user=user,
            action="BLOG_POST_UPDATED",
            entity_type="BlogPost",
            entity_id=post.id,
            details={
                "title": post.title,
                "slug": post.slug,
                "changes": changes,
                "is_published": post.is_published
            }
        )

        logger.info(f"Blog post updated: {post.title} by {user.email}")
        return post

    @classmethod
    def delete_post(cls, user, post):
        """
        Delete a blog post.

        Args:
            user (User): User deleting the post
            post (BlogPost): Post to delete

        Returns:
            bool: True if deleted successfully
        """
        title = post.title
        slug = post.slug
        post_id = post.id

        post.delete()

        # Log audit
        AuditService.log_action(
            user=user,
            action="BLOG_POST_DELETED",
            entity_type="BlogPost",
            entity_id=post_id,
            details={
                "title": title,
                "slug": slug
            }
        )

        logger.info(f"Blog post deleted: {title} by {user.email}")
        return True

    @classmethod
    def toggle_publish(cls, user, post):
        """
        Toggle publish status of a blog post.

        Args:
            user (User): User toggling the post
            post (BlogPost): Post to toggle

        Returns:
            BlogPost: Updated post
        """
        post.is_published = not post.is_published

        if post.is_published and not post.published_at:
            post.published_at = timezone.now()
        elif not post.is_published:
            post.published_at = None

        post.save()

        # Log audit
        AuditService.log_action(
            user=user,
            action="BLOG_POST_TOGGLED",
            entity_type="BlogPost",
            entity_id=post.id,
            details={
                "title": post.title,
                "is_published": post.is_published,
                "published_at": post.published_at.isoformat() if post.published_at else None
            }
        )

        logger.info(f"Blog post toggled: {post.title} (published: {post.is_published}) by {user.email}")
        return post

    @classmethod
    def broadcast_to_subscribers(cls, user, post):
        """
        Manually re-broadcast a published blog post to all active newsletter
        subscribers. Use this when an already-published post has been
        materially updated and you want subscribers to see the change.

        The first-publish broadcast is handled automatically by the blog
        post_save signal — do NOT call this for a draft that was just
        published, or you'll send the broadcast twice.

        Args:
            user (User): Admin user pressing the "Email Subscribers" button.
            post (BlogPost): Post to broadcast. Must be published.

        Returns:
            dict: {sent: int, failed: int, total: int, skipped: bool}
        """
        if not post.is_published:
            return {"sent": 0, "failed": 0, "total": 0, "skipped": True,
                    "reason": "Post is not published; refusing to broadcast."}

        try:
            from website.models.newsletter import NewsletterSubscriber
            subscribers = list(
                NewsletterSubscriber.objects.filter(is_active=True)
                .values_list('email', flat=True)
            )
        except Exception:
            logger.exception("broadcast_to_subscribers: could not load subscribers.")
            return {"sent": 0, "failed": 0, "total": 0, "skipped": False,
                    "reason": "Could not load subscriber list."}

        if not subscribers:
            AuditService.log_action(
                user=user,
                action="BLOG_POST_BROADCAST",
                entity_type="BlogPost",
                entity_id=post.id,
                details={"title": post.title, "sent": 0, "total": 0,
                         "note": "no active subscribers"},
            )
            return {"sent": 0, "failed": 0, "total": 0, "skipped": False,
                    "reason": "No active subscribers."}

        try:
            from notifications.services.email_service import EmailService
            result = EmailService.send_newsletter_post(
                blog_post=post,
                subscribers=subscribers,
                user=user,
            )
        except Exception:
            logger.exception("broadcast_to_subscribers: send failed for post %s", post.id)
            AuditService.log_action(
                user=user,
                action="BLOG_POST_BROADCAST",
                entity_type="BlogPost",
                entity_id=post.id,
                details={"title": post.title, "error": "send_failed"},
            )
            return {"sent": 0, "failed": len(subscribers), "total": len(subscribers),
                    "skipped": False, "reason": "Email service raised."}

        AuditService.log_action(
            user=user,
            action="BLOG_POST_BROADCAST",
            entity_type="BlogPost",
            entity_id=post.id,
            details={
                "title": post.title,
                "slug": post.slug,
                "sent": result.get("sent", 0),
                "failed": result.get("failed", 0),
                "total": result.get("total", len(subscribers)),
            },
        )
        logger.info(
            "broadcast_to_subscribers: '%s' broadcast by %s — sent=%s failed=%s total=%s",
            post.title, user.email,
            result.get("sent"), result.get("failed"), result.get("total"),
        )
        return result

    @classmethod
    def get_admin_posts(cls, user=None):
        """
        Get all posts for admin view (including unpublished).

        Args:
            user (User, optional): User requesting posts

        Returns:
            QuerySet: All BlogPost objects
        """
        # Audit log for admin view (optional)
        if user:
            AuditService.log_action(
                user=user,
                action="BLOG_POSTS_VIEWED",
                entity_type="BlogPost",
                details={"view": "admin_list"}
            )

        return BlogPost.objects.all().order_by("-created_at")

    @classmethod
    def get_admin_post_by_id(cls, post_id, user=None):
        """
        Get a single post by ID for admin view.

        Args:
            post_id (int): Post ID
            user (User, optional): User requesting the post

        Returns:
            BlogPost: BlogPost object or None
        """
        try:
            post = BlogPost.objects.get(id=post_id)

            if user:
                AuditService.log_action(
                    user=user,
                    action="BLOG_POST_VIEWED",
                    entity_type="BlogPost",
                    entity_id=post.id,
                    details={"title": post.title}
                )

            return post
        except BlogPost.DoesNotExist:
            return None