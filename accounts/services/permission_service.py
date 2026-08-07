"""
Permission Service - Role-based access control management.

This service handles permission management for admin users including
permission assignment, checking, and inheritance.
"""

import logging
from typing import Dict, List, Optional, Set
from django.core.exceptions import PermissionDenied

from accounts.models import User, Profile

logger = logging.getLogger('caldan')


class PermissionService:
    """
    Service for permission management.

    Features:
    - Role-based access control
    - Configurable permissions for Platform Admins
    - Permission inheritance (Chief Admin has all)
    - Permission checking decorators
    """

    # =====================================================================
    # PERMISSION DEFINITIONS
    # =====================================================================

    ADMIN_PERMISSIONS = {
        'can_invite_admins': {
            'label': 'Invite Admins',
            'description': 'Can invite new platform admins',
            'default': True,
        },
        'can_manage_settings': {
            'label': 'Manage Settings',
            'description': 'Can modify system settings',
            'default': True,
        },
        'can_manage_projects': {
            'label': 'Manage Projects',
            'description': 'Can create, edit, and delete projects',
            'default': True,
        },
        'can_manage_inventory': {
            'label': 'Manage Inventory',
            'description': 'Can manage materials and stock',
            'default': True,
        },
        'can_manage_shop': {
            'label': 'Manage Shop',
            'description': 'Can manage products and orders',
            'default': True,
        },
        'can_manage_finances': {
            'label': 'Manage Finances',
            'description': 'Can manage payments and expenses',
            'default': True,
        },
        'can_manage_clients': {
            'label': 'Manage Clients',
            'description': 'Can manage client records',
            'default': True,
        },
        'can_manage_team': {
            'label': 'Manage Team',
            'description': 'Can manage team members',
            'default': True,
        },
        'can_manage_services': {
            'label': 'Manage Services',
            'description': 'Can manage service offerings',
            'default': True,
        },
        'can_manage_reports': {
            'label': 'Manage Reports',
            'description': 'Can view and export reports',
            'default': True,
        },
        'can_export_data': {
            'label': 'Export Data',
            'description': 'Can export data in various formats',
            'default': True,
        },
        'can_backup_data': {
            'label': 'Backup Data',
            'description': 'Can create and restore backups',
            'default': True,
        },
        'can_delete_data': {
            'label': 'Delete Data',
            'description': 'Can permanently delete data',
            'default': False,
        },
        'can_manage_audit_log': {
            'label': 'Manage Audit Log',
            'description': 'Can view and export audit logs',
            'default': True,
        },
    }

    # =====================================================================
    # PERMISSION CHECKING
    # =====================================================================

    @classmethod
    def has_permission(cls, user: User, permission: str) -> bool:
        """
        Check if a user has a specific permission.

        Args:
            user: User to check
            permission: Permission key to check

        Returns:
            bool: True if user has permission
        """
        # Not logged in
        if not user or not user.is_authenticated:
            return False

        # Chief Admin has all permissions
        if user.is_chief or user.is_superuser:
            return True

        # Platform Admin - check profile permissions
        if user.is_platform_admin:
            if hasattr(user, 'profile'):
                return user.profile.get_permission(permission, False)
            return False

        # Client has no admin permissions
        return False

    @classmethod
    def has_any_permission(cls, user: User, permissions: List[str]) -> bool:
        """
        Check if a user has any of the specified permissions.

        Args:
            user: User to check
            permissions: List of permission keys

        Returns:
            bool: True if user has any permission
        """
        for permission in permissions:
            if cls.has_permission(user, permission):
                return True
        return False

    @classmethod
    def has_all_permissions(cls, user: User, permissions: List[str]) -> bool:
        """
        Check if a user has all specified permissions.

        Args:
            user: User to check
            permissions: List of permission keys

        Returns:
            bool: True if user has all permissions
        """
        for permission in permissions:
            if not cls.has_permission(user, permission):
                return False
        return True

    # =====================================================================
    # PERMISSION MANAGEMENT
    # =====================================================================

    @classmethod
    def get_user_permissions(cls, user: User) -> Dict[str, bool]:
        """
        Get all permissions for a user.

        Args:
            user: User to get permissions for

        Returns:
            dict: Permission key-value pairs
        """
        # Chief Admin has all permissions
        if user.is_chief or user.is_superuser:
            return {perm: True for perm in cls.ADMIN_PERMISSIONS}

        # Platform Admin - get from profile
        if user.is_platform_admin:
            if hasattr(user, 'profile'):
                return user.profile.permissions
            return {}

        # Client has no permissions
        return {}

    @classmethod
    def set_user_permissions(
            cls,
            user: User,
            permissions: Dict[str, bool],
            *,
            replace: bool = False,
    ) -> None:
        """
        Set permissions for a user.

        Args:
            user: User to set permissions for
            permissions: Dictionary of permission key-value pairs
            replace: When True, the supplied dict is treated as the
                WHOLE permission set — every key known to
                ``ADMIN_PERMISSIONS`` is forced to its boolean value
                (or False if absent). Use this for invitation accept
                so the chief's toggles are authoritative. When False
                (default), keys are merged into whatever the profile
                already holds, which is what the manage-admins edit
                page uses for partial updates.
        """
        # Only Platform Admins can have configurable permissions
        if not user.is_platform_admin:
            raise PermissionDenied("Only Platform Admins can have configurable permissions")

        # Get or create profile
        profile, created = Profile.objects.get_or_create(user=user)

        if replace:
            # Build the full authoritative set: granted keys as the chief
            # set them, every other known permission forced to False so
            # nothing leaks from the old profile or from defaults.
            new_perms = {
                key: bool(permissions.get(key, False))
                for key in cls.ADMIN_PERMISSIONS.keys()
            }
        else:
            # Merge with existing keys (partial update path).
            new_perms = dict(profile.permissions or {})
            new_perms.update(permissions)

        profile.permissions = new_perms
        profile.save(update_fields=['permissions'])

        logger.info(f"Permissions updated for user: {user.email}")

    @classmethod
    def reset_user_permissions(cls, user: User) -> None:
        """
        Reset permissions to default for a user.

        Args:
            user: User to reset permissions for
        """
        if not user.is_platform_admin:
            raise PermissionDenied("Only Platform Admins can have configurable permissions")

        # Get or create profile
        profile, created = Profile.objects.get_or_create(user=user)

        # Reset to default
        profile.permissions = {
            perm: data['default'] for perm, data in cls.ADMIN_PERMISSIONS.items()
        }
        profile.save(update_fields=['permissions'])

        logger.info(f"Permissions reset for user: {user.email}")

    @classmethod
    def get_available_permissions(cls) -> List[Dict[str, str]]:
        """
        Get list of all available permissions with labels and descriptions.

        Returns:
            list: List of permission definitions
        """
        return [
            {
                'key': key,
                'label': data['label'],
                'description': data['description'],
                'default': data['default'],
            }
            for key, data in cls.ADMIN_PERMISSIONS.items()
        ]

    # =====================================================================
    # PERMISSION DECORATORS
    # =====================================================================

    @classmethod
    def require_permission(cls, permission: str):
        """
        Decorator for views requiring a specific permission.

        Args:
            permission: Permission key required

        Returns:
            function: Decorated view function
        """
        from functools import wraps
        from django.shortcuts import redirect
        from django.contrib import messages

        def decorator(view_func):
            @wraps(view_func)
            def wrapper(request, *args, **kwargs):
                if not request.user.is_authenticated:
                    return redirect('accounts:login')

                if not cls.has_permission(request.user, permission):
                    messages.error(request, 'You do not have permission to perform this action.')
                    return redirect('dashboard:overview')

                return view_func(request, *args, **kwargs)

            return wrapper

        return decorator

    @classmethod
    def require_admin(cls):
        """
        Decorator for views requiring admin access.

        Returns:
            function: Decorated view function
        """
        from functools import wraps
        from django.shortcuts import redirect
        from django.contrib import messages

        def decorator(view_func):
            @wraps(view_func)
            def wrapper(request, *args, **kwargs):
                if not request.user.is_authenticated:
                    return redirect('accounts:login')

                if not request.user.is_admin:
                    messages.error(request, 'Access denied. Admin privileges required.')
                    return redirect('dashboard:overview')

                return view_func(request, *args, **kwargs)

            return wrapper

        return decorator

    @classmethod
    def require_chief_admin(cls):
        """
        Decorator for views requiring Chief Admin access.

        Returns:
            function: Decorated view function
        """
        from functools import wraps
        from django.shortcuts import redirect
        from django.contrib import messages

        def decorator(view_func):
            @wraps(view_func)
            def wrapper(request, *args, **kwargs):
                if not request.user.is_authenticated:
                    return redirect('accounts:login')

                if not request.user.is_chief:
                    messages.error(request, 'Access denied. Chief Admin privileges required.')
                    return redirect('dashboard:overview')

                return view_func(request, *args, **kwargs)

            return wrapper

        return decorator

    @classmethod
    def require_setup(cls):
        """
        Decorator for setup views (only accessible when no users exist).

        Returns:
            function: Decorated view function
        """
        from functools import wraps
        from django.shortcuts import redirect
        from django.contrib import messages
        from accounts.models import User

        def decorator(view_func):
            @wraps(view_func)
            def wrapper(request, *args, **kwargs):
                if User.objects.exists():
                    messages.error(request, 'Setup has already been completed.')
                    return redirect('accounts:login')

                return view_func(request, *args, **kwargs)

            return wrapper

        return decorator