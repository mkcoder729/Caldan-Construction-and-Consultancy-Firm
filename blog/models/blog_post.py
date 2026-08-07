from django.db import models
from django.utils import timezone
from django.utils.text import slugify
from cloudinary.models import CloudinaryField


class BlogPost(models.Model):
    """
    Blog/News post model for Caldan Construction.

    This model stores all blog posts created by the admin.
    Posts can be published/unpublished and have a featured image.
    """

    # Core content
    title = models.CharField(max_length=200, db_index=True)
    slug = models.SlugField(unique=True, max_length=200, db_index=True)
    excerpt = models.TextField(max_length=500, blank=True, default="")
    content = models.TextField()

    # Media
    image = CloudinaryField(
        "image",
        folder="blog/",
        blank=True,
        null=True
    )

    # Categorisation — drives the filter pills on the public blog page.
    class Category(models.TextChoices):
        CONSTRUCTION = "construction", "Construction"
        CONSULTANCY  = "consultancy",  "Consultancy"
        NEWS         = "news",         "News"

    category = models.CharField(
        max_length=20,
        choices=Category.choices,
        default=Category.NEWS,
        db_index=True,
    )

    # Status
    is_published = models.BooleanField(default=False, db_index=True)
    published_at = models.DateTimeField(null=True, blank=True, db_index=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "blog_posts"
        ordering = ["-published_at", "-created_at"]
        indexes = [
            models.Index(fields=["is_published", "published_at"]),
            models.Index(fields=["is_published", "category", "published_at"]),
            models.Index(fields=["slug"]),
            models.Index(fields=["title"]),
        ]
        verbose_name = "Blog Post"
        verbose_name_plural = "Blog Posts"

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        """Auto-generate slug and set published_at."""
        if not self.slug:
            self.slug = slugify(self.title)

        # Auto-publish if marked published
        if self.is_published and not self.published_at:
            self.published_at = timezone.now()

        super().save(*args, **kwargs)

    @property
    def is_recent(self):
        """Check if post is from the last 7 days."""
        if not self.published_at:
            return False
        days_ago = (timezone.now() - self.published_at).days
        return days_ago <= 7

    @property
    def reading_time(self):
        """Estimate reading time in minutes."""
        words = len(self.content.split())
        minutes = words // 200
        return max(1, minutes)