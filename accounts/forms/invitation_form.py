"""
Invitation Forms - Admin invitations.

This module contains forms for creating and accepting admin invitations.
"""

from django import forms
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.conf import settings

from accounts.models import User, AdminInvitation


# ============================================================================
# Helpers
# ============================================================================

def normalize_kenyan_phone(phone: str) -> str:
    """
    Accepts Kenyan numbers in any of these forms:
        - 07XXXXXXXX or 01XXXXXXXX  (10 digits, leading 0 + prefix 1 or 7)
        - 7XXXXXXXX or 1XXXXXXXX    (9 digits, prefix 1 or 7 — common when typing)
        - 2547XXXXXXXX or 2541XXXXXXXX  (12 digits, international 254 prefix)

    Returns the value normalised to the local ``0X`` form, or raises
    ``ValidationError`` if the input doesn't match.
    """
    if not phone:
        return ''

    # Strip everything non-digit (spaces, dashes, parens, leading +)
    digits = ''.join(filter(str.isdigit, phone))

    if not digits:
        raise ValidationError(_('Please enter a valid Kenyan phone number.'))

    if len(digits) == 9 and digits[0] in {'1', '7'}:
        return '0' + digits
    if len(digits) == 10 and digits[0] == '0' and digits[1] in {'1', '7'}:
        return digits
    if len(digits) == 12 and digits.startswith('254') and digits[3] in {'1', '7'}:
        return '0' + digits[3:]

    raise ValidationError(_('Please enter a valid Kenyan phone number.'))


class InviteAdminForm(forms.Form):
    """
    Form for inviting a new platform admin.
    """

    email = forms.EmailField(
        label=_('Email Address'),
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'admin@example.com',
            'autocomplete': 'email',
            'inputmode': 'email',
        }),
        help_text=_('The email address of the person you want to invite.')
    )

    def clean_email(self):
        """
        Validate that email is not already in use and no valid invitation exists.
        """
        email = self.cleaned_data.get('email', '').lower().strip()

        # Check if user already exists
        if User.objects.filter(email=email).exists():
            raise ValidationError(_('A user with this email already exists.'))

        # Check if there's already a valid invitation
        from accounts.services.invitation_service import InvitationService
        invitations = InvitationService.get_invitations_by_email(email)

        if invitations:
            # Check if any are still valid
            for invitation in invitations:
                if not invitation.is_expired() and not invitation.is_accepted:
                    raise ValidationError(
                        _('An invitation has already been sent to this email.')
                    )

        return email


class AcceptInvitationForm(forms.Form):
    """
    Form for accepting an admin invitation.
    """

    email = forms.EmailField(
        label=_('Email Address'),
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'readonly': True,
        }),
        help_text=_('This email is associated with the invitation.')
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Pre-populate email if provided as initial
        if self.initial and 'email' in self.initial:
            self.fields['email'].initial = self.initial['email']

    def clean_phone(self):
        """Validate and normalise the Kenyan phone number."""
        phone = self.cleaned_data.get('phone', '').strip()
        return normalize_kenyan_phone(phone)

    def clean(self):
        """
        Cross-field validation hook (kept for future extensions).
        Password is no longer collected here — the system generates one
        and emails it; the invitee is forced to change it on first
        login.
        """
        return super().clean()


class InvitationDetailsAdminForm(forms.Form):
    """
    Step-2 form for the inline admin invite card.

    The chief has already entered an email (step 1). This form collects
    the recruitment details (name, phone, role, initial permissions,
    delivery channels, and an optional personal message) and submits
    alongside the pre-validated email from step 1.
    """

    full_name = forms.CharField(
        label=_('Full name'),
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Jane Wanjiku',
            'autocomplete': 'name',
            'id': 'id_full_name',
        }),
        help_text=_('Optional — pre-fills the acceptance page if provided.'),
    )

    phone = forms.CharField(
        label=_('Phone number'),
        max_length=15,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '0712 345 678',
            'inputmode': 'tel',
            'autocomplete': 'tel',
            'id': 'id_phone',
        }),
        help_text=_('Optional — Kenyan format (0712345678, +2547…, etc.). Required to send via SMS.'),
    )

    role = forms.ChoiceField(
        label=_('Role'),
        choices=[(User.Role.PLATFORM_ADMIN, _('Platform Admin'))],
        initial=User.Role.PLATFORM_ADMIN,
        widget=forms.Select(attrs={'class': 'form-control', 'id': 'id_role'}),
        help_text=_('Chief Admins can only be created via the management command — never via invitation.'),
    )

    permissions = forms.MultipleChoiceField(
        label=_('Initial permissions'),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        choices=[],   # populated in __init__ from PermissionService
        help_text=_('Toggles the new admin will start with. Skip to use the defaults.'),
    )

    channels = forms.MultipleChoiceField(
        label=_('Delivery channels'),
        choices=[
            ('email', _('Email')),
            ('sms', _('SMS')),
        ],
        initial=['email'],
        widget=forms.CheckboxSelectMultiple(
            attrs={'id': 'id_channels'}
        ),
        help_text=_('Where to deliver the invitation. Email is selected by default.'),
    )

    personal_message = forms.CharField(
        label=_('Personal message'),
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'maxlength': '500',
            'placeholder': "Optional — 'Welcome to the team! Looking forward to working with you.'",
            'id': 'id_personal_message',
        }),
        help_text=_('Optional — appears in the invitation email. Up to 500 characters.'),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Lazy import: PermissionService imports settings, and the form
        # may be imported before the app registry is fully loaded at
        # module import time in some test harnesses.
        from accounts.services.permission_service import PermissionService

        available = PermissionService.get_available_permissions()
        self.fields['permissions'].choices = [
            (p['key'], p['label']) for p in available
        ]

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------
    def clean_phone(self):
        """Validate and normalise the Kenyan phone number (when present)."""
        phone = (self.cleaned_data.get('phone') or '').strip()
        if not phone:
            return ''
        return normalize_kenyan_phone(phone)

    def clean_channels(self):
        channels = self.cleaned_data.get('channels') or []
        if not channels:
            raise ValidationError(_('Select at least one delivery channel.'))
        return list(channels)

    def clean(self):
        cleaned = super().clean()

        channels = cleaned.get('channels') or []
        phone = cleaned.get('phone') or ''

        # If SMS is selected but no phone is provided, drop the SMS
        # choice silently and tell the chief. We don't raise — they
        # may have just forgotten to fill the phone field.
        if 'sms' in channels and not phone:
            cleaned['channels'] = [c for c in channels if c != 'sms']
            self.add_error(
                'phone',
                _('A phone number is required to deliver via SMS. '
                  'SMS has been removed from your channel selection.'),
            )

        # Must end up with at least one channel.
        if not cleaned.get('channels'):
            self.add_error(
                'channels',
                _('Select at least one delivery channel (Email or SMS).'),
            )

        return cleaned