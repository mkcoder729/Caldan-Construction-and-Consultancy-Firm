"""
Supplier Form - Create and edit suppliers.

Validates supplier information including contact details,
payment terms, and business registration.
"""

from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import EmailValidator

from inventory.models import Supplier


class SupplierForm(forms.ModelForm):
    """Form for creating and editing suppliers."""

    class Meta:
        model = Supplier
        fields = [
            'name',
            'contact_person',
            'phone',
            'alternative_phone',
            'email',
            'address',
            'county',
            'town',
            'payment_terms',
            'tax_id',
            'business_registration',
            'notes',
            'is_active',
            'is_preferred',
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_person': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 0712345678'}),
            'alternative_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 0712345678'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'county': forms.TextInput(attrs={'class': 'form-control'}),
            'town': forms.TextInput(attrs={'class': 'form-control'}),
            'payment_terms': forms.Select(attrs={'class': 'form-select'}),
            'tax_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., PIN: A123456789B'}),
            'business_registration': forms.TextInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_preferred': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'name': 'Supplier Name',
            'contact_person': 'Contact Person',
            'phone': 'Phone Number',
            'alternative_phone': 'Alternative Phone',
            'email': 'Email Address',
            'address': 'Physical Address',
            'county': 'County',
            'town': 'Town/City',
            'payment_terms': 'Payment Terms',
            'tax_id': 'Tax/PIN Number',
            'business_registration': 'Business Registration',
            'notes': 'Notes',
            'is_active': 'Active',
            'is_preferred': 'Preferred Supplier',
        }
        help_texts = {
            'phone': 'Kenyan phone number format (e.g., 0712345678).',
            'payment_terms': 'Agreed payment terms with this supplier.',
            'tax_id': 'KRA PIN or tax identification number.',
        }

    def clean_phone(self):
        """Validate and normalize Kenyan phone number."""
        phone = self.cleaned_data.get('phone')
        if phone:
            # Remove spaces, hyphens, and parentheses
            phone = phone.strip().replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
            # Check if it's a Kenyan number
            if not (phone.startswith('07') or phone.startswith('01') or phone.startswith('+254') or phone.startswith('254')):
                raise ValidationError('Please enter a valid Kenyan phone number (e.g., 0712345678).')
        return phone

    def clean_alternative_phone(self):
        """Validate alternative phone number."""
        phone = self.cleaned_data.get('alternative_phone')
        if phone:
            phone = phone.strip().replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
            if not (phone.startswith('07') or phone.startswith('01') or phone.startswith('+254') or phone.startswith('254')):
                raise ValidationError('Please enter a valid Kenyan phone number (e.g., 0712345678).')
        return phone

    def clean_email(self):
        """Validate email address."""
        email = self.cleaned_data.get('email')
        if email:
            try:
                EmailValidator()(email)
            except ValidationError:
                raise ValidationError('Please enter a valid email address.')
        return email

    def clean(self):
        """Cross-field validation."""
        cleaned_data = super().clean()
        name = cleaned_data.get('name')
        contact_person = cleaned_data.get('contact_person')

        if name and contact_person and name == contact_person:
            self.add_warning('Supplier name and contact person are the same. This might be a sole proprietorship.')

        return cleaned_data

    def add_warning(self, message):
        """Add a warning to the form."""
        if not hasattr(self, '_warnings'):
            self._warnings = []
        self._warnings.append(message)

    @property
    def warnings(self):
        """Get warnings added to the form."""
        return getattr(self, '_warnings', [])