"""
Celery tasks for the accounts app.

This module contains background tasks for user management,
invitation cleanup, and audit log maintenance.
"""

import logging
from celery import shared_task
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings

from accounts.models import User, AuditLog, AdminInvitation
from accounts.services.audit_service import AuditService
from accounts.services.invitation_service import InvitationService

logger = logging.getLogger('caldan')


@shared_task
def cleanup_expired_invitations():
    """
    Task to clean up expired invitations.

    Runs daily to remove expired invitations from the database.
    """
    try:
        count = InvitationService.cleanup_expired_invitations()
        logger.info(f"Cleaned up {count} expired invitations")
        return {'cleaned': count}
    except Exception as e:
        logger.error(f"Failed to clean up expired invitations: {str(e)}")
        raise


@shared_task
def cleanup_old_audit_logs():
    """
    Task to clean up old audit logs.

    Runs weekly to remove audit logs older than the retention period (365 days).
    """
    try:
        from django.conf import settings
        retention_days = getattr(settings, 'AUDIT_LOG_RETENTION_DAYS', 365)
        count = AuditService.cleanup_old_logs(retention_days)
        logger.info(f"Cleaned up {count} old audit logs")
        return {'cleaned': count}
    except Exception as e:
        logger.error(f"Failed to clean up audit logs: {str(e)}")
        raise


@shared_task
def deactivate_inactive_users(days=90):
    """
    Task to deactivate inactive users.

    Args:
        days: Number of days of inactivity before deactivation.
    """
    try:
        cutoff = timezone.now() - timezone.timedelta(days=days)

        # Find users who haven't logged in for the specified period
        inactive_users = User.objects.filter(
            is_active=True,
            is_superuser=False,
            is_chief=False,
            last_login__lt=cutoff,
            date_joined__lt=cutoff
        )

        count = inactive_users.count()
        inactive_users.update(is_active=False)

        logger.info(f"Deactivated {count} inactive users")
        return {'deactivated': count}
    except Exception as e:
        logger.error(f"Failed to deactivate inactive users: {str(e)}")
        raise


@shared_task
def send_account_activation_reminder(user_id=None):
    """
    Send a reminder to activate an account.

    Args:
        user_id: Optional ID of a single user to remind. When None,
            reminders go to every active user whose email is not yet
            verified.
    """
    try:
        from notifications.services.email_service import EmailService

        if user_id is not None:
            users = User.objects.filter(id=user_id)
        else:
            users = User.objects.filter(is_active=True, is_email_verified=False)

        if not users.exists():
            return {'sent': False, 'reason': 'No matching users'}

        sent_count = 0
        for user in users:
            if user.is_email_verified:
                continue

            context = {
                'user': user,
                'site_name': getattr(settings, 'APP_NAME', 'Caldan Construction and Consultancy Firm'),
                'login_url': f"{getattr(settings, 'BASE_URL', 'http://localhost:8000')}/accounts/login/",
            }

            ok = EmailService.send_template(
                to_email=user.email,
                subject='Reminder: Complete Your Account Setup',
                template_name='email/account_activation_reminder.html',
                context=context,
                email_type='ACCOUNT_REMINDER'
            )
            if ok:
                sent_count += 1

        logger.info(f"Sent activation reminder to {sent_count} users")
        return {'sent': sent_count, 'total_users': users.count()}
    except Exception as e:
        logger.error(f"Failed to send activation reminder: {str(e)}")
        raise


@shared_task
def verify_audit_chain():
    """
    Task to verify the integrity of the audit chain.

    Runs weekly to ensure the audit trail hasn't been tampered with.
    """
    try:
        is_valid, message, broken_at = AuditService.verify_chain_integrity()

        if is_valid:
            logger.info("Audit chain integrity verified")
        else:
            logger.warning(f"Audit chain integrity check failed: {message}")

            # Send alert to admin
            subject = "CRITICAL: Audit Chain Integrity Compromised"
            message_body = f"""
            The audit chain integrity check has failed.

            Message: {message}
            Broken at ID: {broken_at}
            Timestamp: {timezone.now().isoformat()}

            Please investigate immediately.
            """

            send_mail(
                subject=subject,
                message=message_body,
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', f"Caldan Construction and Consultancy Firm <{getattr(settings, 'ADMIN_EMAIL', 'info.caldanconstruction@gmail.com')}>"),
                recipient_list=[getattr(settings, 'ADMIN_EMAIL', 'info.caldanconstruction@gmail.com')],
            )

        return {
            'valid': is_valid,
            'message': message,
            'broken_at': broken_at
        }
    except Exception as e:
        logger.error(f"Failed to verify audit chain: {str(e)}")
        raise