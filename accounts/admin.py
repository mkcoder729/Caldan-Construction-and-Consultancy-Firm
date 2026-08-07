from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _
from accounts.models import User, AuditLog, AdminInvitation, Profile


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    """Custom admin interface for User model."""

    list_display = (
        'email', 'full_name', 'role', 'is_active',
        'is_email_verified', 'is_chief', 'is_staff', 'date_joined'
    )
    list_filter = (
        'role', 'is_active', 'is_staff', 'is_superuser',
        'is_chief', 'is_email_verified', 'date_joined'
    )
    search_fields = ('email', 'full_name', 'phone', 'admin_id')
    ordering = ('-date_joined',)

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('Personal info'), {
            'fields': ('full_name', 'phone', 'admin_id')
        }),
        (_('Permissions'), {
            'fields': (
                'is_active', 'is_staff', 'is_superuser',
                'is_chief', 'role', 'is_email_verified',
                'groups', 'user_permissions'
            )
        }),
        (_('OTP & Security'), {
            'fields': (
                'otp_code_hash', 'otp_created_at', 'otp_attempts',
                'otp_resend_count', 'otp_last_resend', 'trusted_devices',
                'failed_login_attempts', 'locked_until'
            )
        }),
        (_('Important dates'), {
            'fields': ('last_login', 'date_joined', 'password_change_required')
        }),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'full_name', 'phone', 'password1', 'password2'),
        }),
    )


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """Admin interface for AuditLog."""

    list_display = (
        'action', 'user', 'user_role', 'entity_type',
        'entity_id', 'ip_address', 'created_at'
    )
    list_filter = ('action', 'user_role', 'created_at')
    search_fields = ('user__email', 'entity_type', 'entity_id', 'ip_address')
    readonly_fields = (
        'user', 'user_role', 'action', 'entity_type', 'entity_id',
        'details', 'ip_address', 'user_agent', 'hash_previous',
        'hash_current', 'created_at'
    )
    ordering = ('-created_at',)
    date_hierarchy = 'created_at'

    def has_add_permission(self, request):
        """Prevent manual creation of audit logs."""
        return False

    def has_change_permission(self, request, obj=None):
        """Prevent modification of audit logs."""
        return False


@admin.register(AdminInvitation)
class AdminInvitationAdmin(admin.ModelAdmin):
    """Admin interface for AdminInvitation."""

    list_display = (
        'email', 'created_by', 'created_at', 'expires_at',
        'is_accepted', 'accepted_at'
    )
    list_filter = ('is_accepted', 'created_at', 'expires_at')
    search_fields = ('email', 'token')
    readonly_fields = ('token', 'created_at')
    ordering = ('-created_at',)


@admin.register(Profile)
class UserProfileAdmin(admin.ModelAdmin):
    """Admin interface for UserProfile."""

    list_display = ('user', 'theme')
    list_filter = ('theme',)
    search_fields = ('user__email', 'user__full_name')
    ordering = ('-updated_at',)