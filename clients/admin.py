"""
Admin configuration for Clients app.
Caldan Construction - "Building Kenya's Future, One Project at a Time."
"""

from django.contrib import admin
from django.utils.html import format_html

from clients.models import Client


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    """Admin configuration for Client model."""

    list_display = (
        'name',
        'email',
        'phone',
        'type_display',
        'status_display',
        'source',
        'project_count',
        'created_at',
    )
    list_filter = ('type', 'status', 'source', 'created_at')
    search_fields = ('name', 'email', 'phone', 'company_name', 'notes')
    readonly_fields = ('created_at', 'updated_at', 'last_contact')
    ordering = ('-created_at',)

    fieldsets = (
        ('Identity', {
            'fields': ('name', 'type', 'company_name')
        }),
        ('Contact', {
            'fields': ('email', 'phone', 'alternative_phone')
        }),
        ('Address', {
            'fields': ('address', 'county', 'town'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('status', 'source', 'notes')
        }),
        ('Relationships', {
            'fields': ('projects', 'orders'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at', 'last_contact'),
            'classes': ('collapse',)
        }),
    )

    def type_display(self, obj):
        """Display type with nice formatting."""
        return obj.get_type_display()
    type_display.short_description = 'Type'

    def status_display(self, obj):
        """Display status with color coding."""
        colors = {
            'LEAD': '#95A5A6',
            'ACTIVE': '#27AE60',
            'INACTIVE': '#B9342B',
            'CONVERTED': '#0B66C3',
        }
        color = colors.get(obj.status, '#95A5A6')
        return format_html(
            '<span style="background: {}; color: white; padding: 2px 10px; border-radius: 4px; font-size: 0.7rem; font-weight: 600;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_display.short_description = 'Status'

    def project_count(self, obj):
        """Display number of linked projects."""
        count = obj.projects.count()
        return format_html(
            '<a href="/admin/projects/project/?clients__id={}">{}</a>',
            obj.id,
            count
        )
    project_count.short_description = 'Projects'

    def get_queryset(self, request):
        """Optimize queryset with prefetch_related."""
        return super().get_queryset(request).prefetch_related('projects')