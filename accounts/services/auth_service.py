"""
Authentication Service - Handles all authentication business logic.

This service manages login, logout, session management, and account lockout
logic for the Caldan Construction platform.
"""

import logging
from datetime import datetime
from typing import Optional, Tuple, Dict, Any
from django.contrib.auth import authenticate as django_authenticate
from django.contrib.auth import login, logout
from django.contrib.auth.hashers import check_password
from django.http import HttpRequest
from django.utils import timezone
from django.conf import settings
from django.db import transaction

from accounts.models import User
from accounts.services.audit_service import AuditService
from accounts.services.otp_service import OTPService

logger = logging.getLogger('caldan')


class AuthService:
    """
    Authentication service for Caldan Construction.

    Features:
    - Email-based authentication
    - OTP verification flow
    - Account lockout after 5 failed attempts
    - Trusted device management
    - Session management
    """

    MAX_FAILED_ATTEMPTS = 5
    LOCKOUT_DURATION_MINUTES = 15

    @classmethod
    def authenticate(cls, email: str, password: str) -> Dict[str, Any]:
        """
        Authenticate user with email and password only.
        Returns user if successful, error dict if not.
        """
        # Normalize email
        email = email.lower().strip()

        # Try to get user
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return {
                'success': False,
                'error': 'Invalid email or password',
                'code': 'INVALID_CREDENTIALS'
            }

        # Check if user is active
        if not user.is_active:
            return {
                'success': False,
                'error': 'Your account has been deactivated. Please contact support.',
                'code': 'ACCOUNT_INACTIVE'
            }

        # Check if account is locked
        is_locked, lock_message = cls._is_account_locked(user)
        if is_locked:
            return {
                'success': False,
                'error': lock_message,
                'code': 'ACCOUNT_LOCKED'
            }

        # Authenticate using Django
        request = HttpRequest()
        request.META = {}
        authenticated_user = django_authenticate(request, email=email, password=password)

        if authenticated_user is None:
            # Handle failed login
            cls._handle_failed_login(user)
            remaining = cls.MAX_FAILED_ATTEMPTS - user.failed_login_attempts

            # Check if now locked
            is_locked, lock_message = cls._is_account_locked(user)
            if is_locked:
                return {
                    'success': False,
                    'error': lock_message,
                    'code': 'ACCOUNT_LOCKED'
                }

            return {
                'success': False,
                'error': f'Invalid email or password. {remaining} attempt(s) remaining.',
                'code': 'INVALID_CREDENTIALS',
                'remaining_attempts': remaining
            }

        # Successful authentication - reset failed attempts
        cls._handle_successful_login(authenticated_user)

        return {
            'success': True,
            'user': authenticated_user,
            'code': 'AUTH_SUCCESS'
        }

    @classmethod
    def login_with_credentials(
            cls,
            email: str,
            password: str,
            request: HttpRequest
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Authenticate user with email and password.

        Args:
            email: User's email address
            password: User's password
            request: Django request object

        Returns:
            Tuple: (success, response_data)
        """
        # Normalize email
        email = email.lower().strip()

        # Check if user exists
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return False, {
                'error': 'Invalid email or password',
                'code': 'INVALID_CREDENTIALS'
            }

        # Check if user is active
        if not user.is_active:
            return False, {
                'error': 'Your account has been deactivated. Please contact support.',
                'code': 'ACCOUNT_INACTIVE'
            }

        # Check if account is locked
        is_locked, lock_message = cls._is_account_locked(user)
        if is_locked:
            AuditService.log_action(
                user=user,
                action='ACCOUNT_LOCKED',
                details={'reason': lock_message},
                request=request
            )
            return False, {
                'error': lock_message,
                'code': 'ACCOUNT_LOCKED'
            }

        # Authenticate using Django's authenticate
        authenticated_user = django_authenticate(request, email=email, password=password)

        if authenticated_user is None:
            # Handle failed login
            cls._handle_failed_login(user)
            remaining = cls.MAX_FAILED_ATTEMPTS - user.failed_login_attempts

            # Check if now locked
            is_locked, lock_message = cls._is_account_locked(user)
            if is_locked:
                return False, {
                    'error': lock_message,
                    'code': 'ACCOUNT_LOCKED'
                }

            return False, {
                'error': f'Invalid email or password. {remaining} attempt(s) remaining.',
                'code': 'INVALID_CREDENTIALS',
                'remaining_attempts': remaining
            }

        # Successful login - reset failed attempts
        cls._handle_successful_login(authenticated_user)

        # Check if email is already verified and device is trusted
        if user.is_email_verified and cls._is_trusted_device(request, user):
            # Log in immediately for trusted devices
            login(request, user)
            return True, {
                'success': True,
                'message': 'Login successful',
                'redirect_url': 'dashboard:overview',
                'is_trusted': True
            }

        # Generate and send OTP
        otp_code = OTPService.generate_otp(user)

        # Send OTP via email
        try:
            from notifications.services.email_service import EmailService
            email_sent = EmailService.send_otp(
                user=user,
                otp_code=otp_code,
                device_info=request.META.get('HTTP_USER_AGENT', 'Unknown')[:100],
                ip_address=request.META.get('REMOTE_ADDR', '')
            )
        except Exception as e:
            logger.error(f"Failed to send OTP email: {str(e)}")
            return False, {
                'error': 'Failed to send verification code. Please try again.',
                'code': 'OTP_SEND_FAILED'
            }

        if not email_sent:
            return False, {
                'error': 'Failed to send verification code. Please try again.',
                'code': 'OTP_SEND_FAILED'
            }

        # Log OTP sent
        AuditService.log_action(
            user=user,
            action='OTP_SENT',
            details={'email': user.email},
            request=request
        )

        # Store user in session for OTP verification
        request.session['otp_user_id'] = user.id
        request.session['otp_email'] = user.email

        return True, {
            'success': True,
            'message': 'Verification code sent to your email',
            'redirect_url': 'accounts:otp_verify',
            'email': user.email,
            'is_trusted': False,
            'resend_cooldown': getattr(settings, 'OTP_RESEND_COOLDOWN_SECONDS', 60)
        }

    @classmethod
    def verify_otp_and_login(
            cls,
            email: str,
            otp_code: str,
            remember_device: bool,
            request: HttpRequest
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Verify OTP and complete login.

        Args:
            email: User's email address
            otp_code: 8-digit OTP code
            remember_device: Whether to remember the device
            request: Django request object

        Returns:
            Tuple: (success, response_data)
        """
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return False, {
                'error': 'User not found',
                'code': 'USER_NOT_FOUND'
            }

        # Verify OTP
        success, message = OTPService.verify_otp(user, otp_code)

        if not success:
            return False, {
                'error': message,
                'code': 'OTP_INVALID'
            }

        # Log OTP verified
        AuditService.log_action(
            user=user,
            action='OTP_VERIFIED',
            details={'email': user.email},
            request=request
        )

        # Add trusted device if requested
        if remember_device:
            cls._add_trusted_device(request, user)
            AuditService.log_action(
                user=user,
                action='TRUSTED_DEVICE_ADDED',
                details={'device_name': request.META.get('HTTP_USER_AGENT', 'Unknown')[:100]},
                request=request
            )

        # Log in user
        login(request, user)

        # Log successful login
        AuditService.log_action(
            user=user,
            action='LOGIN_SUCCESS',
            details={'ip': request.META.get('REMOTE_ADDR', '')},
            request=request
        )

        # Clear OTP session data
        request.session.pop('otp_user_id', None)
        request.session.pop('otp_email', None)

        return True, {
            'success': True,
            'message': 'Login successful',
            'redirect_url': 'dashboard:overview'
        }

    @classmethod
    def resend_otp(cls, email: str, request: HttpRequest) -> Tuple[bool, Dict[str, Any]]:
        """
        Resend OTP to user's email.

        Args:
            email: User's email address
            request: Django request object

        Returns:
            Tuple: (success, response_data)
        """
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return False, {
                'error': 'User not found',
                'code': 'USER_NOT_FOUND'
            }

        # Check if user can resend OTP
        can_resend, message, wait_seconds = cls._can_resend_otp(user)

        if not can_resend:
            return False, {
                'error': message,
                'code': 'RESEND_BLOCKED',
                'wait_seconds': wait_seconds
            }

        # Generate and send new OTP
        otp_code = OTPService.generate_otp(user)

        # Send OTP via email
        try:
            from notifications.services.email_service import EmailService
            email_sent = EmailService.send_otp(
                user=user,
                otp_code=otp_code,
                device_info=request.META.get('HTTP_USER_AGENT', 'Unknown')[:100],
                ip_address=request.META.get('REMOTE_ADDR', '')
            )
        except Exception as e:
            logger.error(f"Failed to resend OTP email: {str(e)}")
            return False, {
                'error': 'Failed to send verification code. Please try again.',
                'code': 'OTP_SEND_FAILED'
            }

        if not email_sent:
            return False, {
                'error': 'Failed to send verification code. Please try again.',
                'code': 'OTP_SEND_FAILED'
            }

        # Mark OTP as resent
        cls._mark_otp_resend(user)

        # Log OTP resent
        AuditService.log_action(
            user=user,
            action='OTP_RESENT',
            details={'email': user.email},
            request=request
        )

        return True, {
            'success': True,
            'message': 'New verification code sent to your email',
            'resend_cooldown': getattr(settings, 'OTP_RESEND_COOLDOWN_SECONDS', 60)
        }

    @classmethod
    def logout_user(cls, user: User, request: HttpRequest) -> None:
        """
        Log out a user.

        Args:
            user: User to log out
            request: Django request object
        """
        # Log logout
        AuditService.log_action(
            user=user,
            action='LOGOUT',
            details={'email': user.email},
            request=request
        )

        # Clear session
        logout(request)

    @classmethod
    def change_password(
            cls,
            user: User,
            current_password: str,
            new_password: str,
            request: HttpRequest
    ) -> Tuple[bool, str]:
        """
        Change user password.

        Args:
            user: User changing password
            current_password: Current password
            new_password: New password
            request: Django request object

        Returns:
            Tuple: (success, message)
        """
        # Verify current password
        if not check_password(current_password, user.password):
            return False, "Current password is incorrect"

        # Validate new password
        min_length = getattr(settings, 'PASSWORD_MIN_LENGTH', 8)
        if len(new_password) < min_length:
            return False, f"Password must be at least {min_length} characters"

        # Change password
        user.set_password(new_password)
        user.password_change_required = False
        user.save()

        # Log password change
        AuditService.log_action(
            user=user,
            action='PASSWORD_CHANGED',
            details={'email': user.email},
            request=request
        )

        return True, "Password changed successfully"

    @classmethod
    def _is_account_locked(cls, user: User) -> Tuple[bool, Optional[str]]:
        """Check if account is currently locked."""
        if user.locked_until and user.locked_until > timezone.now():
            remaining = user.locked_until - timezone.now()
            minutes = int(remaining.total_seconds() // 60)
            return True, f"Account locked for {minutes} minutes"
        if user.locked_until and user.locked_until <= timezone.now():
            user.failed_login_attempts = 0
            user.locked_until = None
            user.save(update_fields=['failed_login_attempts', 'locked_until'])
        return False, None

    @classmethod
    def _handle_failed_login(cls, user: User) -> None:
        """Handle a failed login attempt."""
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= cls.MAX_FAILED_ATTEMPTS:
            user.locked_until = timezone.now() + timezone.timedelta(minutes=cls.LOCKOUT_DURATION_MINUTES)
        user.save(update_fields=['failed_login_attempts', 'locked_until'])

    @classmethod
    def _handle_successful_login(cls, user: User) -> None:
        """Handle a successful login attempt."""
        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_login = timezone.now()
        user.save(update_fields=['failed_login_attempts', 'locked_until', 'last_login'])

    @classmethod
    def _is_trusted_device(cls, request: HttpRequest, user: User) -> bool:
        """Check if device is trusted for user."""
        fingerprint = cls._generate_device_fingerprint(request)
        devices = user.trusted_devices if isinstance(user.trusted_devices, list) else []
        for device in devices:
            if not isinstance(device, dict):
                continue
            if device.get('fingerprint') == fingerprint:
                expires_at = device.get('expires_at')
                if expires_at:
                    try:
                        if timezone.now() < datetime.fromisoformat(expires_at):
                            return True
                    except (ValueError, TypeError):
                        continue
        return False

    @classmethod
    def _add_trusted_device(cls, request: HttpRequest, user: User) -> None:
        """Add current device as trusted for 30 days."""
        fingerprint = cls._generate_device_fingerprint(request)
        devices = user.trusted_devices if isinstance(user.trusted_devices, list) else []
        if len(devices) >= 10:
            devices = devices[-9:]
        devices.append({
            'fingerprint': fingerprint,
            'expires_at': (timezone.now() + timezone.timedelta(days=30)).isoformat(),
            'created_at': timezone.now().isoformat(),
            'device_name': request.META.get('HTTP_USER_AGENT', 'Unknown')[:50],
            'ip_address': request.META.get('REMOTE_ADDR', '')
        })
        user.trusted_devices = devices
        user.save(update_fields=['trusted_devices'])

    @classmethod
    def _generate_device_fingerprint(cls, request: HttpRequest) -> str:
        """Generate a unique device fingerprint."""
        import hashlib
        components = [
            request.META.get('HTTP_USER_AGENT', ''),
            request.META.get('HTTP_ACCEPT_LANGUAGE', ''),
            request.META.get('HTTP_ACCEPT_ENCODING', ''),
            request.META.get('REMOTE_ADDR', '').split(',')[0],
            settings.SECRET_KEY[:10],
        ]
        return hashlib.sha256(''.join(components).encode()).hexdigest()

    @classmethod
    def _can_resend_otp(cls, user: User) -> Tuple[bool, Optional[str], Optional[int]]:
        """Check if user can resend OTP."""
        MAX_RESENDS = 5
        RESEND_COOLDOWN = 60

        if user.otp_resend_count >= MAX_RESENDS:
            return False, "Maximum OTP resend limit reached. Please try again later.", None

        if user.otp_last_resend:
            elapsed = (timezone.now() - user.otp_last_resend).total_seconds()
            if elapsed < RESEND_COOLDOWN:
                wait = RESEND_COOLDOWN - elapsed
                return False, f"Please wait {wait} seconds before requesting another OTP", wait

        return True, None, None

    @classmethod
    def _mark_otp_resend(cls, user: User) -> None:
        """Mark that an OTP was resent."""
        user.otp_resend_count += 1
        user.otp_last_resend = timezone.now()
        user.save(update_fields=['otp_resend_count', 'otp_last_resend'])