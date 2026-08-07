"""
Audit Service - Immutable audit logging with SHA-256 hash chain.

This service handles all audit logging for the Caldan Construction platform.
Every significant action is logged with cryptographic hash chaining to ensure
tamper-proof audit trails.
"""

import logging
import hashlib
from typing import Optional, Dict, Any
from django.http import HttpRequest
from django.utils import timezone
from django.conf import settings

from accounts.models import AuditLog, User

logger = logging.getLogger('caldan.audit')


class AuditService:
    """
    Centralized audit logging service with SHA-256 hash chain.

    Features:
    - Immutable audit trail with cryptographic verification
    - Automatic IP and user agent capture
    - Consistent logging across all apps
    - Chain integrity verification
    """

    @staticmethod
    def log_action(
            user: Optional[User],
            action: str,
            entity_type: str = '',
            entity_id: str = '',
            details: Optional[Dict[str, Any]] = None,
            request: Optional[HttpRequest] = None
    ) -> AuditLog:
        """
        Log an action to the immutable audit trail.

        Args:
            user: The user performing the action (or None for system actions)
            action: The action type (from AuditLog.Action choices)
            entity_type: Type of entity affected (e.g., 'Project', 'User')
            entity_id: ID of the entity affected
            details: Additional context as a dictionary
            request: Django request object for IP and user agent

        Returns:
            AuditLog: The created audit log entry
        """
        # Get IP address and user agent from request
        ip_address = None
        user_agent = ''

        if request:
            ip_address = AuditService._get_client_ip(request)
            user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]

        # Prepare details
        if details is None:
            details = {}

        # Add timestamp to details
        details['timestamp'] = timezone.now().isoformat()

        # Create audit log entry
        log_entry = AuditLog.objects.create(
            user=user,
            user_role=user.role if user else 'SYSTEM',
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id else '',
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        # Log to file as well
        logger.info(
            f"ACTION: {action} | USER: {user.email if user else 'SYSTEM'} | "
            f"ENTITY: {entity_type}/{entity_id} | IP: {ip_address}"
        )

        return log_entry

    @staticmethod
    def _get_client_ip(request: HttpRequest) -> Optional[str]:
        """
        Extract client IP address from request.

        Handles proxies and load balancers by checking X-Forwarded-For header.

        Args:
            request: Django request object

        Returns:
            str: Client IP address or None
        """
        # Check for X-Forwarded-For header (proxies/load balancers)
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            # Get the first IP in the chain (client IP)
            return x_forwarded_for.split(',')[0].strip()

        # Fall back to REMOTE_ADDR
        return request.META.get('REMOTE_ADDR')

    @staticmethod
    def log_login_success(user: User, request: HttpRequest) -> AuditLog:
        """Log a successful login."""
        return AuditService.log_action(
            user=user,
            action=AuditLog.Action.LOGIN_SUCCESS,
            entity_type='User',
            entity_id=user.id,
            details={
                'email': user.email,
                'role': user.role,
            },
            request=request
        )

    @staticmethod
    def log_login_failed(email: str, request: HttpRequest, attempts: int) -> AuditLog:
        """Log a failed login attempt."""
        return AuditService.log_action(
            user=None,
            action=AuditLog.Action.LOGIN_FAILED,
            entity_type='User',
            entity_id=email,
            details={
                'email': email,
                'attempts': attempts,
            },
            request=request
        )

    @staticmethod
    def log_account_locked(user: User, request: HttpRequest) -> AuditLog:
        """Log an account lockout."""
        return AuditService.log_action(
            user=user,
            action=AuditLog.Action.ACCOUNT_LOCKED,
            entity_type='User',
            entity_id=user.id,
            details={
                'email': user.email,
                'locked_until': user.locked_until.isoformat() if user.locked_until else None,
            },
            request=request
        )

    @staticmethod
    def log_otp_sent(user: User, request: HttpRequest) -> AuditLog:
        """Log an OTP being sent."""
        return AuditService.log_action(
            user=user,
            action=AuditLog.Action.OTP_SENT,
            entity_type='User',
            entity_id=user.id,
            details={
                'email': user.email,
                'expiry_minutes': getattr(settings, 'OTP_EXPIRY_MINUTES', 5),
            },
            request=request
        )

    @staticmethod
    def log_otp_verified(user: User, request: HttpRequest) -> AuditLog:
        """Log successful OTP verification."""
        return AuditService.log_action(
            user=user,
            action=AuditLog.Action.OTP_VERIFIED,
            entity_type='User',
            entity_id=user.id,
            details={
                'email': user.email,
            },
            request=request
        )

    @staticmethod
    def log_otp_failed(user: User, request: HttpRequest, remaining_attempts: int) -> AuditLog:
        """Log a failed OTP verification attempt."""
        return AuditService.log_action(
            user=user,
            action=AuditLog.Action.OTP_FAILED,
            entity_type='User',
            entity_id=user.id,
            details={
                'email': user.email,
                'remaining_attempts': remaining_attempts,
                'max_attempts': getattr(settings, 'OTP_MAX_ATTEMPTS', 3),
            },
            request=request
        )

    @staticmethod
    def log_password_changed(user: User, request: HttpRequest) -> AuditLog:
        """Log a password change."""
        return AuditService.log_action(
            user=user,
            action=AuditLog.Action.PASSWORD_CHANGED,
            entity_type='User',
            entity_id=user.id,
            details={
                'email': user.email,
            },
            request=request
        )

    @staticmethod
    def log_user_created(created_by: User, new_user: User, request: HttpRequest) -> AuditLog:
        """Log a new user being created."""
        return AuditService.log_action(
            user=created_by,
            action=AuditLog.Action.USER_CREATED,
            entity_type='User',
            entity_id=new_user.id,
            details={
                'email': new_user.email,
                'role': new_user.role,
                'full_name': new_user.full_name,
            },
            request=request
        )

    @staticmethod
    def log_user_deleted(deleted_by: User, deleted_user: User, request: HttpRequest) -> AuditLog:
        """Log a user being deleted."""
        return AuditService.log_action(
            user=deleted_by,
            action=AuditLog.Action.USER_DELETED,
            entity_type='User',
            entity_id=deleted_user.id,
            details={
                'email': deleted_user.email,
                'role': deleted_user.role,
                'full_name': deleted_user.full_name,
            },
            request=request
        )

    @staticmethod
    def log_admin_invitation_sent(
            created_by: User,
            email: str,
            invitation_id: str,
            request: HttpRequest
    ) -> AuditLog:
        """Log an admin invitation being sent."""
        return AuditService.log_action(
            user=created_by,
            action=AuditLog.Action.ADMIN_INVITATION_SENT,
            entity_type='AdminInvitation',
            entity_id=invitation_id,
            details={
                'email': email,
                'invited_by': created_by.email,
            },
            request=request
        )

    @staticmethod
    def log_admin_invitation_accepted(
            user: User,
            invitation_id: str,
            request: HttpRequest
    ) -> AuditLog:
        """Log an admin invitation being accepted."""
        return AuditService.log_action(
            user=user,
            action=AuditLog.Action.ADMIN_INVITATION_ACCEPTED,
            entity_type='AdminInvitation',
            entity_id=invitation_id,
            details={
                'email': user.email,
            },
            request=request
        )

    @staticmethod
    def verify_chain_integrity() -> tuple:
        """
        Verify the cryptographic hash chain integrity.

        Returns:
            tuple: (is_valid, message, broken_at_id)
        """
        return AuditLog.verify_chain()

    @staticmethod
    def cleanup_old_logs(retention_days: Optional[int] = None) -> int:
        """
        Clean up audit logs older than retention period.

        Args:
            retention_days: Number of days to retain. Defaults to 365.

        Returns:
            int: Number of logs deleted
        """
        return AuditLog.cleanup_old_logs(retention_days)

    @staticmethod
    def get_user_audit_trail(
            user: User,
            limit: int = 100,
            action: Optional[str] = None
    ) -> list:
        """
        Get audit trail for a specific user.

        Args:
            user: The user to get audit trail for
            limit: Maximum number of logs to return
            action: Optional filter by action type

        Returns:
            list: AuditLog entries for the user
        """
        queryset = AuditLog.objects.filter(user=user)

        if action:
            queryset = queryset.filter(action=action)

        return list(queryset.order_by('-created_at')[:limit])

    @staticmethod
    def get_system_audit_trail(
            limit: int = 100,
            action: Optional[str] = None,
            start_date: Optional[str] = None,
            end_date: Optional[str] = None
    ) -> list:
        """
        Get system-wide audit trail with filters.

        Args:
            limit: Maximum number of logs to return
            action: Optional filter by action type
            start_date: Optional start date filter (ISO format)
            end_date: Optional end date filter (ISO format)

        Returns:
            list: AuditLog entries
        """
        queryset = AuditLog.objects.all()

        if action:
            queryset = queryset.filter(action=action)

        if start_date:
            queryset = queryset.filter(created_at__gte=start_date)

        if end_date:
            queryset = queryset.filter(created_at__lte=end_date)

        return list(queryset.order_by('-created_at')[:limit])