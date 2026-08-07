"""
Stock Out Form - Record outgoing stock.

Allows admins to record stock OUT transactions.
Validates sufficient stock before allowing transaction.
"""

from django import forms
from django.core.exceptions import ValidationError
from decimal import Decimal

from inventory.models import Material, StockTransaction


class StockOutForm(forms.ModelForm):
    """Form for recording stock OUT transactions."""

    class Meta:
        model = StockTransaction
        fields = [
            'material',
            'quantity',
            'reference',
            'notes',
        ]
        widgets = {
            'material': forms.Select(attrs={'class': 'form-select', 'id': 'material-select'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01'}),
            'reference': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Project #123'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }
        labels = {
            'material': 'Material',
            'quantity': 'Quantity',
            'reference': 'Reference',
            'notes': 'Notes',
        }
        help_texts = {
            'quantity': 'Quantity being removed from stock.',
            'reference': 'Reference (e.g., project code, order number).',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show active materials with stock
        self.fields['material'].queryset = Material.objects.filter(
            is_active=True,
            current_quantity__gt=0
        ).order_by('name')

        # Add current quantity display to material choices
        self.fields['material'].label_from_instance = self._material_label

    def _material_label(self, obj):
        """Custom label showing current quantity."""
        return f"{obj.name} ({obj.current_quantity} {obj.get_unit_display()})"

    def clean_quantity(self):
        """Validate quantity is positive."""
        quantity = self.cleaned_data.get('quantity')
        if quantity is not None and quantity <= 0:
            raise ValidationError('Quantity must be greater than 0.')
        return quantity

    def clean(self):
        """Validate sufficient stock."""
        cleaned_data = super().clean()
        material = cleaned_data.get('material')
        quantity = cleaned_data.get('quantity')

        if material and quantity:
            if quantity > material.current_quantity:
                raise ValidationError(
                    f'Insufficient stock. Available: {material.current_quantity} '
                    f'{material.get_unit_display()}. Requested: {quantity}.'
                )

            # Warn if this will trigger low stock
            if material.current_quantity - quantity <= material.minimum_threshold:
                self.add_warning(
                    f'This transaction will trigger a low stock alert. '
                    f'Remaining: {material.current_quantity - quantity} '
                    f'{material.get_unit_display()}. Threshold: {material.minimum_threshold}.'
                )

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