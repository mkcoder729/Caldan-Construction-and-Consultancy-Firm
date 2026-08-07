"""
Client form with validation for Kenyan phone numbers and email.
Caldan Construction - "Building Kenya's Future, One Project at a Time."
"""

from django import forms
from django.core.exceptions import ValidationError

from clients.models import Client


class ClientForm(forms.ModelForm):
    """
    Form for creating and editing clients.
    Includes Kenyan phone number validation.
    """

    class Meta:
        model = Client
        fields = [
            'name',
            'type',
            'company_name',
            'email',
            'phone',
            'alternative_phone',
            'address',
            'county',
            'town',
            'status',
            'source',
            'notes',
            'projects',
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. John Doe'
            }),
            'type': forms.Select(attrs={'class': 'form-control'}),
            'company_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. ABC Construction Ltd'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'john@example.com'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '0712345678'
            }),
            'alternative_phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '0723456789'
            }),
            'address': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. 123 Main Street'
            }),
            'county': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Nairobi'
            }),
            'town': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Westlands'
            }),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'source': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Website, Referral, Direct'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Additional notes about this client...'
            }),
            'projects': forms.SelectMultiple(attrs={
                'class': 'form-control',
                'size': 5
            }),
        }
        labels = {
            'name': 'Full Name',
            'type': 'Client Type',
            'company_name': 'Company Name',
            'email': 'Email Address',
            'phone': 'Phone Number',
            'alternative_phone': 'Alternative Phone',
            'address': 'Physical Address',
            'county': 'County',
            'town': 'Town/City',
            'status': 'Status',
            'source': 'Lead Source',
            'notes': 'Notes',
            'projects': 'Linked Projects',
        }
        help_texts = {
            'phone': 'Kenyan format: 07XXXXXXXX or +2547XXXXXXXX',
            'alternative_phone': 'Optional second contact number',
            'source': 'Where did this client come from?',
            'projects': 'Hold Ctrl to select multiple projects',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make phone required for new clients
        if not self.instance.pk:
            self.fields['phone'].required = True

    def clean_phone(self):
        """Validate and format Kenyan phone number."""
        phone = self.cleaned_data.get('phone', '')
        if not phone:
            return phone

        # Remove spaces, dashes, parentheses
        phone = ''.join(c for c in phone if c.isdigit() or c == '+')

        # Validate Kenyan phone number
        if phone.startswith('+254'):
            if len(phone) != 13:
                raise ValidationError('Invalid Kenyan phone number. Format: +2547XXXXXXXX')
        elif phone.startswith('0'):
            if len(phone) != 10:
                raise ValidationError('Invalid Kenyan phone number. Format: 07XXXXXXXX')
            # Convert to international format for storage
            phone = '+254' + phone[1:]
        elif len(phone) == 9 and phone.startswith('7'):
            phone = '+254' + phone
        elif len(phone) == 9 and phone.startswith('1'):
            phone = '+254' + phone
        else:
            raise ValidationError('Invalid phone number. Use Kenyan format: 07XXXXXXXX or +2547XXXXXXXX')

        return phone

    def clean_alternative_phone(self):
        """Validate alternative phone number."""
        phone = self.cleaned_data.get('alternative_phone', '')
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
        else:
            raise ValidationError('Invalid phone number. Use Kenyan format: 07XXXXXXXX or +2547XXXXXXXX')

        return phone

    def clean_email(self):
        """Validate email and check for duplicates."""
        email = self.cleaned_data.get('email', '').strip().lower()
        if email:
            # Check for existing client with same email (excluding current instance)
            qs = Client.objects.filter(email=email)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise ValidationError('A client with this email already exists.')
        return email

    def clean(self):
        """Validate that at least name or company_name is provided."""
        cleaned_data = super().clean()
        name = cleaned_data.get('name')
        company_name = cleaned_data.get('company_name')

        if not name and not company_name:
            raise ValidationError('Either Name or Company Name must be provided.')

        return cleaned_data