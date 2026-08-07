"""
Checkout form with validation for Kenyan addresses and phone numbers.
Caldan Construction - "Building Kenya's Future, One Project at a Time."
"""

from django import forms
from django.core.exceptions import ValidationError


class CheckoutForm(forms.Form):
    """
    Form for collecting client information during checkout.
    Includes Kenyan phone number and address validation.
    """

    # Client Information
    name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Full Name',
            'required': True,
        }),
        label='Full Name',
    )

    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Email Address',
            'required': True,
        }),
        label='Email Address',
        help_text='We\'ll send order confirmation to this email',
    )

    phone = forms.CharField(
        max_length=15,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '0712345678',
            'required': True,
        }),
        label='Phone Number',
        help_text='We\'ll use this for delivery updates',
    )

    # Delivery Address
    address = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g. 123 Main Street, Westlands',
            'required': True,
        }),
        label='Delivery Address',
    )

    county = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g. Nairobi',
            'required': True,
        }),
        label='County',
    )

    town = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g. Westlands',
            'required': True,
        }),
        label='Town/City',
    )

    # Additional Notes
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Special delivery instructions or additional notes...',
        }),
        label='Order Notes',
    )

    def clean_phone(self):
        """Validate and format Kenyan phone number."""
        phone = self.cleaned_data.get('phone', '')
        phone = ''.join(c for c in phone if c.isdigit() or c == '+')

        if not phone:
            raise ValidationError('Phone number is required.')

        if phone.startswith('+254'):
            if len(phone) != 13:
                raise ValidationError('Invalid Kenyan phone number. Format: +2547XXXXXXXX')
        elif phone.startswith('0'):
            if len(phone) != 10:
                raise ValidationError('Invalid Kenyan phone number. Format: 07XXXXXXXX')
            phone = '+254' + phone[1:]
        elif len(phone) == 9 and phone.startswith('7'):
            phone = '+254' + phone
        elif len(phone) == 9 and phone.startswith('1'):
            phone = '+254' + phone
        else:
            raise ValidationError('Invalid phone number. Use Kenyan format: 07XXXXXXXX or +2547XXXXXXXX')

        return phone

    def clean_email(self):
        """Validate email format."""
        email = self.cleaned_data.get('email', '').strip().lower()
        if not email:
            raise ValidationError('Email address is required.')
        return email

    def clean(self):
        """Validate that required fields are filled."""
        cleaned_data = super().clean()
        name = cleaned_data.get('name')
        address = cleaned_data.get('address')
        county = cleaned_data.get('county')
        town = cleaned_data.get('town')

        if not name:
            self.add_error('name', 'Full name is required.')

        if not address:
            self.add_error('address', 'Delivery address is required.')

        if not county:
            self.add_error('county', 'County is required.')

        if not town:
            self.add_error('town', 'Town/City is required.')

        return cleaned_data