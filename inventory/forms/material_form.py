"""
Material Form - Create and edit materials.

Validates material data including name, category, unit, quantities,
and cost fields. Ensures data integrity before saving.
"""

from django import forms
from django.core.exceptions import ValidationError
from decimal import Decimal

from inventory.models import Material, Supplier


class MaterialForm(forms.ModelForm):
    """Form for creating and editing materials."""

    class Meta:
        model = Material
        fields = [
            'name',
            'category',
            'unit',
            'description',
            'current_quantity',
            'minimum_threshold',
            'reorder_quantity',
            'unit_cost',
            'supplier',
            'sku',
            'is_available_in_shop',
            'shop_price',
            'is_active',
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Portland Cement'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'unit': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'current_quantity': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'minimum_threshold': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'reorder_quantity': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'unit_cost': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'supplier': forms.Select(attrs={'class': 'form-select'}),
            'sku': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., CEM-001'}),
            'is_available_in_shop': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'shop_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'name': 'Material Name',
            'category': 'Category',
            'unit': 'Unit of Measurement',
            'description': 'Description',
            'current_quantity': 'Current Quantity',
            'minimum_threshold': 'Minimum Threshold (Low Stock Alert)',
            'reorder_quantity': 'Reorder Quantity',
            'unit_cost': 'Unit Cost (KES)',
            'supplier': 'Primary Supplier',
            'sku': 'SKU (Stock Keeping Unit)',
            'is_available_in_shop': 'Available in Online Shop',
            'shop_price': 'Shop Price (KES)',
            'is_active': 'Active',
        }
        help_texts = {
            'current_quantity': 'Current stock quantity on hand.',
            'minimum_threshold': 'When quantity drops below this, an alert is triggered.',
            'reorder_quantity': 'Recommended quantity to reorder when stock is low.',
            'unit_cost': 'Cost per unit in Kenyan Shillings (KES).',
            'is_available_in_shop': 'Enable to sell this material in the online shop.',
            'shop_price': 'Selling price in the online shop (KES).',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show active suppliers
        self.fields['supplier'].queryset = Supplier.objects.filter(is_active=True)

        # Make shop_price required if is_available_in_shop is True
        if self.instance and self.instance.is_available_in_shop:
            self.fields['shop_price'].required = True

    def clean_current_quantity(self):
        """Validate current quantity is not negative."""
        quantity = self.cleaned_data.get('current_quantity')
        if quantity is not None and quantity < 0:
            raise ValidationError('Current quantity cannot be negative.')
        return quantity

    def clean_minimum_threshold(self):
        """Validate minimum threshold is not negative."""
        threshold = self.cleaned_data.get('minimum_threshold')
        if threshold is not None and threshold < 0:
            raise ValidationError('Minimum threshold cannot be negative.')
        return threshold

    def clean_reorder_quantity(self):
        """Validate reorder quantity is not negative."""
        reorder = self.cleaned_data.get('reorder_quantity')
        if reorder is not None and reorder < 0:
            raise ValidationError('Reorder quantity cannot be negative.')
        return reorder

    def clean_unit_cost(self):
        """Validate unit cost is not negative."""
        cost = self.cleaned_data.get('unit_cost')
        if cost is not None and cost < 0:
            raise ValidationError('Unit cost cannot be negative.')
        return cost

    def clean_shop_price(self):
        """Validate shop price if material is available in shop."""
        is_available = self.cleaned_data.get('is_available_in_shop', False)
        shop_price = self.cleaned_data.get('shop_price')

        if is_available and (shop_price is None or shop_price <= 0):
            raise ValidationError('Shop price is required and must be greater than 0 when available in shop.')

        if shop_price is not None and shop_price < 0:
            raise ValidationError('Shop price cannot be negative.')

        return shop_price

    def clean(self):
        """Cross-field validation."""
        cleaned_data = super().clean()
        is_available = cleaned_data.get('is_available_in_shop', False)
        shop_price = cleaned_data.get('shop_price')

        # If available in shop but no SKU, generate one
        if is_available and not cleaned_data.get('sku'):
            name = cleaned_data.get('name', '')
            if name:
                cleaned_data['sku'] = name[:3].upper() + '-' + str(Supplier.objects.count() + 1).zfill(3)

        return cleaned_data