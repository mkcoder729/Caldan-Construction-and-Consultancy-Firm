"""
Password Forms - Password change and reset.

This module contains forms for changing and resetting passwords.
"""

from django import forms
from django.contrib.auth.password_validation import validate_password
from django.utils.translation import gettext_lazy as _
from django.conf import settings


class ChangePasswordForm(forms.Form):
    """
    Form for changing password.
    """

    current_password = forms.CharField(
        label=_('Current Password'),
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': '••••••••',
        }),
        help_text=_('Enter your current password.')
    )

    new_password = forms.CharField(
        label=_('New Password'),
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': '••••••••',
        }),
        help_text=_(
            f'Must be at least {getattr(settings, "PASSWORD_MIN_LENGTH", 8)} characters '
            'and contain at least one letter and one number.'
        ),
        validators=[validate_password]
    )

    confirm_password = forms.CharField(
        label=_('Confirm New Password'),
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': '••••••••',
        }),
        help_text=_('Enter the same password as above.')
    )

    def clean(self):
        """
        Validate that passwords match.
        """
        cleaned_data = super().clean()
        new_password = cleaned_data.get('new_password')
        confirm_password = cleaned_data.get('confirm_password')

        if new_password and confirm_password and new_password != confirm_password:
            self.add_error('confirm_password', _('Passwords do not match.'))

        return cleaned_data