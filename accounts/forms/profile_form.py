"""
Profile Forms - User profile management.

This module contains forms for updating user profiles.
"""

from django import forms
from django.utils.translation import gettext_lazy as _

from accounts.models import User


class ProfileForm(forms.ModelForm):
    """
    Form for updating user profile.
    """

    class Meta:
        model = User
        fields = ['full_name', 'phone', 'avatar']
        widgets = {
            'full_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'John Doe',
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '0712345678 or 0112345678',
            }),
            'avatar': forms.FileInput(attrs={
                'class': 'avatar-file-input',
                'accept': 'image/*',
            }),
        }
        labels = {
            'full_name': _('Full Name'),
            'phone': _('Phone Number'),
            'avatar': _('Profile Photo'),
        }
        help_texts = {
            'full_name': _('Your full name as it appears in the system.'),
            'phone': _('Kenyan phone number (e.g. 0712345678 or 0112345678).'),
            'avatar': _('PNG, JPG, or SVG. Max 10 MB.'),
        }

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
            raise forms.ValidationError(_('Please enter a valid Kenyan phone number.'))

        # Normalise to the local 0X format
        if len(phone) == 9 and phone[0] in {'1', '7'}:
            phone = '0' + phone
        elif len(phone) == 10 and phone[0] == '0' and phone[1] in {'1', '7'}:
            pass  # already in local form
        elif len(phone) == 12 and phone.startswith('254') and phone[3] in {'1', '7'}:
            phone = '0' + phone[3:]
        else:
            raise forms.ValidationError(_('Please enter a valid Kenyan phone number.'))

        return phone

    def clean_avatar(self):
        """Cap avatar at 10 MB and ensure it's a real image."""
        avatar = self.cleaned_data.get('avatar')
        if not avatar:
            return avatar
        # 10 MB ceiling
        if avatar.size > 10 * 1024 * 1024:
            raise forms.ValidationError(_('Image must be 10 MB or smaller.'))
        # Verify it's actually an image
        if hasattr(avatar, 'content_type') and avatar.content_type:
            if not avatar.content_type.startswith('image/'):
                raise forms.ValidationError(_('File must be an image.'))
        return avatar