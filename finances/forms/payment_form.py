"""
Payment form with validation and Kenyan currency formatting.
Caldan Construction - "Building Kenya's Future, One Project at a Time."
"""

from django import forms
from django.core.exceptions import ValidationError

from finances.models import Payment
from projects.models import Project


class PaymentForm(forms.ModelForm):
    """
    Form for creating and editing payments.
    Includes amount validation and project linking.
    """

    class Meta:
        model = Payment
        fields = [
            'project',
            'amount',
            'type',
            'method',
            'description',
            'paid_to',
            'paid_to_contact',
            'reference',
            'invoice_number',
            'receipt',
            'status',
            'payment_date',
        ]
        widgets = {
            'project': forms.Select(attrs={'class': 'form-control'}),
            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'placeholder': '0.00'
            }),
            'type': forms.Select(attrs={'class': 'form-control'}),
            'method': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Description of the payment...'
            }),
            'paid_to': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. John Doe Construction'
            }),
            'paid_to_contact': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. 0712345678'
            }),
            'reference': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. INV-001'
            }),
            'invoice_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. INV-2026-001'
            }),
            'receipt': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*,.pdf'
            }),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'payment_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
        }
        labels = {
            'project': 'Project',
            'amount': 'Amount (KES)',
            'type': 'Payment Type',
            'method': 'Payment Method',
            'description': 'Description',
            'paid_to': 'Paid To',
            'paid_to_contact': 'Contact Number',
            'reference': 'Reference Number',
            'invoice_number': 'Invoice Number',
            'receipt': 'Receipt/Attachment',
            'status': 'Status',
            'payment_date': 'Payment Date',
        }
        help_texts = {
            'amount': 'Enter the amount in Kenyan Shillings (KES)',
            'paid_to_contact': 'Kenyan format: 07XXXXXXXX or +2547XXXXXXXX',
            'reference': 'Optional reference number for tracking',
            'receipt': 'Upload receipt or attachment (JPG, PNG, PDF)',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filter projects to only active ones
        self.fields['project'].queryset = Project.objects.filter(
            is_archived=False
        ).order_by('-created_at')

        # Set initial payment date to today
        if not self.instance.pk:
            from django.utils import timezone
            self.fields['payment_date'].initial = timezone.now().date()

    def clean_amount(self):
        """Validate amount is positive."""
        amount = self.cleaned_data.get('amount')
        if amount is None:
            raise ValidationError('Amount is required.')
        if amount <= 0:
            raise ValidationError('Amount must be greater than zero.')
        if amount > 999999999.99:
            raise ValidationError('Amount is too large.')
        return amount

    def clean_paid_to_contact(self):
        """Validate Kenyan phone number."""
        phone = self.cleaned_data.get('paid_to_contact', '')
        if not phone:
            return phone

        phone = ''.join(c for c in phone if c.isdigit() or c == '+')

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
        elif phone:
            raise ValidationError('Invalid phone number. Use Kenyan format: 07XXXXXXXX or +2547XXXXXXXX')

        return phone

    def clean_receipt(self):
        """Validate receipt upload."""
        receipt = self.cleaned_data.get('receipt')
        if receipt:
            if receipt.size > 5 * 1024 * 1024:
                raise ValidationError('File size must be under 5MB')
            valid_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.pdf']
            ext = '.' + receipt.name.split('.')[-1].lower()
            if ext not in valid_extensions:
                raise ValidationError('Only JPG, PNG, GIF, WEBP, and PDF files are allowed')
        return receipt

    def clean(self):
        """Validate that required fields are filled."""
        cleaned_data = super().clean()
        project = cleaned_data.get('project')
        paid_to = cleaned_data.get('paid_to')

        if not project:
            self.add_error('project', 'Project is required.')

        if not paid_to:
            self.add_error('paid_to', 'Recipient name is required.')

        return cleaned_data