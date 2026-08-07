"""
Notification Views
In-app notification management for the dashboard.
All notification-related views are now centralized in the notifications app.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from notifications.models import Notification
from notifications.services.notification_service import NotificationService


@login_required
def notification_list(request):
    """
    List all notifications with filtering and pagination.
    URL: /dashboard/notifications/
    """
    notifications = Notification.objects.filter(user=request.user)

    # Filter by read status
    status = request.GET.get('status', 'all')
    if status == 'unread':
        notifications = notifications.filter(is_read=False)
    elif status == 'read':
        notifications = notifications.filter(is_read=True)

    # Order by most recent
    notifications = notifications.order_by('-created_at')

    # Pagination
    paginator = Paginator(notifications, 20)
    page = request.GET.get('page', 1)

    try:
        page_obj = paginator.page(page)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    # Stats
    total_count = Notification.objects.filter(user=request.user).count()
    unread_count = Notification.objects.filter(user=request.user, is_read=False).count()
    read_count = Notification.objects.filter(user=request.user, is_read=True).count()

    context = {
        'page_title': 'Notifications',
        'page_icon': 'fa-bell',
        'notifications': page_obj,
        'total_count': total_count,
        'unread_count': unread_count,
        'read_count': read_count,
        'status': status,
        'page_obj': page_obj,
        'paginator': paginator,
        'is_paginated': page_obj.has_other_pages(),
    }

    # FIXED: Correct template path based on actual directory structure
    return render(request, 'notifications/dashboard/admin/notifications/index.html', context)


@login_required
def notification_mark_read(request, notification_id):
    """
    Mark a single notification as read.
    Supports both AJAX and standard POST requests.
    """
    notification = get_object_or_404(Notification, id=notification_id, user=request.user)
    notification.mark_as_read()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        unread_count = Notification.objects.filter(user=request.user, is_read=False).count()
        return JsonResponse({
            'success': True,
            'unread_count': unread_count,
            'message': 'Notification marked as read.'
        })

    messages.success(request, 'Notification marked as read.')
    return redirect('notifications:list')


@login_required
def notification_mark_all_read(request):
    """
    Mark all notifications as read.
    Supports both AJAX and standard POST requests.
    """
    count = NotificationService.mark_all_as_read(request.user)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'count': count,
            'message': f'{count} notifications marked as read.'
        })

    messages.success(request, f'{count} notifications marked as read.')
    return redirect('notifications:list')


@login_required
def notification_delete(request, notification_id):
    """
    Delete a notification.
    Supports both AJAX and standard POST requests.
    """
    notification = get_object_or_404(Notification, id=notification_id, user=request.user)
    notification.delete()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        unread_count = Notification.objects.filter(user=request.user, is_read=False).count()
        return JsonResponse({
            'success': True,
            'unread_count': unread_count,
            'message': 'Notification deleted.'
        })

    messages.success(request, 'Notification deleted.')
    return redirect('notifications:list')


@login_required
def notification_unread_count(request):
    """
    Get unread notification count for badge.
    Always returns JSON.
    """
    count = NotificationService.get_unread_count(request.user)
    return JsonResponse({
        'unread_count': count,
        'success': True,
    })