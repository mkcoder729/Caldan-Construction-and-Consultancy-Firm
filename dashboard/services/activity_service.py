"""
Activity feed service for dashboard.
Provides real-time activity from audit logs.
"""

from django.db.models import Count
from django.utils import timezone
from django.core.paginator import Paginator

from accounts.models import AuditLog
from accounts.models.user import User


class ActivityService:
    """
    Service for fetching and formatting activity feed data.
    """

    @classmethod
    def get_recent_activity(cls, limit=20, offset=0, user=None):
        """
        Get recent activity from audit logs.

        Args:
            limit: Number of items to return
            offset: Pagination offset
            user: Filter by user (optional)

        Returns:
            List of activity items with formatted data
        """
        logs = AuditLog.objects.select_related('user').order_by('-created_at')

        if user:
            logs = logs.filter(user=user)

        total = logs.count()
        logs = logs[offset:offset + limit]

        activities = []
        for log in logs:
            activities.append(cls._format_activity(log))

        return {
            'items': activities,
            'total': total,
            'limit': limit,
            'offset': offset,
            'has_more': total > (offset + limit),
        }

    @classmethod
    def _format_activity(cls, log):
        """
        Format a single audit log entry for display.
        """
        # Icon mapping for actions
        icon_map = {
            'LOGIN_SUCCESS': 'fa-sign-in-alt',
            'LOGIN_FAILED': 'fa-times-circle',
            'LOGOUT': 'fa-sign-out-alt',
            'PASSWORD_CHANGED': 'fa-key',
            'OTP_SENT': 'fa-envelope',
            'OTP_VERIFIED': 'fa-check-circle',
            'OTP_FAILED': 'fa-exclamation-circle',
            'ACCOUNT_LOCKED': 'fa-lock',
            'USER_CREATED': 'fa-user-plus',
            'USER_UPDATED': 'fa-user-edit',
            'USER_DELETED': 'fa-user-minus',
            'PERMISSION_CHANGED': 'fa-user-cog',
            'ADMIN_INVITATION_SENT': 'fa-envelope',
            'ADMIN_ACCOUNT_CREATED': 'fa-user-plus',
            'PROJECT_CREATED': 'fa-plus-circle',
            'PROJECT_UPDATED': 'fa-edit',
            'PROJECT_DELETED': 'fa-trash',
            'PROJECT_ARCHIVED': 'fa-archive',
            'PROJECT_RESTORED': 'fa-undo',
            'MATERIAL_CREATED': 'fa-plus-circle',
            'MATERIAL_UPDATED': 'fa-edit',
            'MATERIAL_DELETED': 'fa-trash',
            'STOCK_IN': 'fa-arrow-down',
            'STOCK_OUT': 'fa-arrow-up',
            'STOCK_ALERT': 'fa-exclamation-triangle',
            'ORDER_PLACED': 'fa-shopping-bag',
            'ORDER_STATUS_UPDATED': 'fa-sync',
            'ORDER_CANCELLED': 'fa-times',
            'PAYMENT_RECORDED': 'fa-money-bill-wave',
            'PAYMENT_APPROVED': 'fa-check',
            'PAYMENT_COMPLETED': 'fa-check-circle',
            'PAYMENT_CANCELLED': 'fa-ban',
            'EXPENSE_RECORDED': 'fa-receipt',
            'REPORT_EXPORTED': 'fa-file-export',
            'DATA_EXPORTED': 'fa-database',
            'SYSTEM_ALERT': 'fa-bell',
            'SETTINGS_CHANGED': 'fa-cog',
        }

        # Color mapping
        color_map = {
            'LOGIN_SUCCESS': 'success',
            'LOGIN_FAILED': 'danger',
            'LOGOUT': 'secondary',
            'PASSWORD_CHANGED': 'warning',
            'OTP_SENT': 'info',
            'OTP_VERIFIED': 'success',
            'OTP_FAILED': 'danger',
            'ACCOUNT_LOCKED': 'danger',
            'USER_CREATED': 'success',
            'USER_UPDATED': 'info',
            'USER_DELETED': 'danger',
            'PERMISSION_CHANGED': 'warning',
            'ADMIN_INVITATION_SENT': 'info',
            'ADMIN_ACCOUNT_CREATED': 'success',
            'PROJECT_CREATED': 'success',
            'PROJECT_UPDATED': 'info',
            'PROJECT_DELETED': 'danger',
            'PROJECT_ARCHIVED': 'warning',
            'PROJECT_RESTORED': 'success',
            'MATERIAL_CREATED': 'success',
            'MATERIAL_UPDATED': 'info',
            'MATERIAL_DELETED': 'danger',
            'STOCK_IN': 'success',
            'STOCK_OUT': 'warning',
            'STOCK_ALERT': 'danger',
            'ORDER_PLACED': 'success',
            'ORDER_STATUS_UPDATED': 'info',
            'ORDER_CANCELLED': 'danger',
            'PAYMENT_RECORDED': 'success',
            'PAYMENT_APPROVED': 'info',
            'PAYMENT_COMPLETED': 'success',
            'PAYMENT_CANCELLED': 'danger',
            'EXPENSE_RECORDED': 'warning',
            'REPORT_EXPORTED': 'info',
            'DATA_EXPORTED': 'info',
            'SYSTEM_ALERT': 'warning',
            'SETTINGS_CHANGED': 'info',
        }

        action = log.action
        icon = icon_map.get(action, 'fa-circle')
        color = color_map.get(action, 'secondary')

        # Human-readable label
        label = action.replace('_', ' ').title()

        # User display name
        user_name = log.user.full_name if log.user else 'System'
        user_email = log.user.email if log.user else 'system@caldan.com'

        return {
            'id': log.id,
            'icon': icon,
            'color': color,
            'label': label,
            'user': user_name,
            'user_email': user_email,
            'user_avatar': user_name[0].upper(),
            'details': log.details,
            'ip_address': log.ip_address,
            'created_at': log.created_at,
            'time_ago': cls._time_ago(log.created_at),
            'entity_type': log.entity_type,
            'entity_id': log.entity_id,
        }

    @classmethod
    def _time_ago(cls, dt):
        """
        Format time ago string.
        """
        now = timezone.now()
        diff = now - dt

        seconds = diff.total_seconds()
        minutes = int(seconds // 60)
        hours = int(minutes // 60)
        days = int(hours // 24)

        if seconds < 60:
            return 'Just now'
        elif minutes < 60:
            return f'{minutes}m ago'
        elif hours < 24:
            return f'{hours}h ago'
        elif days < 7:
            return f'{days}d ago'
        else:
            return dt.strftime('%b %d, %Y')

    @classmethod
    def get_activity_summary(cls):
        """
        Get summary stats for activity feed.
        """
        today = timezone.now().date()

        return {
            'total_actions': AuditLog.objects.count(),
            'today': AuditLog.objects.filter(
                created_at__date=today
            ).count(),
            'this_week': AuditLog.objects.filter(
                created_at__date__gte=today - timezone.timedelta(days=7)
            ).count(),
            'unique_users': AuditLog.objects.values('user').distinct().count(),
            'most_active_actions': AuditLog.objects.values('action')
                .annotate(count=Count('id'))
                .order_by('-count')[:5],
        }