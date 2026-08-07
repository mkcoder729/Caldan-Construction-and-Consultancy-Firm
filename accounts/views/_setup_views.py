"""
Setup Views — First-time admin creation.

Flow:
    GET  /setup/                   → render form (only if no Chief Admin exists)
    POST /setup/ (valid)            → create Chief Admin, log them in, redirect to
                                     /setup-complete/ so they see the success page
    GET  /setup/ (chief exists)     → render the "setup no longer available" page
    GET  /setup-complete/           → success page (must be authenticated)
    GET  /setup/invalid/            → "setup no longer available" page (direct)
"""

import logging
from django.shortcuts import render, redirect
from django.contrib import messages
from django.views import View
from django.contrib.auth import login

from accounts.models import User
from accounts.models.audit import AuditLog
from accounts.forms.setup_form import SetupForm
from accounts.services.audit_service import AuditService

logger = logging.getLogger('caldan')


def _chief_admin_exists():
    """Return True if a Chief Admin has been provisioned."""
    return User.objects.filter(is_chief=True).exists()


class SetupView(View):
    """
    First-time setup view.

    Only reachable when no Chief Admin exists. Once the Chief Admin is created,
    this URL renders the "setup no longer available" page directly (no redirect)
    so the user sees a clear, branded explanation.
    """

    def dispatch(self, request, *args, **kwargs):
        # If a Chief Admin already exists, render the dedicated invalid page
        # immediately — no flash message, no redirect.
        if _chief_admin_exists():
            return render(request, 'accounts/setup/setup_invalid.html', status=403)

        # If somehow logged in (e.g. stale session), bounce to dashboard
        if request.user.is_authenticated:
            return redirect('dashboard:overview')

        return super().dispatch(request, *args, **kwargs)

    def get(self, request):
        """Display the setup form."""
        form = SetupForm()
        return render(request, 'accounts/setup/setup.html', {
            'form': form,
            'page_title': 'Setup — Caldan Construction and Consultancy Firm',
        })

    def post(self, request):
        """Process the setup form and hand off to the success page."""
        form = SetupForm(request.POST)

        if not form.is_valid():
            return render(request, 'accounts/setup/setup.html', {
                'form': form,
                'page_title': 'Setup — Caldan Construction and Consultancy Firm',
            })

        # Belt-and-braces: if a Chief Admin sneaks in between GET and POST (rare),
        # bail out to the invalid page rather than corrupting the platform.
        if _chief_admin_exists():
            return render(request, 'accounts/setup/setup_invalid.html', status=403)

        try:
            user = User.objects.create_superuser(
                email=form.cleaned_data['email'].lower().strip(),
                password=form.cleaned_data['password'],
                full_name=form.cleaned_data['full_name'].strip(),
                phone=form.cleaned_data['phone'].strip(),
                is_active=True,
                is_staff=True,
                is_superuser=True,
                is_chief=True,
                role=User.Role.CHIEF_ADMIN,
            )

            user.generate_admin_id()
            user.save(update_fields=['admin_id'])

            AuditService.log_action(
                user=user,
                action=AuditLog.Action.CHIEF_ADMIN_CREATED,
                entity_type='User',
                entity_id=user.id,
                details={
                    'email': user.email,
                    'role': user.role,
                    'setup_completed': True,
                },
                request=request,
            )

            # Log the Chief Admin in so the success page CTA "Go to Dashboard"
            # works immediately. ModelBackend is the safe default.
            user.backend = 'django.contrib.auth.backends.ModelBackend'
            login(request, user)
            AuditService.log_login_success(user, request)

            logger.info(f"Chief Admin created via setup: {user.email}")

        except Exception as exc:
            logger.exception("Failed to create Chief Admin during setup")
            messages.error(request, 'Failed to create the account. Please try again.')
            return render(request, 'accounts/setup/setup.html', {
                'form': form,
                'page_title': 'Setup — Caldan Construction and Consultancy Firm',
            })

        # Hand off to the success page so the user sees the celebration.
        # The page itself does the final redirect to the dashboard.
        messages.success(
            request,
            'Welcome aboard! Your Chief Admin account is ready.',
        )
        return redirect('accounts:setup_complete')


class SetupCompleteView(View):
    """
    Setup complete page — only reachable immediately after a successful setup.

    Authenticated users land here after POST /setup/. Anyone else (e.g. someone
    who bookmarked the URL) is redirected to login.
    """

    def dispatch(self, request, *args, **kwargs):
        if not _chief_admin_exists():
            # No chief admin yet => they should be on the setup form, not here
            return redirect('accounts:setup')
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        return super().dispatch(request, *args, **kwargs)

    def get(self, request):
        # Surface the chief admin's name for a personal touch
        chief = User.objects.filter(is_chief=True).first()
        return render(request, 'accounts/setup/setup_complete.html', {
            'chief': chief,
            'page_title': 'Setup Complete — Caldan Construction and Consultancy Firm',
        })


class SetupInvalidView(View):
    """
    Dedicated "setup no longer available" page.

    Reached either:
    - directly (someone bookmarks /setup/invalid/),
    - or via SetupView's dispatch when a Chief Admin already exists.
    """

    def get(self, request):
        return render(request, 'accounts/setup/setup_invalid.html', {
            'page_title': 'Setup Unavailable — Caldan Construction and Consultancy Firm',
        })
