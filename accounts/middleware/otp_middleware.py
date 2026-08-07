"""
OTP Middleware - Handles OTP verification redirection.

This middleware ensures that users are redirected to OTP verification
if they haven't completed it after login.
"""

import logging
from django.shortcuts import redirect
from django.urls import reverse

logger = logging.getLogger('caldan')


class OTPMiddleware:
    """
    OTP middleware for enforcing OTP verification.

    Features:
    - Redirects to OTP verification if required
    - Allows access to OTP-related pages
    """

    # URLs that should bypass OTP check
    OTP_BYPASS_URLS = [
        '/accounts/login/',
        '/accounts/verify-otp/',
        '/accounts/resend-otp/',
        '/accounts/logout/',
        '/accounts/setup/',
        '/accept-invite/',
        '/accounts/password-reset/',
        '/accounts/password-reset-done/',
        '/accounts/password-reset-confirm/',
        '/accounts/password-reset-complete/',
        '/accounts/account-locked/',
        '/api/auth/',
        '/health/',
        '/static/',
        '/media/',
    ]

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Check if user is authenticated
        if request.user.is_authenticated:
            # Get current path
            path = request.path_info

            # Check if OTP is required
            if self._requires_otp_verification(request, request.user, path):
                # Store the original URL to redirect back after OTP
                request.session['otp_redirect_url'] = path

                # Check if user is already on OTP page
                if not path.startswith('/accounts/verify-otp/'):
                    return redirect('accounts:otp_verify')

        response = self.get_response(request)
        return response

    def _requires_otp_verification(self, request, user, path: str) -> bool:
        """
        Check if user needs to verify OTP.

        Args:
            request: The current HTTP request (provides session access)
            user: The user object
            path: The current URL path

        Returns:
            bool: True if OTP verification is required
        """
        # Skip if email is already verified
        if user.is_email_verified:
            return False

        # Skip if user is Chief Admin (they created the account during setup)
        if user.is_chief:
            return False

        # Skip if user is on OTP bypass URLs
        for url in self.OTP_BYPASS_URLS:
            if path == url or path.startswith(url):
                return False

        # Check if OTP session exists
        if 'otp_user_id' in request.session:
            # Check if this is the same user
            if request.session.get('otp_user_id') == user.id:
                return True

        # If user has OTP code hash, they need to verify
        if user.otp_code_hash:
            return True

        # Default: require OTP if email not verified
        return not user.is_email_verified