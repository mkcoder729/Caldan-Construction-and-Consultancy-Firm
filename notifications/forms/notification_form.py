"""
Notification Filter Forms
For filtering notifications by status, type, and date range.
"""

from django import forms


class NotificationFilterForm(forms.Form):
    """
    Form for filtering notifications.
    Used on the notification list page.
    """
    STATUS_CHOICES = [
        ('all', 'All'),
        ('unread', 'Unread'),
        ('read', 'Read'),
    ]

    TYPE_CHOICES = [
        ('', 'All Types'),
        ('STOCK_ALERT', 'Stock Alert'),
        ('ORDER_CONFIRMED', 'Order Confirmed'),
        ('ORDER_STATUS', 'Order Status Update'),
        ('PROJECT_UPDATE', 'Project Update'),
        ('PAYMENT_RECEIVED', 'Payment Received'),
        ('SYSTEM', 'System'),
        ('REMINDER', 'Reminder'),
        ('AUDIT', 'Audit Report'),
    ]

    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control form-control-sm'})
    )

    notification_type = forms.ChoiceField(
        choices=TYPE_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control form-control-sm'})
    )

    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control form-control-sm'})
    )

    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control form-control-sm'})
    )

    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-sm',
            'placeholder': 'Search notifications...'
        })
    )

    def clean(self):
        """Validate date range."""
        cleaned_data = super().clean()
        date_from = cleaned_data.get('date_from')
        date_to = cleaned_data.get('date_to')

        if date_from and date_to and date_from > date_to:
            raise forms.ValidationError("'From' date cannot be after 'To' date.")

        return cleaned_data