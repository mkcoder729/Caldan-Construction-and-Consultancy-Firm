"""
Authentication Views - Login, OTP, Logout.

This module handles all authentication views including login,
OTP verification, logout, and account lockout.
"""

import logging
from django.shortcuts import render, redirect
from django.contrib import messages
from django.views import View
from django.contrib.auth import login, logout
from django.utils import timezone
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_http_methods

from accounts.services.auth_service import AuthService
from accounts.services.otp_service import OTPService
from accounts.services.audit_service import AuditService
from accounts.models import User
from accounts.models.audit import AuditLog

logger = logging.getLogger('caldan')


class LoginView(View):
    """Login page view."""

    def get(self, request):
        if request.user.is_authenticated:
            return redirect('dashboard:overview')
        return render(request, 'accounts/shared/login.html')

    def post(self, request):
        email = request.POST.get('email')
        password = request.POST.get('password')
        remember_me = request.POST.get('remember_me') == 'on'

        # Validate input
        if not email or not password:
            messages.error(request, 'Please provide both email and password.')
            return render(request, 'accounts/shared/login.html')

        # Authenticate
        result = AuthService.authenticate(email, password)

        if not result['success']:
            messages.error(request, result['error'])
            return render(request, 'accounts/shared/login.html')

        user = result['user']

        # Generate OTP
        otp_code = OTPService.generate_otp(user)

        # Send OTP via email
        from notifications.services.email_service import EmailService
        email_sent = EmailService.send_otp(
            user=user,
            otp_code=otp_code,
            device_info=request.META.get('HTTP_USER_AGENT', ''),
            ip_address=request.META.get('REMOTE_ADDR', '')
        )

        if not email_sent:
            messages.error(request, 'Failed to send verification code. Please try again.')
            return render(request, 'accounts/shared/login.html')

        # Log OTP sent
        AuditService.log_action(
            user=user,
            action=AuditLog.Action.OTP_SENT,
            details={'email': user.email},
            request=request
        )

        # Store in session
        request.session['otp_email'] = user.email
        request.session['remember_me'] = remember_me

        messages.success(request, f"Verification code sent to {user.email}")
        return redirect('accounts:otp_verify')


class OTPVerifyView(View):
    """OTP verification page."""

    def get(self, request):
        email = request.session.get('otp_email')
        if not email:
            messages.warning(request, 'Please login first.')
            return redirect('accounts:login')
        return render(request, 'accounts/shared/otp_verify.html', {'email': email})

    def post(self, request):
        email = request.session.get('otp_email')
        if not email:
            messages.warning(request, 'Please login first.')
            return redirect('accounts:login')

        otp_code = request.POST.get('otp_code')
        remember_me = request.session.get('remember_me', False)

        if not otp_code:
            messages.error(request, 'Please enter the verification code.')
            return render(request, 'accounts/shared/otp_verify.html', {'email': email})

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            messages.error(request, 'User not found.')
            return redirect('accounts:login')

        # Verify OTP
        success, message = OTPService.verify_otp(user, otp_code)

        if not success:
            messages.error(request, message)
            return render(request, 'accounts/shared/otp_verify.html', {'email': email})

        # Login user - specify the backend
        user.backend = 'django.contrib.auth.backends.ModelBackend'
        login(request, user)

        # Set session expiry
        if remember_me:
            request.session.set_expiry(2592000)  # 30 days
        else:
            request.session.set_expiry(86400)  # 24 hours

        # Clear OTP session data
        request.session.pop('otp_email', None)
        request.session.pop('remember_me', None)

        # Log success
        AuditService.log_action(
            user=user,
            action=AuditLog.Action.LOGIN_SUCCESS,
            details={'ip': request.META.get('REMOTE_ADDR', '')},
            request=request
        )

        messages.success(request, f"Welcome back, {user.full_name}!")
        return redirect('dashboard:overview')


@method_decorator(login_required, name='dispatch')
class LogoutView(View):
    """Logout view."""

    def get(self, request):
        AuditService.log_action(
            user=request.user,
            action=AuditLog.Action.LOGOUT,
            request=request
        )
        logout(request)
        messages.success(request, "You have been logged out successfully.")
        return redirect('accounts:login')


@method_decorator(login_required, name='dispatch')
@method_decorator(require_http_methods(['GET', 'POST']), name='dispatch')
class LogoutAllView(View):
    """
    Log out the user from every device except the current one.
    Deletes every DB session row whose session_key is not the current one.
    """

    def get(self, request):
        return self._handle(request)

    def post(self, request):
        return self._handle(request)

    def _handle(self, request):
        from django.contrib.sessions.models import Session
        current_key = request.session.session_key
        # Capture all session keys for this user
        user_sessions = Session.objects.filter(expire_date__gte=timezone.now())
        deleted = 0
        for s in user_sessions:
            try:
                data = s.get_decoded()
                if data.get('_auth_user_id') == str(request.user.id) and s.session_key != current_key:
                    s.delete()
                    deleted += 1
            except Exception:
                continue

        AuditService.log_action(
            user=request.user,
            action=AuditLog.Action.LOGOUT,
            request=request,
            details={'logout_all': True, 'sessions_cleared': deleted},
        )
        if deleted:
            messages.success(request, f'Logged out of {deleted} other session(s).')
        else:
            messages.info(request, 'No other active sessions to log out.')
        return redirect('dashboard:overview')


class ResendOTPView(View):
    """Resend OTP view."""

    def post(self, request):
        email = request.session.get('otp_email')
        if not email:
            messages.warning(request, 'Please login first.')
            return redirect('accounts:login')

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            messages.error(request, 'User not found.')
            return redirect('accounts:login')

        # Check resend limit (the User model auto-resets hourly on its own)
        if user.otp_resend_count >= 8:
            messages.error(request, "You have exceeded the OTP resend limit. Please try again later.")
            return redirect('accounts:login')

        # Generate new OTP
        otp_code = OTPService.generate_otp(user)

        # Send OTP via email
        from notifications.services.email_service import EmailService
        email_sent = EmailService.send_otp(
            user=user,
            otp_code=otp_code,
            device_info=request.META.get('HTTP_USER_AGENT', ''),
            ip_address=request.META.get('REMOTE_ADDR', '')
        )

        if not email_sent:
            messages.error(request, 'Failed to send verification code. Please try again.')
            return render(request, 'accounts/shared/otp_verify.html', {'email': email})

        # Update resend count
        user.otp_resend_count += 1
        user.otp_last_resend = timezone.now()
        user.save()

        messages.success(request, f"New verification code sent to {user.email}")
        return redirect('accounts:otp_verify')


class AccountLockedView(View):
    """Account locked page."""

    def get(self, request):
        return render(request, 'accounts/shared/account_locked.html')