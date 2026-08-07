"""
Product Form - Create and edit products in the shop catalogue.

Validation:
  - name required and unique (with case-insensitive de-dup)
  - price >= 0
  - compare_price >= price (and > 0 when present)
  - stock_quantity >= 0
  - inventory_material → shop_price should match if linked
  - image required on create, optional on edit
  - meta_title <= 200, meta_description <= 200
"""

from django import forms
from django.core.exceptions import ValidationError
from django.utils.text import slugify

from shop.models import Product


class ProductForm(forms.ModelForm):
    """Form for creating and editing shop products."""

    class Meta:
        model = Product
        fields = [
            'name',
            'shop_section',
            'category',
            'unit',
            'short_description',
            'description',
            'price',
            'compare_price',
            'inventory_material',
            'stock_quantity',
            'image',
            'is_active',
            'is_featured',
            'meta_title',
            'meta_description',
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Portland Cement (50kg)',
            }),
            'shop_section': forms.Select(attrs={'class': 'form-select'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'unit': forms.Select(attrs={'class': 'form-select'}),
            'short_description': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'One-line product summary',
                'maxlength': 200,
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Full product description, specifications, applications…',
            }),
            'price': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
            }),
            'compare_price': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
            }),
            'inventory_material': forms.Select(attrs={'class': 'form-select'}),
            'stock_quantity': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
            }),
            'image': forms.ClearableFileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*',
            }),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_featured': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'meta_title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'SEO title (defaults to product name)',
                'maxlength': 200,
            }),
            'meta_description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'SEO description',
                'maxlength': 200,
            }),
        }
        labels = {
            'name': 'Product Name',
            'category': 'Category',
            'unit': 'Unit',
            'short_description': 'Short Description',
            'description': 'Description',
            'price': 'Price (KES)',
            'compare_price': 'Compare-at Price (KES)',
            'inventory_material': 'Linked Inventory Material',
            'stock_quantity': 'Stock Quantity',
            'image': 'Main Image',
            'is_active': 'Active (visible in shop)',
            'is_featured': 'Featured',
            'meta_title': 'SEO Title',
            'meta_description': 'SEO Description',
        }
        help_texts = {
            'price': 'Selling price in Kenyan Shillings.',
            'compare_price': 'Optional original price shown alongside as a strikethrough.',
            'inventory_material': 'If linked, stock auto-syncs from this material.',
            'stock_quantity': 'Manual override. Auto-updated when inventory is linked.',
            'is_featured': 'Show on the homepage featured section.',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Only show active materials in the inventory link dropdown.
        from inventory.models import Material
        self.fields['inventory_material'].queryset = Material.objects.filter(
            is_active=True
        )
        self.fields['inventory_material'].required = False

        # Image is required on create but optional on edit.
        if not self.instance.pk:
            self.fields['image'].required = True

        # Narrow the Category dropdown to only valid choices for the
        # selected ShopSection. We do this in Python (rather than via
        # AJAX + JS) because the section is decided when the form is
        # rendered; if the user changes the section, the whole form
        # re-renders on submit and clean() will validate the pair.
        section_value = (
            self.data.get('shop_section')
            or getattr(self.instance, 'shop_section', None)
            or Product.ShopSection.CONSTRUCTION
        )
        valid_categories = [
            cat for cat in Product.Category.choices
            if Product.CATEGORY_TO_SECTION.get(cat[0]) == section_value
        ]
        self.fields['category'].choices = valid_categories

    # ---- Field-level validators ----

    def clean_name(self):
        name = (self.cleaned_data.get('name') or '').strip()
        if not name:
            raise ValidationError('Product name is required.')

        # Case-insensitive uniqueness check
        qs = Product.objects.filter(name__iexact=name)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError(
                'A product with this name already exists. Choose a different name.'
            )
        return name

    def clean_price(self):
        price = self.cleaned_data.get('price')
        if price is None:
            raise ValidationError('Price is required.')
        if price < 0:
            raise ValidationError('Price cannot be negative.')
        return price

    def clean_compare_price(self):
        compare_price = self.cleaned_data.get('compare_price')
        if compare_price is None:
            return compare_price
        if compare_price <= 0:
            raise ValidationError('Compare-at price must be greater than 0.')
        return compare_price

    def clean_stock_quantity(self):
        qty = self.cleaned_data.get('stock_quantity')
        if qty is None:
            return qty
        if qty < 0:
            raise ValidationError('Stock quantity cannot be negative.')
        return qty

    # ---- Cross-field ----

    def clean(self):
        cleaned = super().clean()
        price = cleaned.get('price')
        compare_price = cleaned.get('compare_price')
        section = cleaned.get('shop_section')
        category = cleaned.get('category')
        inventory_material = cleaned.get('inventory_material')

        if compare_price is not None and price is not None:
            if compare_price <= price:
                self.add_error(
                    'compare_price',
                    'Compare-at price must be greater than the selling price '
                    'to display as a discount.'
                )

        # Cross-field validation: a category must belong to the chosen
        # section (so a Construction product can't be tagged STATIONERY).
        if category and section:
            cat_section = Product.CATEGORY_TO_SECTION.get(category)
            if cat_section and cat_section != section:
                self.add_error(
                    'category',
                    f"The category '{category}' belongs to the "
                    f"'{cat_section}' section, not '{section}'. "
                    "Pick a category that matches the chosen storefront."
                )

        # General-store products don't link to inventory.Material; only
        # construction products can carry an inventory_material link.
        if inventory_material and section and section != Product.ShopSection.CONSTRUCTION:
            self.add_error(
                'inventory_material',
                'Inventory linking is only available for Construction Shop '
                "products. Clear the inventory link or switch the section to "
                "'Construction Shop'."
            )

        # Auto-fill meta_title with product name if blank
        if not cleaned.get('meta_title') and cleaned.get('name'):
            cleaned['meta_title'] = cleaned['name'][:200]

        # Auto-fill meta_description with short_description if blank
        if not cleaned.get('meta_description') and cleaned.get('short_description'):
            cleaned['meta_description'] = cleaned['short_description'][:200]

        return cleaned

    def save(self, commit=True):
        """Generate a unique slug on save if missing."""
        product = super().save(commit=False)
        if not product.slug:
            base_slug = slugify(product.name) or 'product'
            slug = base_slug
            counter = 1
            qs = Product.objects.filter(slug=slug)
            if product.pk:
                qs = qs.exclude(pk=product.pk)
            while qs.exists():
                counter += 1
                slug = f"{base_slug}-{counter}"
                qs = Product.objects.filter(slug=slug)
                if product.pk:
                    qs = qs.exclude(pk=product.pk)
            product.slug = slug

        if commit:
            product.save()
            self.save_m2m()
        return product