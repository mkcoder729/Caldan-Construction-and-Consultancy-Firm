# Accounts Permissions Decorators - Caldan Construction
# "Building Kenya's Future, One Project at a Time."

from functools import wraps
from django.shortcuts import redirect
from django.core.exceptions import PermissionDenied
from django.contrib import messages


def admin_required(view_func):
    """
    Decorator: View accessible only to admins (staff users).

    Usage:
        @login_required
        @admin_required
        def my_view(request):
            ...
    """

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        if not request.user.is_staff:
            raise PermissionDenied("Access denied. Admin only.")
        return view_func(request, *args, **kwargs)

    return wrapper


def chief_admin_required(view_func):
    """
    Decorator: View accessible only to Chief Admin (superuser).

    Usage:
        @login_required
        @chief_admin_required
        def my_view(request):
            ...
    """

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        if not request.user.is_superuser:
            raise PermissionDenied("Access denied. Chief Admin only.")
        return view_func(request, *args, **kwargs)

    return wrapper


def setup_required(view_func):
    """
    Decorator: Setup view accessible only when no users exist.

    Usage:
        @setup_required
        def setup_view(request):
            ...
    """

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        from accounts.models.user import User
        if User.objects.exists():
            raise PermissionDenied("Setup already completed.")
        return view_func(request, *args, **kwargs)

    return wrapper


def login_required_with_message(view_func):
    """
    Decorator: Login required with custom error message.

    Usage:
        @login_required_with_message
        def my_view(request):
            ...
    """

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'Please login to access this page.')
            return redirect('accounts:login')
        return view_func(request, *args, **kwargs)

    return wrapper


def permission_required(permission_flag):
    """
    Decorator: Check specific permission flag on user profile.

    Usage:
        @permission_required('can_manage_projects')
        def my_view(request):
            ...
    """

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('accounts:login')

            # Check if user has the required permission
            if hasattr(request.user, 'profile'):
                permissions = getattr(request.user.profile, 'permissions', {})
                if not permissions.get(permission_flag, True):
                    raise PermissionDenied(
                        f"You don't have permission to perform this action. "
                        f"Required: {permission_flag}"
                    )
            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator