"""
Order status form for admin order management.
Caldan Construction - "Building Kenya's Future, One Project at a Time."
"""

from django import forms

from shop.models import Order


class OrderStatusForm(forms.Form):
    """
    Form for updating order status in admin dashboard.
    Includes tracking number and admin notes.
    """

    status = forms.ChoiceField(
        choices=Order.Status.choices,
        widget=forms.Select(attrs={
            'class': 'form-control',
            'required': True,
        }),
        label='Order Status',
    )

    tracking_number = forms.CharField(
        required=False,
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g. TRK-2026-001',
        }),
        label='Tracking Number',
        help_text='Enter tracking number if shipping the order',
    )

    estimated_delivery = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
        }),
        label='Estimated Delivery Date',
    )

    admin_notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Internal notes about this order...',
        }),
        label='Admin Notes',
    )

    send_notification = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
        }),
        label='Send Email Notification to Customer',
        help_text='Notify the customer about this status change',
    )

    def clean_tracking_number(self):
        """Clean tracking number."""
        tracking = self.cleaned_data.get('tracking_number', '').strip()
        if tracking:
            # Auto-format if empty
            if not tracking.startswith('TRK-'):
                tracking = f"TRK-{tracking}"
        return tracking

    def clean(self):
        """Validate status transitions."""
        cleaned_data = super().clean()
        status = cleaned_data.get('status')

        # If status is SHIPPED or DELIVERED, tracking number is required
        if status in ['SHIPPED', 'DELIVERED']:
            tracking = cleaned_data.get('tracking_number')
            if not tracking:
                self.add_error('tracking_number', 'Tracking number is required when shipping or delivering an order.')

        return cleaned_data