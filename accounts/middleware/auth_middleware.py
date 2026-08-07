"""
Authentication Middleware - Handles session validation and login checks.

This middleware ensures that users are properly authenticated and
that their sessions are valid for accessing protected pages.
"""

import logging
from django.shortcuts import redirect
from django.urls import reverse, resolve
from django.utils import timezone

from accounts.models import User

logger = logging.getLogger('caldan')


class AuthMiddleware:
    """
    Authentication middleware for session validation and access control.

    Features:
    - Validates user session
    - Ensures user is active
    - Redirects to login for protected pages
    """

    # URLs that don't require authentication
    PUBLIC_URLS = [
        '/',
        '/accounts/login/',
        '/accounts/verify-otp/',
        '/accounts/resend-otp/',
        '/accounts/setup/',
        '/accounts/setup-complete/',
        '/accept-invite/',
        '/invite-status/',
        '/accounts/password-reset/',
        '/accounts/password-reset-done/',
        '/accounts/password-reset-confirm/',
        '/accounts/password-reset-complete/',
        '/accounts/account-locked/',
        '/shop/',
        '/services/',
        '/health/',
        '/robots.txt',
        '/manifest.json',
        '/serviceworker.js',
        '/humans.txt',
        '/security.txt',
        '/ads.txt',
    ]

    # URL prefixes that don't require authentication
    PUBLIC_PREFIXES = [
        '/api/',
        '/static/',
        '/media/',
        '/admin/',
    ]

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Get current path
        path = request.path_info

        # Check if path is public
        is_public = self._is_public_path(path)

        # If user is authenticated, validate session
        if request.user.is_authenticated:
            # Check if user is active
            if not request.user.is_active:
                # Log out inactive user
                from django.contrib.auth import logout
                logout(request)
                request.session.flush()
                return redirect('accounts:login')

            # NOTE: The `User` model does not currently carry a `last_activity`
            # field. To keep this middleware side-effect free until that lands,
            # we intentionally do NOT write last_activity here. Add the field
            # in a future migration and re-enable the update block below.
            #
            # if hasattr(request.user, 'last_activity'):
            #     request.user.last_activity = timezone.now()
            #     request.user.save(update_fields=['last_activity'])

        # Redirect to login for protected pages
        if not is_public and not request.user.is_authenticated:
            # Check if it's an API request
            if path.startswith('/api/'):
                # Return 401 for API
                from django.http import JsonResponse
                return JsonResponse(
                    {'error': 'Authentication required', 'code': 'UNAUTHORIZED'},
                    status=401
                )

            # Store the original URL to redirect back after login
            request.session['next_url'] = path

            return redirect('accounts:login')

        response = self.get_response(request)
        return response

    def _is_public_path(self, path: str) -> bool:
        """
        Check if a path is public (no authentication required).

        Args:
            path: The URL path to check

        Returns:
            bool: True if the path is public
        """
        # Check exact matches
        for url in self.PUBLIC_URLS:
            if path == url or path.startswith(url):
                return True

        # Check prefixes
        for prefix in self.PUBLIC_PREFIXES:
            if path.startswith(prefix):
                return True

        return False