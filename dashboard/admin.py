from django.contrib import admin

# =====================================================================
# DASHBOARD ADMIN
# Dashboard has no models of its own. All data comes from other apps.
# =====================================================================

# If you need to customize User admin from the dashboard side,
# you can unregister and re-register with a custom admin class:

from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

User = get_user_model()

# Unregister the default User admin registered by accounts app
try:
    admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass


# Re-register with custom admin for dashboard
class CustomUserAdmin(BaseUserAdmin):
    list_display = ('email', 'full_name', 'role', 'is_active', 'last_login')
    list_filter = ('role', 'is_active', 'is_staff', 'is_chief')
    search_fields = ('email', 'full_name', 'phone')
    ordering = ('email',)

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {'fields': ('full_name', 'phone')}),
        ('Permissions',
         {'fields': ('role', 'is_active', 'is_staff', 'is_superuser', 'is_chief', 'groups', 'user_permissions')}),
        ('Important Dates', {'fields': ('last_login', 'date_joined')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'full_name', 'phone', 'password1', 'password2'),
        }),
    )


admin.site.register(User, CustomUserAdmin)