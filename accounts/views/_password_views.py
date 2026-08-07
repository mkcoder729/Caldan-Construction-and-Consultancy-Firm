"""
Password Views - Password change functionality.

This module handles password changes for authenticated users.
"""

import logging
from django.shortcuts import render, redirect
from django.contrib import messages
from django.views import View
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.contrib.auth import update_session_auth_hash

from accounts.forms.password_form import ChangePasswordForm
from accounts.models.audit import AuditLog
from accounts.services.audit_service import AuditService

logger = logging.getLogger('caldan')


@method_decorator(login_required, name='dispatch')
class ChangePasswordView(View):
    """
    Change password view.
    """

    def get(self, request):
        """
        Display password change form.
        """
        form = ChangePasswordForm()
        context = {
            'form': form,
            'page_title': 'Change Password - Caldan Construction and Consultancy Firm',
        }
        return render(request, 'accounts/dashboard/admin/change_password.html', context)

    def post(self, request):
        """
        Process password change.
        """
        form = ChangePasswordForm(request.POST)

        if form.is_valid():
            current_password = form.cleaned_data['current_password']
            new_password = form.cleaned_data['new_password']

            # Check current password
            if not request.user.check_password(current_password):
                messages.error(request, 'Current password is incorrect.')
                return render(request, 'accounts/dashboard/admin/change_password.html', {'form': form})

            # Set new password
            request.user.set_password(new_password)
            request.user.password_change_required = False
            request.user.save()

            # Update session to prevent logout
            update_session_auth_hash(request, request.user)

            # Log password change
            AuditService.log_action(
                user=request.user,
                action=AuditLog.Action.PASSWORD_CHANGED,
                details={'email': request.user.email},
                request=request
            )

            messages.success(request, 'Password changed successfully!')
            return redirect('accounts:profile')

        return render(request, 'accounts/dashboard/admin/change_password.html', {'form': form})