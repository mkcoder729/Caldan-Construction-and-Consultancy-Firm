"""
Authentication Forms - Login and OTP verification.

This module contains forms for user authentication including
login and OTP verification.
"""

from django import forms
from django.utils.translation import gettext_lazy as _
from django.conf import settings

from accounts.services.otp_service import OTPService


class LoginForm(forms.Form):
    """
    Login form with email, password, and remember me option.
    """

    email = forms.EmailField(
        label=_('Email Address'),
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'admin@caldanconstruction.com',
            'autofocus': True,
        })
    )

    password = forms.CharField(
        label=_('Password'),
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': '••••••••',
        })
    )

    remember_me = forms.BooleanField(
        label=_('Remember this device'),
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
        }),
        help_text=_('Stay logged in on this device for 30 days.')
    )

    def clean_email(self):
        """
        Normalize email address.
        """
        email = self.cleaned_data.get('email', '').lower().strip()
        return email


class OTPForm(forms.Form):
    """
    OTP verification form.
    """

    otp_code = forms.CharField(
        label=_('Verification Code'),
        max_length=settings.OTP_LENGTH,
        min_length=settings.OTP_LENGTH,
        widget=forms.TextInput(attrs={
            'class': 'form-control text-center',
            'placeholder': '12345678',
            'autofocus': True,
            'maxlength': settings.OTP_LENGTH,
            'minlength': settings.OTP_LENGTH,
        }),
        help_text=_(
            f'Enter the 8-digit verification code sent to your email. '
            f'Valid for {settings.OTP_EXPIRY_MINUTES} minutes.'
        )
    )

    def clean_otp_code(self):
        """
        Validate OTP code format.
        """
        otp_code = self.cleaned_data.get('otp_code', '').strip()

        # Remove any whitespace
        otp_code = otp_code.replace(' ', '').replace('-', '')

        # Validate format
        if not OTPService.validate_otp_code(otp_code):
            raise forms.ValidationError(
                _(f'Please enter exactly {settings.OTP_LENGTH} digits.')
            )

        return otp_code