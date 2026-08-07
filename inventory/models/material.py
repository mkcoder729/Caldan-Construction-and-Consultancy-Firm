"""
Material Model - Core inventory entity for Caldan Construction.

Tracks all construction materials with categories, units, quantities,
costs, and supplier relationships. Supports shop integration and
automatic low stock alerts.
"""

from django.db import models
from django.utils import timezone
from django.conf import settings
from django.core.validators import MinValueValidator
from decimal import Decimal


class Material(models.Model):
    """Construction material model - tracks all physical materials."""

    class Category(models.TextChoices):
        CEMENT = 'CEMENT', 'Cement'
        STEEL = 'STEEL', 'Steel'
        SAND = 'SAND', 'Sand'
        AGGREGATE = 'AGGREGATE', 'Aggregate'
        BLOCKS = 'BLOCKS', 'Blocks'
        PAINT = 'PAINT', 'Paint'
        TIMBER = 'TIMBER', 'Timber'
        PLUMBING = 'PLUMBING', 'Plumbing'
        ELECTRICAL = 'ELECTRICAL', 'Electrical'
        TOOLS = 'TOOLS', 'Tools'
        OTHER = 'OTHER', 'Other'

    class Unit(models.TextChoices):
        BAG = 'BAG', 'Bag'
        TONNE = 'TONNE', 'Tonne'
        PIECE = 'PIECE', 'Piece'
        LITRE = 'LITRE', 'Litre'
        METRE = 'METRE', 'Metre'
        SQUARE_METRE = 'SQUARE_METRE', 'Square Metre'
        CUBIC_METRE = 'CUBIC_METRE', 'Cubic Metre'
        KILOGRAM = 'KILOGRAM', 'Kilogram'
        OTHER = 'OTHER', 'Other'

    # =====================================================================
    # IDENTITY FIELDS
    # =====================================================================
    name = models.CharField(
        max_length=100,
        db_index=True,
        help_text="Material name (e.g., 'Portland Cement')"
    )
    category = models.CharField(
        max_length=20,
        choices=Category.choices,
        db_index=True,
        help_text="Material category for filtering"
    )
    unit = models.CharField(
        max_length=20,
        choices=Unit.choices,
        help_text="Unit of measurement"
    )
    description = models.TextField(
        blank=True,
        default='',
        help_text="Optional description or specifications"
    )

    # =====================================================================
    # QUANTITY FIELDS
    # =====================================================================
    current_quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Current stock quantity"
    )
    minimum_threshold = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Low stock alert threshold"
    )
    reorder_quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Quantity to reorder when low"
    )

    # =====================================================================
    # COST FIELDS (Denormalized for performance)
    # =====================================================================
    unit_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Cost per unit (KES)"
    )
    total_cost = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        help_text="Auto-calculated: current_quantity × unit_cost"
    )

    # =====================================================================
    # SUPPLIER RELATIONSHIP
    # =====================================================================
    supplier = models.ForeignKey(
        'inventory.Supplier',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='materials',
        help_text="Primary supplier for this material"
    )

    # =====================================================================
    # SHOP INTEGRATION (SKU for online store)
    # =====================================================================
    sku = models.CharField(
        max_length=50,
        blank=True,
        default='',
        help_text="Stock Keeping Unit for shop integration"
    )
    is_available_in_shop = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Can this material be sold in the online shop?"
    )
    shop_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text="Price in shop (KES) - only if is_available_in_shop=True"
    )

    # =====================================================================
    # STATUS FIELDS
    # =====================================================================
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Is this material still in use?"
    )
    is_low_stock = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Auto-set when current_quantity <= minimum_threshold"
    )

    # =====================================================================
    # TIMESTAMPS
    # =====================================================================
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_materials',
        help_text="Admin who created this material"
    )

    class Meta:
        db_table = 'materials'
        ordering = ['name']
        indexes = [
            models.Index(fields=['category'], name='materials_category_idx'),
            models.Index(fields=['is_low_stock'], name='materials_low_stock_idx'),
            models.Index(fields=['is_available_in_shop'], name='materials_shop_idx'),
            models.Index(fields=['-created_at'], name='materials_created_idx'),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(current_quantity__gte=0),
                name='material_quantity_non_negative'
            ),
            models.CheckConstraint(
                check=models.Q(unit_cost__gte=0),
                name='material_cost_non_negative'
            ),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_unit_display()})"

    # =====================================================================
    # CORE METHODS
    # =====================================================================

    def save(self, *args, **kwargs):
        """Override save to auto-calculate total_cost and low_stock status."""
        # Auto-calculate total_cost
        self.total_cost = self.current_quantity * self.unit_cost

        # Auto-set low_stock flag
        self.is_low_stock = self.current_quantity <= self.minimum_threshold

        super().save(*args, **kwargs)

    def update_quantity(self, amount: Decimal, transaction=None) -> Decimal:
        """
        Update material quantity and handle alerts.

        Args:
            amount: Positive for IN, negative for OUT
            transaction: Optional StockTransaction for audit reference

        Returns:
            Decimal: New quantity after update
        """
        if amount == 0:
            return self.current_quantity

        # Calculate new quantity
        new_quantity = self.current_quantity + amount

        # Validate we're not going negative
        if new_quantity < 0:
            raise ValueError(
                f"Insufficient stock. Current: {self.current_quantity}, "
                f"Attempted: {amount} (would result in {new_quantity})"
            )

        # Update quantity
        self.current_quantity = new_quantity
        self.total_cost = self.current_quantity * self.unit_cost
        self.is_low_stock = self.current_quantity <= self.minimum_threshold
        self.save(update_fields=['current_quantity', 'total_cost', 'is_low_stock'])

        # Create alert if low stock and quantity decreased
        if self.is_low_stock and amount < 0:
            from inventory.models.stock_alert import StockAlert
            StockAlert.objects.get_or_create(
                material=self,
                status=StockAlert.Status.OPEN,
                defaults={
                    'message': f"Low stock: {self.name} ({self.current_quantity} {self.get_unit_display()})",
                    'threshold_quantity': self.minimum_threshold,
                    'current_quantity_at_alert': self.current_quantity,
                }
            )

        return self.current_quantity

    def resolve_low_stock_alert(self):
        """Resolve any open low stock alerts for this material."""
        from inventory.models.stock_alert import StockAlert
        updated = StockAlert.objects.filter(
            material=self,
            status=StockAlert.Status.OPEN
        ).update(
            status=StockAlert.Status.RESOLVED,
            resolved_at=timezone.now()
        )
        return updated

    @property
    def is_out_of_stock(self) -> bool:
        """Check if material is out of stock."""
        return self.current_quantity <= 0

    @property
    def stock_value(self) -> Decimal:
        """Total stock value for this material."""
        return self.current_quantity * self.unit_cost

    @property
    def remaining_to_threshold(self) -> Decimal:
        """Quantity remaining before hitting low stock threshold."""
        return max(Decimal('0'), self.current_quantity - self.minimum_threshold)