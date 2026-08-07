"""
Stock In Form - Record incoming stock.

Allows admins to record stock IN transactions with receipt upload.
Validates quantity, unit cost, and material selection.
"""

from django import forms
from django.core.exceptions import ValidationError
from decimal import Decimal

from inventory.models import Material, StockTransaction


class StockInForm(forms.ModelForm):
    """Form for recording stock IN transactions."""

    class Meta:
        model = StockTransaction
        fields = [
            'material',
            'quantity',
            'unit_cost',
            'reference',
            'notes',
            'receipt',
            'receipt_number',
        ]
        widgets = {
            'material': forms.Select(attrs={'class': 'form-select', 'id': 'material-select'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01'}),
            'unit_cost': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'reference': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Order #1234'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'receipt': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*,.pdf'}),
            'receipt_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., INV-001'}),
        }
        labels = {
            'material': 'Material',
            'quantity': 'Quantity',
            'unit_cost': 'Unit Cost (KES)',
            'reference': 'Reference',
            'notes': 'Notes',
            'receipt': 'Receipt Upload',
            'receipt_number': 'Receipt Number',
        }
        help_texts = {
            'quantity': 'Quantity being added to stock.',
            'unit_cost': 'Cost per unit. Leave blank to use material\'s current unit cost.',
            'receipt': 'Upload receipt or invoice (JPG, PNG, PDF).',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show active materials
        self.fields['material'].queryset = Material.objects.filter(is_active=True).order_by('name')

        # Make unit_cost optional - will use material's unit_cost if not provided
        self.fields['unit_cost'].required = False

    def clean_quantity(self):
        """Validate quantity is positive."""
        quantity = self.cleaned_data.get('quantity')
        if quantity is not None and quantity <= 0:
            raise ValidationError('Quantity must be greater than 0.')
        return quantity

    def clean_unit_cost(self):
        """Validate unit cost if provided."""
        unit_cost = self.cleaned_data.get('unit_cost')
        if unit_cost is not None and unit_cost < 0:
            raise ValidationError('Unit cost cannot be negative.')
        return unit_cost

    def clean(self):
        """Cross-field validation."""
        cleaned_data = super().clean()
        material = cleaned_data.get('material')
        quantity = cleaned_data.get('quantity')

        if material and quantity:
            # Check if quantity exceeds reasonable limit (optional warning)
            if quantity > 10000:
                self.add_warning('Large quantity entered. Please verify this is correct.')

        return cleaned_data

    def add_warning(self, message):
        """Add a warning to the form (not a validation error)."""
        if not hasattr(self, '_warnings'):
            self._warnings = []
        self._warnings.append(message)

    @property
    def warnings(self):
        """Get warnings added to the form."""
        return getattr(self, '_warnings', [])