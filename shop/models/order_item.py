"""
OrderItem model for individual order items.
Caldan Construction - "Building Kenya's Future, One Project at a Time."
"""

from django.db import models


class OrderItem(models.Model):
    """
    Individual item in an order.
    Links a product with quantity and price at time of order.
    """

    order = models.ForeignKey(
        'shop.Order',
        on_delete=models.CASCADE,
        related_name='items'
    )

    product = models.ForeignKey(
        'shop.Product',
        on_delete=models.PROTECT,
        related_name='order_items'
    )

    quantity = models.PositiveIntegerField(
        help_text='Quantity ordered'
    )

    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text='Price at time of order'
    )

    total_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text='Quantity * Unit Price'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'shop_order_items'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.quantity} x {self.product.name}"

    def save(self, *args, **kwargs):
        """Auto-calculate total price."""
        if not self.total_price:
            self.total_price = self.quantity * self.unit_price
        super().save(*args, **kwargs)

    @property
    def formatted_total(self):
        """Return formatted total price."""
        return f"KES {self.total_price:,.2f}"

    @property
    def formatted_unit_price(self):
        """Return formatted unit price."""
        return f"KES {self.unit_price:,.2f}"