"""
Admin configuration for Team app.
Caldan Construction - "Building Kenya's Future, One Project at a Time."
"""

from django.contrib import admin
from django.utils.html import format_html

from team.models import TeamMember


@admin.register(TeamMember)
class TeamMemberAdmin(admin.ModelAdmin):
    """Admin configuration for TeamMember model."""

    list_display = (
        'name',
        'role_display',
        'title',
        'display_order',
        'is_active',
        'is_featured',
        'photo_preview',
    )
    list_filter = ('role', 'is_active', 'is_featured')
    search_fields = ('name', 'title', 'email', 'phone')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('display_order', 'name')

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'role', 'title', 'bio', 'photo')
        }),
        ('Contact Details', {
            'fields': ('email', 'phone'),
            'classes': ('collapse',)
        }),
        ('Display Settings', {
            'fields': ('display_order', 'is_active', 'is_featured')
        }),
        ('Social Links', {
            'fields': ('linkedin', 'twitter'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def role_display(self, obj):
        """Display role with nice formatting."""
        return obj.get_role_display()
    role_display.short_description = 'Role'

    def photo_preview(self, obj):
        """Display photo thumbnail in admin."""
        if obj.photo:
            return format_html(
                '<img src="{}" width="50" height="50" style="border-radius: 50%; object-fit: cover;" />',
                obj.photo.url
            )
        return format_html(
            '<div style="width:50px;height:50px;border-radius:50%;background:#E5E7EB;display:flex;align-items:center;justify-content:center;font-size:20px;font-weight:bold;color:#6B7280;">{}</div>',
            obj.name[0].upper()
        )
    photo_preview.short_description = 'Photo'