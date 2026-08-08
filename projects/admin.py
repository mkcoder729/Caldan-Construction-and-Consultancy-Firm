# Projects Admin - Caldan Construction
# "Building Kenya's Future, One Project at a Time."

from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone

from projects.models import Project, Milestone, Gallery, ProjectServiceLink


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    """Admin interface for Project model."""

    list_display = [
        'project_code',
        'name',
        'is_featured',
        'status',
        'county',
        'budget_display',
        'progress_display',
        'created_at',
    ]
    list_filter = [
        'is_featured',
        'status',
        'county',
        'is_archived',
        'created_at',
    ]
    search_fields = [
        'name',
        'project_code',
        'location',
        'county',
        'town',
    ]
    readonly_fields = [
        'project_code',
        'created_at',
        'updated_at',
        'progress',
    ]
    fieldsets = (
        ('Identity', {
            'fields': ('project_code', 'name', 'description')
        }),
        ('Location', {
            'fields': ('location', 'county', 'town', 'estate', 'latitude', 'longitude')
        }),
        ('Timeline', {
            'fields': ('start_date', 'end_date', 'estimated_completion', 'actual_completion')
        }),
        ('Budget & Progress', {
            'fields': ('budget', 'spent', 'progress', 'status')
        }),
        ('Metadata', {
            'fields': ('is_archived', 'archived_at', 'created_by', 'created_at', 'updated_at')
        }),
        ('Media', {
            'fields': ('cover_photo',)
        }),
        ('Display', {
            'fields': ('is_featured',),
            'description': 'Toggle on to feature this project in the public /projects/ spotlight section (max 3 recommended).'
        }),
    )
    ordering = ['-created_at']
    date_hierarchy = 'created_at'

    def budget_display(self, obj):
        """Display budget with KES format."""
        return f"KES {obj.budget:,.2f}" if obj.budget else "KES 0.00"
    budget_display.short_description = 'Budget'

    def progress_display(self, obj):
        """Display progress with percentage."""
        return f"{obj.progress:.1f}%"
    progress_display.short_description = 'Progress'


@admin.register(Milestone)
class MilestoneAdmin(admin.ModelAdmin):
    """Admin interface for Milestone model."""

    list_display = [
        'title',
        'project_link',
        'status',
        'target_date',
        'completion_percentage',
        'created_at',
    ]
    list_filter = [
        'status',
        'project',
        'target_date',
    ]
    search_fields = ['title', 'description']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['project', 'order', 'target_date']
    date_hierarchy = 'target_date'

    def project_link(self, obj):
        """Link to project admin."""
        url = f"/admin/projects/project/{obj.project.id}/change/"
        return format_html('<a href="{}">{}</a>', url, obj.project.project_code)
    project_link.short_description = 'Project'


@admin.register(Gallery)
class GalleryAdmin(admin.ModelAdmin):
    """Admin interface for Gallery model."""

    list_display = [
        'project_link',
        'caption_preview',
        'is_primary',
        'display_order',
        'created_at',
    ]
    list_filter = ['is_primary', 'project']
    search_fields = ['caption']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['project', 'display_order']

    def project_link(self, obj):
        """Link to project admin."""
        url = f"/admin/projects/project/{obj.project.id}/change/"
        return format_html('<a href="{}">{}</a>', url, obj.project.project_code)
    project_link.short_description = 'Project'

    def caption_preview(self, obj):
        """Truncated caption."""
        return obj.caption[:50] + '...' if len(obj.caption) > 50 else obj.caption
    caption_preview.short_description = 'Caption'


@admin.register(ProjectServiceLink)
class ProjectServiceLinkAdmin(admin.ModelAdmin):
    """Admin interface for Project-Service link."""

    list_display = [
        'project_link',
        'service_link',
        'is_primary_service',
        'created_at',
    ]
    list_filter = ['is_primary_service', 'project', 'service']
    search_fields = ['notes']
    readonly_fields = ['created_at', 'updated_at']

    def project_link(self, obj):
        """Link to project admin."""
        url = f"/admin/projects/project/{obj.project.id}/change/"
        return format_html('<a href="{}">{}</a>', url, obj.project.project_code)
    project_link.short_description = 'Project'

    def service_link(self, obj):
        """Link to service admin."""
        url = f"/admin/services/service/{obj.service.id}/change/"
        return format_html('<a href="{}">{}</a>', url, obj.service.name)
    service_link.short_description = 'Service'