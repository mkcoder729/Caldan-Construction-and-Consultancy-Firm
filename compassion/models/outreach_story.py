"""
OutreachStory model — content for the public carousel + impact counter
sources. Admin-controlled. Each story falls into one of three categories:
HOSPITAL, PRISON, NEIGHBOURHOOD.

The public page renders only `is_published=True` stories. The
`cover_image` field is optional — the template falls back to a
branded SVG placeholder per category when empty.
"""

from django.db import models
from django.utils import timezone
from django.utils.text import slugify


class OutreachStory(models.Model):
    """A story from the field — hospital, prison, or neighbourhood outreach."""

    class Category(models.TextChoices):
        HOSPITAL = "HOSPITAL", "Hospital outreach"
        PRISON = "PRISON", "Prison ministry"
        NEIGHBOURHOOD = "NEIGHBOURHOOD", "Neighbourhood outreach"

    # ───── Content ─────
    title = models.CharField(max_length=200, verbose_name="Title")
    slug = models.SlugField(
        max_length=220,
        unique=True,
        blank=True,
        db_index=True,
        verbose_name="Slug",
        help_text="Auto-generated from title if left blank.",
    )
    category = models.CharField(
        max_length=14,
        choices=Category.choices,
        db_index=True,
        verbose_name="Category",
    )
    summary = models.TextField(verbose_name="Summary", help_text="1–3 sentence teaser shown on the carousel.")
    body = models.TextField(blank=True, default="", verbose_name="Full story", help_text="Optional long-form text.")

    # ───── Media ─────
    cover_image = models.ImageField(
        upload_to="compassion/stories/%Y/%m/",
        blank=True,
        default="",
        verbose_name="Cover image",
        help_text="Optional. Falls back to a branded SVG placeholder per category.",
    )

    # ───── Field metadata ─────
    location = models.CharField(max_length=200, blank=True, default="", verbose_name="Location")
    event_date = models.DateField(verbose_name="Event date")
    people_served = models.PositiveIntegerField(
        default=0,
        verbose_name="People served",
        help_text="Approximate count of people reached by this outreach.",
    )

    # ───── Display controls ─────
    is_published = models.BooleanField(default=False, db_index=True, verbose_name="Published")
    display_order = models.PositiveIntegerField(default=0, db_index=True, verbose_name="Display order")

    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "compassion_outreach_stories"
        ordering = ["display_order", "-event_date"]
        indexes = [
            models.Index(fields=["is_published", "category", "-event_date"]),
        ]
        verbose_name = "Outreach Story"
        verbose_name_plural = "Outreach Stories"

    def __str__(self) -> str:
        return f"{self.title} ({self.get_category_display()})"

    def save(self, *args, **kwargs):
        # Auto-slug from title if missing. We re-slug only on first save
        # (or when explicitly cleared) so editing the title later does NOT
        # break any external links pointing at the old slug.
        if not self.slug:
            base = slugify(self.title) or "story"
            slug = base
            counter = 1
            # Avoid collisions with other stories.
            while OutreachStory.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                counter += 1
                slug = f"{base}-{counter}"
            self.slug = slug
        super().save(*args, **kwargs)

    # ───── Template helpers ─────
    @property
    def placeholder_svg(self) -> str:
        """Return the static path to the category-specific SVG placeholder."""
        category = self.category.lower()
        return f"img/compassion/{category}-1.svg"

    def has_cover(self) -> bool:
        """True if a real cover image is uploaded."""
        return bool(self.cover_image)
