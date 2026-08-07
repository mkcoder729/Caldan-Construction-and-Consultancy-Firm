"""
AdminEditForm — used by the chief admin to edit another admin's
profile fields (full_name, phone, email, is_active, avatar).
"""

from django import forms
from django.contrib.auth import get_user_model

User = get_user_model()


class AdminEditForm(forms.ModelForm):
    """
    Edit another admin's profile. The chief admin can change
    full_name, phone, email, and is_active. Email is checked for
    uniqueness against other users.
    """

    class Meta:
        model = User
        fields = ['full_name', 'email', 'phone', 'is_active']
        widgets = {
            'full_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Full name',
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'admin@example.com',
                'autocomplete': 'off',
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '0712345678',
                'autocomplete': 'off',
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
        }

    def clean_email(self):
        email = self.cleaned_data.get('email', '').lower().strip()
        qs = User.objects.filter(email=email)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError('A user with this email already exists.')
        return email

    def clean_phone(self):
        phone = self.cleaned_data.get('phone', '').strip()
        digits = ''.join(filter(str.isdigit, phone))
        if digits and len(digits) < 9:
            raise forms.ValidationError('Please enter a valid Kenyan phone number.')
        return phone
