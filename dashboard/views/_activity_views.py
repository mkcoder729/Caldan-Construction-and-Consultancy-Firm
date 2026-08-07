"""
Activity Feed Views
Real-time activity log with filtering and pagination.
"""

import logging
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.utils import timezone

from dashboard.services.activity_service import ActivityService
from accounts.models import AuditLog
from accounts.models.user import User
from collections import Counter

logger = logging.getLogger('caldan.dashboard')


@login_required
def activity_feed(request):
    """
    Activity feed page with pagination and filters.
    """
    page = int(request.GET.get('page', 1))
    limit = 20
    offset = (page - 1) * limit

    # Get filter parameters
    user_filter = request.GET.get('user', None)
    action_filter = request.GET.get('action', None)
    search = request.GET.get('search', None)

    # Build queryset for filters
    qs = AuditLog.objects.select_related('user').order_by('-created_at')
    if user_filter:
        qs = qs.filter(user_id=user_filter)
    if action_filter:
        qs = qs.filter(action=action_filter)
    if search:
        qs = qs.filter(
            details__icontains=search
        ) | qs.filter(action__icontains=search) | qs.filter(entity_type__icontains=search)

    total = qs.count()
    logs = list(qs[offset:offset + limit])
    activities = [ActivityService._format_activity(log) for log in logs]

    # Get activity summary
    summary = ActivityService.get_activity_summary()

    # Users who appear in the activity feed (for filter dropdown)
    user_ids = list(AuditLog.objects.values_list('user_id', flat=True).distinct())
    users = User.objects.filter(id__in=user_ids).order_by('full_name', 'email')

    # Distinct actions (for filter dropdown)
    actions = sorted(set(AuditLog.objects.values_list('action', flat=True)))

    total_pages = (total + limit - 1) // limit

    context = {
        'page_title': 'Activity Feed',
        'page_icon': 'fa-history',
        'activities': activities,
        'total': total,
        'page': page,
        'limit': limit,
        'total_pages': total_pages,
        'has_more': (offset + limit) < total,
        'has_previous': offset > 0,
        'summary': summary,
        'users': users,
        'actions': actions,
        'user_filter': user_filter,
        'action_filter': action_filter,
        'search': search,
    }

    return render(request, 'dashboard/dashboard/admin/activity/index.html', context)


@login_required
def activity_refresh(request):
    """
    AJAX endpoint to refresh activity feed.
    """
    since = request.GET.get('since', None)
    limit = int(request.GET.get('limit', 10))

    # Get recent activity
    activity = ActivityService.get_recent_activity(limit=limit)

    return JsonResponse({
        'success': True,
        'items': activity['items'],
        'total': activity['total'],
        'has_more': activity['has_more'],
    })


@login_required
def activity_export_pdf(request):
    """
    Export the activity feed as a beautifully styled PDF.
    """
    user_filter = request.GET.get('user', None)
    action_filter = request.GET.get('action', None)

    qs = AuditLog.objects.select_related('user').order_by('-created_at')[:500]
    if user_filter:
        qs = qs.filter(user_id=user_filter)
    if action_filter:
        qs = qs.filter(action=action_filter)

    logs = list(qs)

    # Stats
    action_counts = Counter(log.action for log in logs)
    user_counts = Counter(log.user_id for log in logs if log.user_id)
    user_ids_top = [uid for uid, _ in user_counts.most_common(10)]
    users_by_id = {u.id: u for u in User.objects.filter(id__in=user_ids_top)}

    activity_data = {
        'logs': logs,
        'total_actions': AuditLog.objects.count(),
        'period_actions': len(logs),
        'unique_users': len({log.user_id for log in logs if log.user_id}),
        'action_breakdown': [
            {'action': a, 'count': c} for a, c in action_counts.most_common(15)
        ],
        'user_activity': [
            {
                'user_full_name': users_by_id.get(uid).full_name if users_by_id.get(uid) else None,
                'user_email': users_by_id.get(uid).email if users_by_id.get(uid) else 'System',
                'count': count,
            }
            for uid, count in user_counts.most_common(10)
        ],
        'period_start': logs[-1].created_at if logs else None,
        'period_end': logs[0].created_at if logs else None,
        'generated_at': timezone.now(),
    }

    try:
        from reports.services.pdf_service import PDFService
        # Reuse the audit PDF generator — it already has the right template
        return PDFService.generate_audit_report_pdf(activity_data)
    except Exception as e:
        logger.error(f"Activity PDF export failed: {e}")
        response = HttpResponse(
            f"Activity PDF export failed: {e}",
            content_type='text/plain',
        )
        response['Content-Disposition'] = 'attachment; filename="activity_pdf_error.txt"'
        return response