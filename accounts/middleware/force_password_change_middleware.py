"""
Force Password Change Middleware - Enforces password change on first login.

This middleware ensures that users are redirected to change their password
if required (e.g., first login or admin-enforced password reset). When the
flag is set we redirect to the dashboard, which renders an un-closable
modal that submits the change-password form in place.
"""

import logging
from django.shortcuts import redirect
from django.urls import reverse

logger = logging.getLogger('caldan')


class PasswordChangeRequiredMiddleware:
    """
    Middleware to force password change on first login.

    Features:
    - Redirects to dashboard (where the force-change-password modal lives)
    - Allows access to bypass URLs so the modal form can submit
    """

    # URLs that should bypass password change check
    BYPASS_URLS = [
        '/accounts/change-password/',
        '/dashboard/settings/change-password/',
        '/accounts/logout/',
        '/accounts/profile/',
        '/accounts/password-reset/',
        '/accounts/password-reset-done/',
        '/accounts/password-reset-confirm/',
        '/accounts/password-reset-complete/',
        '/admin/',
        '/static/',
        '/media/',
        # The dashboard itself renders the force-change modal, so the
        # request must reach the view instead of being redirected back
        # to /dashboard/ (which would loop forever).
        '/dashboard/',
    ]

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Check if user is authenticated
        if request.user.is_authenticated:
            # Get current path
            path = request.path_info

            # Check if password change is required
            if request.user.password_change_required:
                # Skip if on bypass URLs (so the modal form can submit)
                for url in self.BYPASS_URLS:
                    if path == url or path.startswith(url):
                        break
                else:
                    # Redirect to dashboard so the force-change modal can render
                    return redirect('dashboard:overview')

        response = self.get_response(request)
        return response