"""
Settings Views
User profile, appearance, security, and data management.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.utils import timezone
from django.http import JsonResponse, HttpResponse
import csv
import logging

from accounts.models import User, Profile
from accounts.models.audit import AuditLog
from accounts.services.audit_service import AuditService
from services.models import Service as ServiceModel

logger = logging.getLogger('caldan.dashboard')


@login_required
def general_settings(request):
    """
    General system settings.
    """
    context = {
        'page_title': 'General Settings',
        'page_icon': 'fa-cog',
    }
    return render(request, 'dashboard/dashboard/admin/settings/general.html', context)


@login_required
def appearance_settings(request):
    """
    User appearance/theme preferences.
    """
    profile, created = Profile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        theme = request.POST.get('theme', 'light')
        if theme in ['light', 'dark', 'device']:
            profile.theme = theme
            profile.save()
            messages.success(request, 'Appearance settings updated.')
            return redirect('dashboard:appearance_settings')

    context = {
        'page_title': 'Appearance',
        'page_icon': 'fa-palette',
        'profile': profile,
    }
    return render(request, 'dashboard/dashboard/admin/settings/appearance.html', context)


@login_required
def profile_view(request):
    """
    View user profile.
    """
    context = {
        'page_title': 'Profile',
        'page_icon': 'fa-user',
        'user': request.user,
    }
    return render(request, 'dashboard/dashboard/admin/settings/profile.html', context)


@login_required
def profile_edit(request):
    """
    Edit user profile — uses accounts.forms.ProfileForm so avatar
    uploads (multipart) work correctly.
    """
    from accounts.forms.profile_form import ProfileForm
    from accounts.models.audit import AuditLog

    if request.method == 'POST':
        # Handle avatar-clear flag from the "Remove" button
        if request.POST.get('avatar-clear') == '1':
            if request.user.avatar:
                request.user.avatar.delete(save=False)
                request.user.avatar = None
                request.user.save(update_fields=['avatar'])
        form = ProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            user = form.save()
            from accounts.services.audit_service import AuditService
            AuditService.log_action(
                user=user,
                action=AuditLog.Action.USER_UPDATED,
                entity_type='User',
                entity_id=user.id,
                details={
                    'email': user.email,
                    'fields_updated': list(form.changed_data),
                },
                request=request
            )
            messages.success(request, 'Profile updated successfully.')
            return redirect('dashboard:profile_view')
        context = {
            'page_title': 'Edit Profile',
            'page_icon': 'fa-user-edit',
            'user': request.user,
            'form': form,
        }
        return render(request, 'dashboard/dashboard/admin/settings/profile_edit.html', context)

    form = ProfileForm(instance=request.user)
    context = {
        'page_title': 'Edit Profile',
        'page_icon': 'fa-user-edit',
        'user': request.user,
        'form': form,
    }
    return render(request, 'dashboard/dashboard/admin/settings/profile_edit.html', context)


@login_required
def change_password(request):
    """
    Change user password.

    Supports two submission paths:
    - **AJAX** (`X-Requested-With: XMLHttpRequest`): used by the
      force-change-password modal. On success returns JSON
      ``{"ok": true}``; on error returns JSON
      ``{"ok": false, "error": "<message>"}`` with HTTP 400 so the
      modal can render the message inline. NEVER renders the
      settings page in this path — that would cause the page-level
      form to appear alongside the modal, making the user think the
      modal is "showing twice".
    - **Standard form POST**: rendered from the dedicated settings
      page. Returns the settings page on error, redirects on success.
    """
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    if request.method == 'POST':
        current_password = request.POST.get('current_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')

        if not request.user.check_password(current_password):
            if is_ajax:
                return JsonResponse(
                    {'ok': False, 'error': 'Current password is incorrect.'},
                    status=400,
                )
            messages.error(request, 'Current password is incorrect.')
            return render(request, 'dashboard/dashboard/admin/settings/change_password.html')

        if new_password != confirm_password:
            if is_ajax:
                return JsonResponse(
                    {'ok': False, 'error': 'New passwords do not match.'},
                    status=400,
                )
            messages.error(request, 'Passwords do not match.')
            return render(request, 'dashboard/dashboard/admin/settings/change_password.html')

        if len(new_password) < 8:
            if is_ajax:
                return JsonResponse(
                    {'ok': False, 'error': 'Password must be at least 8 characters.'},
                    status=400,
                )
            messages.error(request, 'Password must be at least 8 characters.')
            return render(request, 'dashboard/dashboard/admin/settings/change_password.html')

        request.user.set_password(new_password)
        request.user.password_change_required = False
        request.user.save()
        update_session_auth_hash(request, request.user)

        AuditService.log_action(
            user=request.user,
            action='PASSWORD_CHANGED',
            details={'changed_at': timezone.now().isoformat()}
        )

        if is_ajax:
            return JsonResponse({'ok': True})

        messages.success(request, 'Password changed successfully.')
        return redirect('dashboard:overview')

    context = {
        'page_title': 'Change Password',
        'page_icon': 'fa-key',
    }
    return render(request, 'dashboard/dashboard/admin/settings/change_password.html', context)


@login_required
def security_settings(request):
    """
    Security settings view.
    """
    context = {
        'page_title': 'Security',
        'page_icon': 'fa-shield-alt',
    }
    return render(request, 'dashboard/dashboard/admin/settings/security.html', context)


@login_required
def notification_settings(request):
    """
    Notification preferences.
    """
    profile, created = Profile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        email_notifications = request.POST.get('email_notifications') == 'on'
        sms_notifications = request.POST.get('sms_notifications') == 'on'
        in_app_notifications = request.POST.get('in_app_notifications') == 'on'

        profile.preferences = {
            'email': email_notifications,
            'sms': sms_notifications,
            'in_app': in_app_notifications,
        }
        profile.save()

        messages.success(request, 'Notification preferences updated.')
        return redirect('dashboard:notification_settings')

    context = {
        'page_title': 'Notification Settings',
        'page_icon': 'fa-bell',
        'preferences': profile.preferences or {'email': True, 'sms': True, 'in_app': True},
    }
    return render(request, 'dashboard/dashboard/admin/settings/notifications.html', context)


@login_required
def data_management(request):
    """
    Data management view - exports, backups, deletion.
    """
    context = {
        'page_title': 'Data Management',
        'page_icon': 'fa-database',
    }
    return render(request, 'dashboard/dashboard/admin/settings/data_management.html', context)


@login_required
def services_settings(request):
    """
    Service catalog settings — categories and featured services.
    """
    services = ServiceModel.objects.all().order_by('category', 'display_order', 'name')

    # Group services by category
    category_groups = []
    for code, label in ServiceModel.Category.choices:
        in_group = [s for s in services if s.category == code]
        if in_group:
            category_groups.append({
                'code': code,
                'label': label,
                'count': len(in_group),
                'services': in_group,
            })

    context = {
        'page_title': 'Services Settings',
        'page_icon': 'fa-tools',
        'services': services,
        'category_groups': category_groups,
        'total_categories': len(category_groups),
        'total_services': services.count(),
    }
    return render(request, 'dashboard/dashboard/admin/settings/services.html', context)


@login_required
def audit_log(request):
    """
    Platform audit log viewer — every significant action with filters.
    """
    qs = AuditLog.objects.select_related('user').order_by('-created_at')

    # Filters
    action_filter = request.GET.get('action', '').strip()
    user_filter = request.GET.get('user', '').strip()
    date_from = request.GET.get('date_from', '').strip()
    date_to = request.GET.get('date_to', '').strip()

    if action_filter:
        qs = qs.filter(action=action_filter)
    if user_filter:
        qs = qs.filter(user_id=user_filter)
    if date_from:
        qs = qs.filter(created_at__date__gte=date_from)
    if date_to:
        qs = qs.filter(created_at__date__lte=date_to)

    # Pagination
    from django.core.paginator import Paginator
    paginator = Paginator(qs, 50)
    page_obj = paginator.get_page(request.GET.get('page', 1))
    logs = page_obj.object_list
    total_entries = paginator.count

    # Distinct actions for filter dropdown
    actions = sorted(set(AuditLog.objects.values_list('action', flat=True)))

    # Users who appear in audit log (for filter dropdown)
    user_ids = AuditLog.objects.values_list('user_id', flat=True).distinct()
    users = User.objects.filter(id__in=list(user_ids)).order_by('email')

    context = {
        'page_title': 'Audit Log',
        'page_icon': 'fa-history',
        'logs': logs,
        'actions': actions,
        'users': users,
        'action_filter': action_filter,
        'user_filter': user_filter,
        'date_from': date_from,
        'date_to': date_to,
        'page_obj': page_obj,
        'total_entries': total_entries,
    }
    return render(request, 'dashboard/dashboard/admin/settings/audit_log.html', context)


@login_required
def audit_export(request):
    """
    Export audit logs as CSV or PDF.
    """
    qs = AuditLog.objects.select_related('user').order_by('-created_at')

    fmt = request.GET.get('format', 'csv').lower()
    if fmt == 'pdf':
        return _audit_pdf(qs)

    response = HttpResponse(content_type='text/csv')
    filename = f'audit_log_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv'
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)
    writer.writerow(['Timestamp', 'User', 'Role', 'Action', 'Entity', 'IP Address', 'User Agent', 'Hash'])
    for log in qs.iterator():
        writer.writerow([
            log.created_at.isoformat() if log.created_at else '',
            log.user.email if log.user_id else 'System',
            log.user_role or '',
            log.get_action_display() if hasattr(log, 'get_action_display') else log.action,
            f'{log.entity_type}{f"#{log.entity_id}" if log.entity_id else ""}',
            log.ip_address or '',
            (log.user_agent or '')[:200],
            log.hash_current or '',
        ])
    return response


def _audit_pdf(qs):
    """Generate a comprehensive audit log PDF using the existing template."""
    from collections import Counter

    # Use ALL logs (not capped to 500) so the PDF shows everything
    all_logs = list(qs)
    logs = all_logs[:200]  # cap so the PDF stays a premium summary, not an exhaustive dump

    # Stats
    action_counts = Counter(log.action for log in all_logs)
    user_ids_in_logs = {log.user_id for log in all_logs if log.user_id}
    users_by_id = {u.id: u for u in User.objects.filter(id__in=list(user_ids_in_logs))}

    # Security events = auth-related
    security_actions = {
        'LOGIN_SUCCESS', 'LOGIN_FAILED', 'LOGOUT', 'PASSWORD_CHANGED',
        'PASSWORD_RESET_REQUESTED', 'ACCOUNT_LOCKED', 'OTP_FAILED',
        'PERMISSION_CHANGED', 'CHIEF_ADMIN_CREATED',
    }
    security_events_list = [log for log in logs if log.action in security_actions]

    # Top 10 users by event count
    user_counts = Counter(log.user_id for log in all_logs if log.user_id)
    user_activity = [
        {
            'user_full_name': users_by_id.get(uid).full_name if users_by_id.get(uid) else None,
            'user_email': users_by_id.get(uid).email if users_by_id.get(uid) else 'System',
            'count': count,
        }
        for uid, count in user_counts.most_common(10)
    ]

    # Hash chain — take the latest entry's hash as "current"
    latest = logs[0] if logs else None

    audit_data = {
        # The template needs these exact names — they are spread into the
        # PDF rendering context by PDFService.generate_audit_report_pdf.
        'total_actions': len(all_logs),
        'unique_users': len(user_ids_in_logs),
        'security_events': len(security_events_list),
        'security_events_list': security_events_list,
        'action_breakdown': [
            {'action': a, 'count': c} for a, c in action_counts.most_common(20)
        ],
        'user_activity': user_activity,
        'logs': logs,
        'previous_hash': latest.hash_previous if latest else '',
        'current_hash': latest.hash_current if latest else '',
        'period_start': all_logs[-1].created_at if all_logs else None,
        'period_end': all_logs[0].created_at if all_logs else None,
        'generated_at': timezone.now(),
        'brand_name': 'Caldan Construction',
        'tagline': "Building Kenya's Future, One Project at a Time.",
    }

    try:
        from reports.services.pdf_service import PDFService
        return PDFService.generate_audit_report_pdf(audit_data)
    except Exception:
        logger.exception("PDF audit export failed")
        messages.error(
            request,
            "Audit log PDF export failed. Please try the CSV export or contact support "
            "if this persists.",
        )
        return redirect('dashboard:audit_log')


@login_required
def audit_verify(request):
    """
    Verify the integrity of the audit log hash chain.
    """
    try:
        is_valid, message, broken_at_id = AuditService.verify_chain_integrity()
        return JsonResponse({
            'verified': is_valid,
            'message': message or ('Audit chain is intact.' if is_valid else 'Audit chain FAILED verification.'),
            'broken_at_id': broken_at_id,
        })
    except Exception as e:
        logger.error(f'Audit verification error: {e}')
        return JsonResponse({'verified': False, 'message': str(e)}, status=500)