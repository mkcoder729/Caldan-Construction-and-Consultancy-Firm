"""
Delivery Form - Create and edit deliveries.

Handles delivery creation with line items for materials,
quantities, and costs. Supports receipt upload.
"""

from django import forms
from django.core.exceptions import ValidationError
from django.forms import inlineformset_factory
from decimal import Decimal

from inventory.models import Delivery, DeliveryItem, Material, Supplier


class DeliveryForm(forms.ModelForm):
    """Form for creating and editing deliveries."""

    class Meta:
        model = Delivery
        fields = [
            'supplier',
            'expected_date',
            'actual_date',
            'status',
            'receipt',
            'tracking_number',
            'notes',
            'delivery_fee',
        ]
        widgets = {
            'supplier': forms.Select(attrs={'class': 'form-select'}),
            'expected_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'actual_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'receipt': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*,.pdf'}),
            'tracking_number': forms.TextInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'delivery_fee': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
        }
        labels = {
            'supplier': 'Supplier',
            'expected_date': 'Expected Delivery Date',
            'actual_date': 'Actual Delivery Date',
            'status': 'Status',
            'receipt': 'Delivery Receipt',
            'tracking_number': 'Tracking Number',
            'notes': 'Notes',
            'delivery_fee': 'Delivery Fee (KES)',
        }
        help_texts = {
            'expected_date': 'When is this delivery expected?',
            'actual_date': 'When was it actually delivered?',
            'delivery_fee': 'Additional delivery fee charged by supplier.',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show active suppliers
        self.fields['supplier'].queryset = Supplier.objects.filter(is_active=True)

        # Make actual_date optional
        self.fields['actual_date'].required = False

        # If status is DELIVERED, require actual_date
        if self.instance and self.instance.status == Delivery.Status.DELIVERED:
            self.fields['actual_date'].required = True

    def clean_expected_date(self):
        """Validate expected date is not in the past (for new deliveries)."""
        expected_date = self.cleaned_data.get('expected_date')
        if expected_date and not self.instance.pk:
            from django.utils import timezone
            if expected_date < timezone.now().date():
                self.add_warning('Expected date is in the past. Please verify this is correct.')
        return expected_date

    def clean_delivery_fee(self):
        """Validate delivery fee is not negative."""
        fee = self.cleaned_data.get('delivery_fee')
        if fee is not None and fee < 0:
            raise ValidationError('Delivery fee cannot be negative.')
        return fee or Decimal('0')

    def clean(self):
        """Cross-field validation."""
        cleaned_data = super().clean()
        status = cleaned_data.get('status')
        actual_date = cleaned_data.get('actual_date')

        # If status is DELIVERED, require actual_date
        if status == Delivery.Status.DELIVERED and not actual_date:
            raise ValidationError('Actual delivery date is required when status is "Delivered".')

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


# =====================================================================
# DELIVERY ITEM FORMSET
# =====================================================================

class DeliveryItemForm(forms.ModelForm):
    """Form for delivery line items."""

    class Meta:
        model = DeliveryItem
        fields = ['material', 'quantity', 'unit_cost', 'notes']
        widgets = {
            'material': forms.Select(attrs={'class': 'form-select'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01'}),
            'unit_cost': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'notes': forms.TextInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'material': 'Material',
            'quantity': 'Quantity',
            'unit_cost': 'Unit Cost (KES)',
            'notes': 'Notes',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show active materials
        self.fields['material'].queryset = Material.objects.filter(is_active=True).order_by('name')

        # Custom label showing unit
        self.fields['material'].label_from_instance = self._material_label

    def _material_label(self, obj):
        """Custom label showing unit."""
        return f"{obj.name} ({obj.get_unit_display()})"

    def clean_quantity(self):
        """Validate quantity is positive."""
        quantity = self.cleaned_data.get('quantity')
        if quantity is not None and quantity <= 0:
            raise ValidationError('Quantity must be greater than 0.')
        return quantity

    def clean_unit_cost(self):
        """Validate unit cost is not negative."""
        cost = self.cleaned_data.get('unit_cost')
        if cost is not None and cost < 0:
            raise ValidationError('Unit cost cannot be negative.')
        return cost


# Create formset for delivery items
DeliveryItemFormSet = inlineformset_factory(
    Delivery,
    DeliveryItem,
    form=DeliveryItemForm,
    extra=1,
    min_num=1,
    validate_min=True,
    can_delete=True,
    fields=['material', 'quantity', 'unit_cost', 'notes'],
)