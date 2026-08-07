from django.contrib import admin

from notifications.models import Notification, EmailLog, SMSLog


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    """Admin view for in-app notifications."""

    list_display = ('title', 'user', 'type', 'priority', 'is_read', 'created_at')
    list_filter = ('type', 'priority', 'is_read', 'created_at')
    search_fields = ('title', 'message', 'user__email', 'user__full_name')
    readonly_fields = ('created_at', 'updated_at', 'read_at')
    ordering = ('-created_at',)
    list_per_page = 25
    date_hierarchy = 'created_at'

    fieldsets = (
        (None, {
            'fields': ('user', 'title', 'message', 'type', 'priority')
        }),
        ('Display', {
            'fields': ('icon', 'action_url', 'metadata')
        }),
        ('Status', {
            'fields': ('is_read', 'read_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    """Admin view for sent email log."""

    list_display = ('to_email', 'subject', 'status', 'email_type', 'created_at')
    list_filter = ('status', 'email_type', 'created_at')
    search_fields = ('to_email', 'subject', 'email_id', 'user__email')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)
    list_per_page = 50
    date_hierarchy = 'created_at'


@admin.register(SMSLog)
class SMSLogAdmin(admin.ModelAdmin):
    """Admin view for sent SMS log."""

    list_display = ('recipient_phone', 'status', 'provider', 'notification_type', 'created_at')
    list_filter = ('status', 'provider', 'notification_type', 'created_at')
    search_fields = ('recipient_phone', 'message', 'user__email')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)
    list_per_page = 50
    date_hierarchy = 'created_at'
