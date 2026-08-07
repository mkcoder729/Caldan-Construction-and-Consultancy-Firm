# Gallery Model - Caldan Construction
# "Building Kenya's Future, One Project at a Time."

from django.db import models
from django.conf import settings


class Gallery(models.Model):
    """Project gallery images - multiple photos per project."""

    # =====================================================================
    # RELATIONSHIPS
    # =====================================================================
    project = models.ForeignKey(
        'projects.Project',
        on_delete=models.CASCADE,
        related_name='gallery_images',
        help_text="Parent project"
    )

    # =====================================================================
    # MEDIA
    # =====================================================================
    image = models.ImageField(
        upload_to='projects/gallery/',
        help_text="Gallery image (Cloudinary)"
    )

    # =====================================================================
    # METADATA
    # =====================================================================
    caption = models.CharField(
        max_length=200,
        blank=True,
        default='',
        help_text="Image caption/description"
    )

    # =====================================================================
    # DISPLAY CONTROLS
    # =====================================================================
    is_primary = models.BooleanField(
        default=False,
        help_text="Use as cover/primary image"
    )
    display_order = models.PositiveSmallIntegerField(
        default=0,
        help_text="Display order"
    )

    # =====================================================================
    # TIMESTAMPS
    # =====================================================================
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='uploaded_gallery_images',
        help_text="User who uploaded this image"
    )

    class Meta:
        db_table = 'project_gallery'
        ordering = ['display_order', '-created_at']
        indexes = [
            models.Index(fields=['project', 'is_primary']),
            models.Index(fields=['display_order']),
        ]

    def __str__(self):
        return f"{self.project.name} - {self.caption or 'Image'}"

    def save(self, *args, **kwargs):
        """Ensure only one primary image per project."""
        if self.is_primary:
            # Set all other images to non-primary
            Gallery.objects.filter(
                project=self.project,
                is_primary=True
            ).exclude(id=self.id).update(is_primary=False)
        super().save(*args, **kwargs)