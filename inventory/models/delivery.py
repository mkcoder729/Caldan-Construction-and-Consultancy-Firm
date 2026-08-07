"""
Delivery Model - Tracks incoming material shipments from suppliers.

Manages delivery tracking with line items for materials,
quantities, costs, and status tracking.
"""

from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.validators import MinValueValidator
from decimal import Decimal


def get_default_date():
    """Return today's date for default values."""
    return timezone.now().date()


class Delivery(models.Model):
    """Delivery from supplier - tracks incoming shipments."""

    class Status(models.TextChoices):
        EXPECTED = 'EXPECTED', 'Expected'
        IN_TRANSIT = 'IN_TRANSIT', 'In Transit'
        DELIVERED = 'DELIVERED', 'Delivered'
        CANCELLED = 'CANCELLED', 'Cancelled'

    # =====================================================================
    # SUPPLIER RELATIONSHIP
    # =====================================================================
    supplier = models.ForeignKey(
        'inventory.Supplier',
        on_delete=models.CASCADE,
        related_name='deliveries',
        help_text="Supplier making this delivery"
    )

    # =====================================================================
    # DELIVERY DETAILS
    # =====================================================================
    delivery_number = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        default='DEL-2026-0001',
        help_text="Unique delivery reference number"
    )

    # =====================================================================
    # DATES
    # =====================================================================
    expected_date = models.DateField(
        default=get_default_date,
        help_text="Expected delivery date"
    )
    actual_date = models.DateField(
        null=True,
        blank=True,
        help_text="Actual delivery date"
    )

    # =====================================================================
    # STATUS
    # =====================================================================
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.EXPECTED,
        db_index=True,
        help_text="Delivery status"
    )

    # =====================================================================
    # DOCUMENTATION
    # =====================================================================
    receipt = models.ImageField(
        upload_to='inventory/deliveries/%Y/%m/%d/',
        blank=True,
        null=True,
        help_text="Delivery receipt (Cloudinary storage)"
    )
    tracking_number = models.CharField(
        max_length=100,
        blank=True,
        default='',
        help_text="Tracking number if available"
    )

    # =====================================================================
    # NOTES
    # =====================================================================
    notes = models.TextField(
        blank=True,
        default='',
        help_text="Additional notes about this delivery"
    )

    # =====================================================================
    # TOTAL COSTS (Denormalized)
    # =====================================================================
    subtotal = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        help_text="Subtotal from delivery items"
    )
    delivery_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Delivery fee charged"
    )
    total = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        help_text="Total = subtotal + delivery_fee"
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
        related_name='created_deliveries',
        help_text="Admin who created this delivery"
    )

    class Meta:
        db_table = 'deliveries'
        ordering = ['-expected_date']
        indexes = [
            models.Index(fields=['delivery_number'], name='delivery_number_idx'),
            models.Index(fields=['status'], name='delivery_status_idx'),
            models.Index(fields=['supplier', '-expected_date'], name='delivery_supplier_idx'),
        ]

    def __str__(self):
        return f"{self.delivery_number} - {self.supplier.name} ({self.get_status_display()})"

    # =====================================================================
    # CORE METHODS
    # =====================================================================

    def save(self, *args, **kwargs):
        """Override save to generate delivery number and calculate totals."""
        if not self.delivery_number or self.delivery_number == 'DEL-2026-0001':
            self.delivery_number = self.generate_delivery_number()

        # Calculate totals from items
        self._update_totals()

        super().save(*args, **kwargs)

    def generate_delivery_number(self) -> str:
        """Generate unique delivery number: DEL-2026-0001."""
        year = timezone.now().year
        count = Delivery.objects.filter(
            created_at__year=year
        ).count() + 1
        return f"DEL-{year}-{count:04d}"

    def _update_totals(self):
        """Update totals from delivery items."""
        items = self.items.all()
        if items.exists():
            self.subtotal = sum(item.total_cost for item in items)
        else:
            self.subtotal = Decimal('0')
        self.total = self.subtotal + self.delivery_fee

    def mark_as_delivered(self, actual_date=None):
        """Mark this delivery as delivered."""
        if self.status != self.Status.DELIVERED:
            self.status = self.Status.DELIVERED
            self.actual_date = actual_date or timezone.now().date()
            self.save()

    def mark_as_cancelled(self):
        """Mark this delivery as cancelled."""
        if self.status != self.Status.CANCELLED:
            self.status = self.Status.CANCELLED
            self.save()

    @property
    def item_count(self) -> int:
        """Number of items in this delivery."""
        return self.items.count()

    @property
    def is_completed(self) -> bool:
        """Check if delivery is completed (delivered or cancelled)."""
        return self.status in [self.Status.DELIVERED, self.Status.CANCELLED]


class DeliveryItem(models.Model):
    """Individual item in a delivery."""

    # =====================================================================
    # RELATIONSHIPS
    # =====================================================================
    delivery = models.ForeignKey(
        Delivery,
        on_delete=models.CASCADE,
        related_name='items',
        help_text="Parent delivery"
    )
    material = models.ForeignKey(
        'inventory.Material',
        on_delete=models.PROTECT,
        related_name='delivery_items',
        help_text="Material being delivered"
    )

    # =====================================================================
    # QUANTITY & COST
    # =====================================================================
    quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Quantity delivered"
    )
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
        help_text="Auto-calculated: quantity × unit_cost"
    )

    # =====================================================================
    # RECEIVED QUANTITY (For partial deliveries)
    # =====================================================================
    received_quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Quantity actually received (for partial deliveries)"
    )
    is_fully_received = models.BooleanField(
        default=False,
        help_text="Has the full quantity been received?"
    )

    # =====================================================================
    # NOTES
    # =====================================================================
    notes = models.TextField(
        blank=True,
        default='',
        help_text="Item-specific notes"
    )

    class Meta:
        db_table = 'delivery_items'
        ordering = ['id']
        unique_together = ['delivery', 'material']
        indexes = [
            models.Index(fields=['material'], name='delivery_item_material_idx'),
        ]

    def __str__(self):
        return f"{self.material.name} ({self.quantity} {self.material.get_unit_display()})"

    # =====================================================================
    # CORE METHODS
    # =====================================================================

    def save(self, *args, **kwargs):
        """Override save to calculate total_cost."""
        self.total_cost = self.quantity * self.unit_cost
        self.is_fully_received = self.received_quantity >= self.quantity
        super().save(*args, **kwargs)
        # Update parent delivery totals
        self.delivery._update_totals()
        self.delivery.save(update_fields=['subtotal', 'total'])

    def receive(self, quantity=None):
        """Record partial or full receipt of this item."""
        if quantity is None:
            quantity = self.quantity

        if quantity > self.quantity:
            raise ValueError(f"Cannot receive more than ordered: {self.quantity}")

        self.received_quantity += quantity
        self.is_fully_received = self.received_quantity >= self.quantity
        self.save()
        return self.received_quantity

    @property
    def remaining_quantity(self) -> Decimal:
        """Quantity remaining to be received."""
        return self.quantity - self.received_quantity

    @property
    def received_percentage(self) -> Decimal:
        """Percentage of quantity received."""
        if self.quantity == 0:
            return Decimal('0')
        return round((self.received_quantity / self.quantity) * 100, 2)