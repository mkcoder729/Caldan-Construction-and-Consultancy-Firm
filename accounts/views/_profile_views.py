"""
Profile Views - User profile management.

This module handles profile viewing, editing, and password changes
for authenticated users.
"""

import logging
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views import View
from django.utils.decorators import method_decorator

from accounts.forms.profile_form import ProfileForm
from accounts.forms.password_form import ChangePasswordForm
from accounts.models.audit import AuditLog
from accounts.services.auth_service import AuthService
from accounts.services.audit_service import AuditService

logger = logging.getLogger('caldan')


@method_decorator(login_required, name='dispatch')
class ProfileView(View):
    """
    View user profile.
    """

    def get(self, request):
        """
        Display user profile.
        """
        user = request.user
        profile = user.profile if hasattr(user, 'profile') else None

        context = {
            'user': user,
            'profile': profile,
            'page_title': 'My Profile - Caldan Construction and Consultancy Firm',
        }
        return render(request, 'accounts/dashboard/admin/profile.html', context)


@method_decorator(login_required, name='dispatch')
class ProfileUpdateView(View):
    """
    Update user profile.
    """

    def get(self, request):
        """
        Display profile update form.
        """
        form = ProfileForm(instance=request.user)

        context = {
            'form': form,
            'page_title': 'Edit Profile - Caldan Construction and Consultancy Firm',
        }
        return render(request, 'accounts/dashboard/admin/profile_edit.html', context)

    def post(self, request):
        """
        Process profile update.
        """
        form = ProfileForm(request.POST, request.FILES, instance=request.user)

        if form.is_valid():
            user = form.save()

            # Log profile update
            AuditService.log_action(
                user=user,
                action=AuditLog.Action.USER_UPDATED,
                entity_type='User',
                entity_id=user.id,
                details={
                    'email': user.email,
                    'fields_updated': list(form.changed_data),
                },
                request=request
            )

            messages.success(request, 'Profile updated successfully!')
            return redirect('accounts:profile')

        return render(request, 'accounts/dashboard/admin/profile_edit.html', {'form': form})


@method_decorator(login_required, name='dispatch')
class ChangePasswordView(View):
    """
    Change user password.
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

            success, message = AuthService.change_password(
                user=request.user,
                current_password=current_password,
                new_password=new_password,
                request=request
            )

            if success:
                messages.success(request, message)
                return redirect('accounts:profile')
            else:
                messages.error(request, message)
                return render(request, 'accounts/dashboard/admin/change_password.html', {'form': form})

        return render(request, 'accounts/dashboard/admin/change_password.html', {'form': form})