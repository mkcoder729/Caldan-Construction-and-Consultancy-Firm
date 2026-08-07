"""
Forms for the accounts app.

This module contains all forms for authentication, user management,
and admin invitations.
"""

from accounts.forms.setup_form import SetupForm
from accounts.forms.auth_form import LoginForm, OTPForm
from accounts.forms.invitation_form import InviteAdminForm, AcceptInvitationForm
from accounts.forms.profile_form import ProfileForm
from accounts.forms.password_form import ChangePasswordForm

__all__ = [
    'SetupForm',
    'LoginForm',
    'OTPForm',
    'InviteAdminForm',
    'AcceptInvitationForm',
    'ProfileForm',
    'ChangePasswordForm',
]