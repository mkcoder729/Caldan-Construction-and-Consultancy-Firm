"""
BackupRecord model for tracking project backups.
Caldan Construction - "Building Kenya's Future, One Project at a Time."
"""

from django.db import models
from django.conf import settings
from django.utils import timezone

from cloudinary.models import CloudinaryField


class BackupRecord(models.Model):
    """
    Model for tracking project backups.
    Stores backup file in Cloudinary with metadata.
    """

    # Project being backed up
    project = models.ForeignKey(
        'projects.Project',
        on_delete=models.CASCADE,
        related_name='backups'
    )

    # Backup file (Cloudinary)
    backup_file = CloudinaryField(
        'backup_file',
        folder='backups/',
        resource_type='auto',
        help_text='JSON backup file stored in Cloudinary'
    )

    # Metadata
    file_size = models.PositiveIntegerField(
        default=0,
        help_text='File size in bytes'
    )

    record_count = models.PositiveIntegerField(
        default=0,
        help_text='Total number of records backed up'
    )

    includes = models.JSONField(
        default=dict,
        help_text='List of included related data types'
    )

    # Notes
    notes = models.TextField(
        blank=True,
        default='',
        help_text='Optional notes about this backup'
    )

    # Version
    version = models.CharField(
        max_length=20,
        default='1.0.0',
        help_text='Backup format version'
    )

    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_backups'
    )

    # Restore tracking
    restored_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When this backup was restored'
    )

    restored_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='restored_backups'
    )

    # Deletion tracking (soft delete)
    is_deleted = models.BooleanField(
        default=False,
        db_index=True,
        help_text='Whether this backup has been soft-deleted'
    )

    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When this backup was deleted'
    )

    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='deleted_backups'
    )

    class Meta:
        db_table = 'backup_records'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['project', '-created_at']),
            models.Index(fields=['is_deleted']),
        ]

    def __str__(self):
        return f"Backup: {self.project.project_code} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"

    @property
    def file_url(self):
        """Get the Cloudinary URL for the backup file."""
        if self.backup_file:
            return self.backup_file.url
        return None

    def mark_restored(self, user):
        """Mark this backup as restored."""
        self.restored_at = timezone.now()
        self.restored_by = user
        self.save(update_fields=['restored_at', 'restored_by'])

    def soft_delete(self, user):
        """Soft delete this backup."""
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.deleted_by = user
        self.save(update_fields=['is_deleted', 'deleted_at', 'deleted_by'])

    def hard_delete(self):
        """Hard delete this backup (remove from Cloudinary and database)."""
        if self.backup_file:
            self.backup_file.delete()
        self.delete()