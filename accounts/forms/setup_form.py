"""
Setup Form - First-time admin creation.

This form handles the creation of the Chief Admin account
during the initial platform setup.
"""

from django import forms
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.conf import settings

from accounts.models import User


class SetupForm(forms.Form):
    """
    Form for creating the Chief Admin during setup.
    """

    email = forms.EmailField(
        label=_('Email Address'),
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'admin@caldanconstruction.com',
            'autofocus': True,
        }),
        help_text=_('This will be your login email.')
    )

    full_name = forms.CharField(
        label=_('Full Name'),
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'John Doe',
        }),
        help_text=_('Your full name as it will appear in the system.')
    )

    phone = forms.CharField(
        label=_('Phone Number'),
        max_length=15,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '0712345678 or 0112345678',
        }),
        help_text=_('Kenyan phone number (e.g. 0712345678 or 0112345678).')
    )

    password = forms.CharField(
        label=_('Password'),
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
        label=_('Confirm Password'),
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': '••••••••',
        }),
        help_text=_('Enter the same password as above.')
    )

    def clean_email(self):
        """
        Validate that email is not already in use.
        """
        email = self.cleaned_data.get('email', '').lower().strip()

        if User.objects.filter(email=email).exists():
            raise ValidationError(_('A user with this email already exists.'))

        return email

    def clean_phone(self):
        """
        Validate phone number format.

        Accepts Kenyan numbers in any of these forms:
        - 07XXXXXXXX or 01XXXXXXXX  (10 digits, leading 0 + prefix 1 or 7)
        - 7XXXXXXXX or 1XXXXXXXX    (9 digits, prefix 1 or 7 — common when typing)
        - 2547XXXXXXXX or 2541XXXXXXXX  (12 digits, international 254 prefix)
        """
        phone = self.cleaned_data.get('phone', '').strip()

        # Strip everything non-digit (spaces, dashes, parens, leading +)
        phone = ''.join(filter(str.isdigit, phone))

        if not phone:
            raise ValidationError(_('Please enter a valid Kenyan phone number.'))

        # Normalise to the local 0X format
        if len(phone) == 9 and phone[0] in {'1', '7'}:
            phone = '0' + phone
        elif len(phone) == 10 and phone[0] == '0' and phone[1] in {'1', '7'}:
            pass  # already in local form
        elif len(phone) == 12 and phone.startswith('254') and phone[3] in {'1', '7'}:
            phone = '0' + phone[3:]
        else:
            raise ValidationError(_('Please enter a valid Kenyan phone number.'))

        return phone

    def clean(self):
        """
        Validate that passwords match.
        """
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')

        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', _('Passwords do not match.'))

        return cleaned_data