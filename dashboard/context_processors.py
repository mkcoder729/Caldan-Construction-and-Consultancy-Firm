"""
Context processors for the dashboard app.

This module provides global context data for all dashboard templates
including user stats, notifications, and sidebar menu.
"""

from django.utils import timezone
from django.contrib import messages

from accounts.models import User
from dashboard.data.sidebar_menu import ADMIN_MENU


def _filter_sidebar_for_user(menu, user):
    """
    Filter sidebar items by the user's permissions.

    Chief Admin / superuser sees everything. Platform Admins only see items
    whose `permission` key (if any) is granted in their profile.

    Headers (section sub-headers like 'Suppliers') are kept only if the next
    non-header item would remain visible — otherwise empty headers collapse.
    """
    try:
        from accounts.services.permission_service import PermissionService
    except Exception:
        return menu

    # Chief / superuser: short-circuit, return as-is
    if getattr(user, 'is_chief', False) or getattr(user, 'is_superuser', False):
        return menu

    filtered = {'sections': []}
    for section in menu.get('sections', []):
        items = section.get('items', [])
        visible_items = []
        for item in items:
            if item.get('type') == 'header':
                # keep headers; they'll appear where they fall in the order
                visible_items.append(item)
                continue
            required = item.get('permission')
            if required is None:
                visible_items.append(item)
            else:
                if PermissionService.has_permission(user, required):
                    visible_items.append(item)

        # Drop trailing headers (no items follow them)
        while visible_items and visible_items[-1].get('type') == 'header':
            visible_items.pop()

        # Drop leading headers if the previous section's last item was a header
        # (handled by traversal order; we just trim leading headers if any)
        # Actually, keep leading headers — they label the start of a section.

        if visible_items:
            new_section = dict(section)
            new_section['items'] = visible_items
            filtered['sections'].append(new_section)

    return filtered


def dashboard_context(request):
    """
    Context processor that injects dashboard data into all templates.

    Provides:
    - Dashboard sidebar menu
    - User stats (projects count, notifications, etc.)
    - Theme preference
    - Current date/time
    - Unread notification count for bell badge
    """
    context = {}

    # Only add dashboard context for authenticated users
    if request.user.is_authenticated:
        user = request.user

        # =================================================================
        # USER STATS
        # =================================================================
        # Build avatar context — used by activity feed, etc.
        avatar_url = ''
        try:
            if user.avatar:
                avatar_url = user.avatar.url
        except Exception:
            avatar_url = ''

        context.update({
            'user_name': user.full_name,
            'user_email': user.email,
            'user_role': user.role,
            'user_avatar': user.full_name[:1].upper() if user.full_name else (user.email[:1].upper() if user.email else '?'),
            'user_avatar_url': avatar_url,
            'is_admin': user.is_admin,
            'is_chief': user.is_chief,
            'is_platform_admin': user.is_platform_admin,
            'password_change_required': getattr(user, 'password_change_required', False),
        })

        # =================================================================
        # THEME PREFERENCE
        # =================================================================
        if hasattr(user, 'profile') and user.profile:
            context['user_theme'] = user.profile.theme
        else:
            context['user_theme'] = 'device'

        # =================================================================
        # SIDEBAR MENU (Admin only) — filtered by permissions for non-chief
        # =================================================================
        if user.is_admin:
            context['sidebar_menu'] = _filter_sidebar_for_user(ADMIN_MENU, user)

        # =================================================================
        # NOTIFICATION COUNT - UPDATED to use notifications app
        # =================================================================
        try:
            from notifications.models import Notification
            unread_count = Notification.objects.filter(
                user=user,
                is_read=False
            ).count()
            context['unread_notifications'] = unread_count
            context['unread_count'] = unread_count  # For bell badge
        except (ImportError, Exception):
            context['unread_notifications'] = 0
            context['unread_count'] = 0

        # =================================================================
        # RECENT NOTIFICATIONS (for dropdown)
        # =================================================================
        try:
            from notifications.models import Notification
            recent_notifications = Notification.objects.filter(
                user=user
            ).order_by('-created_at')[:5]
            context['recent_notifications'] = recent_notifications
        except (ImportError, Exception):
            context['recent_notifications'] = []

    # =================================================================
    # ALWAYS AVAILABLE
    # =================================================================
    context.update({
        'current_date': timezone.now(),
        'current_year': timezone.now().year,
        'app_name': 'Caldan Construction and Consultancy Firm',
        'app_tagline': 'Building Kenya\'s Future, One Project at a Time.',
    })

    return context


def website_context(request):
    """
    Context processor for public website.
    """
    context = {
        'site_name': 'Caldan Construction and Consultancy Firm',
        'site_tagline': 'Building Kenya\'s Future, One Project at a Time.',
        'current_year': timezone.now().year,
    }
    return context


def website_context(request):
    """
    Context processor for public website.
    """
    context = {
        'site_name': 'Caldan Construction and Consultancy Firm',
        'site_tagline': 'Building Kenya\'s Future, One Project at a Time.',
        'current_year': timezone.now().year,
    }
    return context