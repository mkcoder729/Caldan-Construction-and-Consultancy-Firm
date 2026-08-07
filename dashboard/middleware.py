from django.shortcuts import redirect
from django.urls import reverse
from django.conf import settings


class DashboardAccessMiddleware:
    """
    Middleware to ensure users accessing dashboard are properly authenticated.
    Redirects non-authenticated users to login.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Skip for public URLs
        public_urls = [
            reverse('website:index'),
            reverse('accounts:login'),
            reverse('accounts:otp_verify'),
            reverse('accounts:password_reset'),
            reverse('accounts:setup'),
        ]

        # Check if current path is dashboard
        if request.path.startswith('/dashboard/'):
            if not request.user.is_authenticated:
                return redirect('accounts:login')

            # Check if user has admin access
            if not (request.user.is_staff or request.user.is_superuser):
                return redirect('website:index')

        response = self.get_response(request)
        return response


class DashboardContextMiddleware:
    """
    Injects dashboard context data into all dashboard requests.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Add dashboard-specific headers
        if request.path.startswith('/dashboard/'):
            response['X-Dashboard-Version'] = getattr(settings, 'DASHBOARD_VERSION', '1.0')

        return response