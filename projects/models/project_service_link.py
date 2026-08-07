# Project Service Link Model - Caldan Construction
# "Building Kenya's Future, One Project at a Time."

from django.db import models
from django.conf import settings


class ProjectServiceLink(models.Model):
    """Through model for Project-Service many-to-many relationship."""

    # =====================================================================
    # RELATIONSHIPS
    # =====================================================================
    project = models.ForeignKey(
        'projects.Project',
        on_delete=models.CASCADE,
        related_name='service_links',
        help_text="Project"
    )
    service = models.ForeignKey(
        'services.Service',
        on_delete=models.CASCADE,
        related_name='project_links',
        help_text="Service"
    )

    # =====================================================================
    # METADATA
    # =====================================================================
    notes = models.TextField(
        blank=True,
        default='',
        help_text="Notes about this service on this project"
    )
    is_primary_service = models.BooleanField(
        default=False,
        help_text="Is this the primary service for this project?"
    )

    # =====================================================================
    # TIMESTAMPS
    # =====================================================================
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_service_links',
        help_text="User who created this link"
    )

    class Meta:
        db_table = 'project_service_links'
        unique_together = ['project', 'service']
        indexes = [
            models.Index(fields=['project', 'service']),
            models.Index(fields=['is_primary_service']),
        ]

    def __str__(self):
        return f"{self.project.name} - {self.service.name}"

    def save(self, *args, **kwargs):
        """Ensure only one primary service per project."""
        if self.is_primary_service:
            ProjectServiceLink.objects.filter(
                project=self.project,
                is_primary_service=True
            ).exclude(id=self.id).update(is_primary_service=False)
        super().save(*args, **kwargs)