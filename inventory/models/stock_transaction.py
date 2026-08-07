"""
Stock Transaction Model - Tracks all material movements.

Records every stock IN, OUT, ADJUSTMENT, and RETURN with full audit trail,
including who performed the transaction, receipts, and quantity changes.
"""

from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.validators import MinValueValidator
from decimal import Decimal


class StockTransaction(models.Model):
    """Stock transaction - tracks every material movement."""

    class Type(models.TextChoices):
        IN = 'IN', 'Stock In'
        OUT = 'OUT', 'Stock Out'
        ADJUSTMENT = 'ADJUSTMENT', 'Adjustment'
        RETURN = 'RETURN', 'Return'

    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        CONFIRMED = 'CONFIRMED', 'Confirmed'
        CANCELLED = 'CANCELLED', 'Cancelled'

    # =====================================================================
    # MATERIAL RELATIONSHIP
    # =====================================================================
    material = models.ForeignKey(
        'inventory.Material',
        on_delete=models.CASCADE,
        related_name='transactions',
        help_text="Material being transacted"
    )

    # =====================================================================
    # TRANSACTION DETAILS
    # =====================================================================
    type = models.CharField(
        max_length=20,
        choices=Type.choices,
        db_index=True,
        help_text="Type of transaction"
    )
    quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Quantity transacted (always positive)"
    )
    unit_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Cost per unit at time of transaction"
    )
    total_cost = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        default=0,
        help_text="Auto-calculated: quantity × unit_cost"
    )

    # =====================================================================
    # PERFORMED BY
    # =====================================================================
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='stock_transactions',
        help_text="Admin who performed this transaction"
    )

    # =====================================================================
    # REFERENCE & NOTES
    # =====================================================================
    reference = models.CharField(
        max_length=100,
        blank=True,
        default='',
        help_text="External reference (e.g., order number, invoice)"
    )
    notes = models.TextField(
        blank=True,
        default='',
        help_text="Additional notes about this transaction"
    )

    # =====================================================================
    # RECEIPT UPLOAD (Cloudinary)
    # =====================================================================
    receipt = models.ImageField(
        upload_to='inventory/receipts/%Y/%m/%d/',
        blank=True,
        null=True,
        help_text="Uploaded receipt (Cloudinary storage)"
    )
    receipt_number = models.CharField(
        max_length=50,
        blank=True,
        default='',
        help_text="Receipt or invoice number"
    )

    # =====================================================================
    # STATUS & CONFIRMATION
    # =====================================================================
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
        help_text="Transaction status"
    )
    confirmed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this transaction was confirmed"
    )
    cancelled_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this transaction was cancelled"
    )
    cancelled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cancelled_transactions',
        help_text="Admin who cancelled this transaction"
    )

    # =====================================================================
    # QUANTITY TRACKING (Before/After for audit)
    # =====================================================================
    quantity_before = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Material quantity before this transaction"
    )
    quantity_after = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Material quantity after this transaction"
    )

    # =====================================================================
    # TIMESTAMPS
    # =====================================================================
    transaction_date = models.DateTimeField(
        default=timezone.now,
        db_index=True,
        help_text="Date/time of the transaction"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'stock_transactions'
        ordering = ['-transaction_date']
        indexes = [
            models.Index(fields=['material', '-transaction_date'], name='stock_material_txn_idx'),
            models.Index(fields=['status'], name='stock_status_idx'),
            models.Index(fields=['type'], name='stock_type_idx'),
            models.Index(fields=['-transaction_date'], name='stock_txn_date_idx'),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(quantity__gte=0),
                name='stock_quantity_non_negative'
            ),
        ]

    def __str__(self):
        return f"{self.get_type_display()} - {self.material.name} ({self.quantity} {self.material.get_unit_display()})"

    # =====================================================================
    # CORE METHODS
    # =====================================================================

    def save(self, *args, **kwargs):
        """Override save to calculate total_cost and track quantity changes."""
        # Calculate total_cost if unit_cost is provided
        if self.unit_cost is not None:
            self.total_cost = self.quantity * self.unit_cost
        else:
            self.total_cost = 0

        # Track quantity before if not set
        if self.quantity_before is None and self.material_id:
            self.quantity_before = self.material.current_quantity

        # Auto-confirm if status is CONFIRMED and not yet confirmed
        if self.status == self.Status.CONFIRMED and not self.confirmed_at:
            self._apply_transaction()

        super().save(*args, **kwargs)

    def _apply_transaction(self):
        """Apply the transaction to the material quantity."""
        if self.status == self.Status.CONFIRMED:
            # Record quantity before if not already set
            if self.quantity_before is None:
                self.quantity_before = self.material.current_quantity

            # Apply transaction based on type
            if self.type == self.Type.IN:
                self.material.current_quantity += self.quantity
            elif self.type == self.Type.OUT:
                self.material.current_quantity -= self.quantity
            elif self.type == self.Type.ADJUSTMENT:
                self.material.current_quantity = self.quantity
            elif self.type == self.Type.RETURN:
                self.material.current_quantity += self.quantity

            # Update material
            self.material.total_cost = self.material.current_quantity * self.material.unit_cost
            self.material.is_low_stock = self.material.current_quantity <= self.material.minimum_threshold
            self.material.save(update_fields=['current_quantity', 'total_cost', 'is_low_stock'])

            # Record quantity after
            self.quantity_after = self.material.current_quantity

            # Set confirmed_at
            self.confirmed_at = timezone.now()

    def confirm(self):
        """Confirm and apply this transaction."""
        if self.status == self.Status.PENDING:
            self.status = self.Status.CONFIRMED
            self._apply_transaction()
            self.save()

            # Create alert if low stock (for OUT transactions)
            if self.type == self.Type.OUT and self.material.is_low_stock:
                from inventory.models.stock_alert import StockAlert
                StockAlert.objects.get_or_create(
                    material=self.material,
                    status=StockAlert.Status.OPEN,
                    defaults={
                        'message': f"Low stock: {self.material.name} "
                                   f"({self.material.current_quantity} {self.material.get_unit_display()})",
                        'threshold_quantity': self.material.minimum_threshold,
                        'current_quantity_at_alert': self.material.current_quantity,
                    }
                )

    def cancel(self, user, reason=""):
        """Cancel this transaction (reverse if confirmed)."""
        if self.status == self.Status.CONFIRMED:
            # Reverse the transaction on the material
            if self.type == self.Type.IN:
                self.material.current_quantity -= self.quantity
            elif self.type == self.Type.OUT:
                self.material.current_quantity += self.quantity
            elif self.type == self.Type.RETURN:
                self.material.current_quantity -= self.quantity

            self.material.total_cost = self.material.current_quantity * self.material.unit_cost
            self.material.is_low_stock = self.material.current_quantity <= self.material.minimum_threshold
            self.material.save(update_fields=['current_quantity', 'total_cost', 'is_low_stock'])

        self.status = self.Status.CANCELLED
        self.cancelled_at = timezone.now()
        self.cancelled_by = user
        if reason:
            self.notes = f"{self.notes}\n\nCancelled: {reason}" if self.notes else f"Cancelled: {reason}"
        self.save()

    @property
    def is_in_transaction(self) -> bool:
        """Check if this is an IN transaction."""
        return self.type == self.Type.IN

    @property
    def is_out_transaction(self) -> bool:
        """Check if this is an OUT transaction."""
        return self.type == self.Type.OUT