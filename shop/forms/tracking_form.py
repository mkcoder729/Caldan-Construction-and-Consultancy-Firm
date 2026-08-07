"""
Tracking Form - Order tracking with email verification.
Caldan Construction - "Building Kenya's Future, One Project at a Time."
"""

from django import forms
from django.core.exceptions import ValidationError

from shop.models import Order


class OrderTrackingForm(forms.Form):
    """
    Form for tracking orders with email verification.
    """
    order_number = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter order number (e.g., ORD-2026-A7F3K9)',
            'required': True,
        }),
        label='Order Number'
    )

    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email address',
            'required': True,
        }),
        label='Email Address',
        help_text='We\'ll send a verification code to this email.'
    )

    def clean(self):
        """Validate that the email matches the order."""
        cleaned_data = super().clean()
        order_number = cleaned_data.get('order_number')
        email = cleaned_data.get('email')

        if order_number and email:
            try:
                order = Order.objects.get(order_number=order_number)
                if not order.verify_email(email):
                    raise ValidationError('The email address does not match this order. Please check and try again.')
                cleaned_data['order'] = order
            except Order.DoesNotExist:
                raise ValidationError('Order not found. Please check your order number.')

        return cleaned_data