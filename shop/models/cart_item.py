"""
CartItem model for individual cart items.
Caldan Construction - "Building Kenya's Future, One Project at a Time."
"""

from django.db import models
from django.db.models import F


class CartItem(models.Model):
    """
    Individual item in a shopping cart.
    Links a product with quantity and unit price.
    """

    cart = models.ForeignKey(
        'shop.Cart',
        on_delete=models.CASCADE,
        related_name='items'
    )

    product = models.ForeignKey(
        'shop.Product',
        on_delete=models.CASCADE,
        related_name='cart_items'
    )

    quantity = models.PositiveIntegerField(
        default=1,
        help_text='Quantity of this product in cart'
    )

    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text='Price at time of adding to cart'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'shop_cart_items'
        unique_together = ['cart', 'product']
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.quantity} x {self.product.name}"

    @property
    def total_price(self):
        """Calculate total price for this cart item."""
        return self.quantity * self.unit_price

    @property
    def formatted_total(self):
        """Return formatted total price."""
        return f"KES {self.total_price:,.2f}"

    def update_quantity(self, quantity):
        """Update quantity and save."""
        if quantity <= 0:
            self.delete()
            return None
        self.quantity = quantity
        self.save(update_fields=['quantity', 'updated_at'])
        return self