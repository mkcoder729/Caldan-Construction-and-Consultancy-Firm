# Milestone Model - Caldan Construction
# "Building Kenya's Future, One Project at a Time."

from django.db import models
from django.utils import timezone
from django.conf import settings


class Milestone(models.Model):
    """Project milestone - tracks key project phases."""

    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        IN_PROGRESS = 'IN_PROGRESS', 'In Progress'
        COMPLETED = 'COMPLETED', 'Completed'
        OVERDUE = 'OVERDUE', 'Overdue'

    # =====================================================================
    # RELATIONSHIPS
    # =====================================================================
    project = models.ForeignKey(
        'projects.Project',
        on_delete=models.CASCADE,
        related_name='milestones',
        help_text="Parent project"
    )

    # =====================================================================
    # IDENTITY FIELDS
    # =====================================================================
    title = models.CharField(
        max_length=200,
        help_text="Milestone title/name"
    )
    description = models.TextField(
        blank=True,
        default='',
        help_text="Detailed milestone description"
    )

    # =====================================================================
    # DATE FIELDS
    # =====================================================================
    target_date = models.DateField(
        help_text="Target completion date"
    )
    completed_date = models.DateField(
        null=True,
        blank=True,
        help_text="Actual completion date"
    )

    # =====================================================================
    # PROGRESS FIELDS
    # =====================================================================
    completion_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text="Completion percentage (0-100)"
    )

    # =====================================================================
    # STATUS FIELDS
    # =====================================================================
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
        help_text="Current milestone status"
    )

    # =====================================================================
    # MEDIA
    # =====================================================================
    photo = models.ImageField(
        upload_to='projects/milestones/',
        blank=True,
        null=True,
        help_text="Milestone evidence photo (Cloudinary)"
    )

    # =====================================================================
    # NOTES & ORDER
    # =====================================================================
    notes = models.TextField(
        blank=True,
        default='',
        help_text="Additional notes"
    )
    order = models.PositiveSmallIntegerField(
        default=0,
        help_text="Display order"
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
        related_name='created_milestones',
        help_text="User who created this milestone"
    )

    class Meta:
        db_table = 'project_milestones'
        ordering = ['order', 'target_date']
        indexes = [
            models.Index(fields=['project', 'status']),
            models.Index(fields=['target_date']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"

    # =====================================================================
    # CORE METHODS
    # =====================================================================

    def save(self, *args, **kwargs):
        """Auto-update status based on completion and target date."""
        # Update status based on completion
        if self.completion_percentage >= 100:
            self.status = self.Status.COMPLETED
            if not self.completed_date:
                self.completed_date = timezone.now().date()

        # Check if overdue
        elif self.target_date and timezone.now().date() > self.target_date:
            if self.status != self.Status.COMPLETED:
                self.status = self.Status.OVERDUE

        # If completion is between 1-99% and not overdue
        elif self.completion_percentage > 0 and self.completion_percentage < 100:
            if self.status not in [self.Status.COMPLETED, self.Status.OVERDUE]:
                self.status = self.Status.IN_PROGRESS

        super().save(*args, **kwargs)

        # Update parent project progress
        self.project.update_progress()

    def mark_complete(self, user=None):
        """Mark milestone as complete."""
        self.completion_percentage = 100
        self.completed_date = timezone.now().date()
        self.status = self.Status.COMPLETED
        self.save()
        return self

    def update_progress(self, percentage, user=None):
        """Update milestone progress."""
        self.completion_percentage = min(max(percentage, 0), 100)
        self.save()
        return self

    @property
    def is_overdue(self):
        """Check if milestone is overdue."""
        if self.completed_date:
            return False
        return timezone.now().date() > self.target_date

    @property
    def days_until_target(self):
        """Calculate days until target date."""
        if not self.target_date:
            return None
        delta = self.target_date - timezone.now().date()
        return delta.days

    @property
    def days_overdue(self):
        """Calculate days overdue if applicable."""
        if not self.is_overdue:
            return 0
        delta = timezone.now().date() - self.target_date
        return delta.days