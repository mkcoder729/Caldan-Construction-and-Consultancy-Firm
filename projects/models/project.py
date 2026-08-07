# Project Model - Caldan Construction
# "Building Kenya's Future, One Project at a Time."

from django.db import models
from django.utils import timezone
from django.conf import settings
from django.utils.text import slugify


class Project(models.Model):
    """Construction project model - Core entity for all operations."""

    class Status(models.TextChoices):
        PLANNING = 'PLANNING', 'Planning'
        ACTIVE = 'ACTIVE', 'Active'
        ON_HOLD = 'ON_HOLD', 'On Hold'
        COMPLETED = 'COMPLETED', 'Completed'
        ARCHIVED = 'ARCHIVED', 'Archived'

    # =====================================================================
    # IDENTITY FIELDS
    # =====================================================================
    name = models.CharField(
        max_length=200,
        db_index=True,
        help_text="Project name/title"
    )
    project_code = models.CharField(
        max_length=20,
        unique=True,
        db_index=True,
        help_text="Auto-generated: PRJ-YYYY-XXXX"
    )
    description = models.TextField(
        blank=True,
        default='',
        help_text="Detailed project description"
    )

    # =====================================================================
    # LOCATION FIELDS
    # =====================================================================
    location = models.CharField(
        max_length=200,
        help_text="Primary location/address"
    )
    county = models.CharField(
        max_length=100,
        db_index=True,
        help_text="Kenyan county"
    )
    town = models.CharField(
        max_length=100,
        db_index=True,
        help_text="Town/city"
    )
    estate = models.CharField(
        max_length=150,
        blank=True,
        default='',
        help_text="Estate/neighborhood"
    )

    # =====================================================================
    # GEOCODING FIELDS (For maps integration)
    # =====================================================================
    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        help_text="Latitude for map display"
    )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        help_text="Longitude for map display"
    )

    # =====================================================================
    # TIMELINE FIELDS
    # =====================================================================
    start_date = models.DateField(
        help_text="Project start date"
    )
    end_date = models.DateField(
        null=True,
        blank=True,
        help_text="Actual completion date"
    )
    estimated_completion = models.DateField(
        null=True,
        blank=True,
        help_text="Estimated completion date"
    )
    actual_completion = models.DateField(
        null=True,
        blank=True,
        help_text="Actual completion date"
    )

    # =====================================================================
    # BUDGET FIELDS (Denormalized from finances app)
    # =====================================================================
    budget = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        help_text="Total allocated budget (KES)"
    )
    spent = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        help_text="Total spent to date (KES)"
    )

    # =====================================================================
    # PROGRESS FIELDS
    # =====================================================================
    progress = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text="Overall progress percentage (0-100)"
    )

    # =====================================================================
    # STATUS FIELDS
    # =====================================================================
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PLANNING,
        db_index=True,
        help_text="Current project status"
    )

    # =====================================================================
    # SOFT DELETE FIELDS
    # =====================================================================
    is_archived = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Soft delete flag"
    )
    archived_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When project was archived"
    )

    # =====================================================================
    # RELATIONSHIPS
    # =====================================================================
    services = models.ManyToManyField(
        'services.Service',
        through='projects.ProjectServiceLink',
        related_name='projects',
        blank=True,
        help_text="Services used on this project"
    )

    # =====================================================================
    # MEDIA
    # =====================================================================
    cover_photo = models.ImageField(
        upload_to='projects/covers/',
        blank=True,
        null=True,
        help_text="Project cover image (Cloudinary)"
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
        related_name='created_projects',
        help_text="User who created this project"
    )

    class Meta:
        db_table = 'projects'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['county', 'town']),
            models.Index(fields=['is_archived']),
            models.Index(fields=['project_code']),
        ]

    def __str__(self):
        return f"{self.project_code} - {self.name}"

    # =====================================================================
    # CORE METHODS
    # =====================================================================

    def save(self, *args, **kwargs):
        """Auto-generate project code if not set."""
        if not self.project_code:
            self.project_code = self.generate_project_code()
        super().save(*args, **kwargs)

    def generate_project_code(self):
        """Generate unique project code: PRJ-2026-0001."""
        year = timezone.now().year
        count = Project.objects.filter(
            created_at__year=year
        ).count() + 1
        return f"PRJ-{year}-{count:04d}"

    def update_progress(self):
        """Calculate overall progress from milestones."""
        milestones = self.milestones.all()
        if not milestones:
            self.progress = 0
            self.save(update_fields=['progress'])
            return 0

        total_progress = sum(
            float(m.completion_percentage) for m in milestones
        )
        self.progress = round(total_progress / milestones.count(), 2)
        self.save(update_fields=['progress'])
        return self.progress

    def archive(self, user=None):
        """Soft delete - archive the project."""
        if self.status == self.Status.ARCHIVED:
            return

        self.status = self.Status.ARCHIVED
        self.is_archived = True
        self.archived_at = timezone.now()
        self.save()

        # Audit logging handled in service layer

    def restore(self):
        """Restore an archived project."""
        if not self.is_archived:
            return

        self.status = self.Status.PLANNING
        self.is_archived = False
        self.archived_at = None
        self.save()

    @property
    def days_active(self):
        """Calculate days since project started."""
        if not self.start_date:
            return 0
        end = self.actual_completion or timezone.now().date()
        return (end - self.start_date).days

    @property
    def remaining_budget(self):
        """Calculate remaining budget."""
        return self.budget - self.spent

    @property
    def budget_used_percentage(self):
        """Calculate budget used percentage."""
        if self.budget == 0:
            return 0
        return round((self.spent / self.budget) * 100, 2)

    @property
    def is_over_budget(self):
        """Check if project is over budget."""
        return self.spent > self.budget