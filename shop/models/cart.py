"""
Cart model for shopping cart functionality.
Caldan Construction - "Building Kenya's Future, One Project at a Time."
"""

from django.db import models
from django.db.models import Sum, F
from django.utils import timezone


class Cart(models.Model):
    """
    Shopping cart model linked to a session.
    Stores cart items and tracks totals.
    """

    session_key = models.CharField(
        max_length=40,
        unique=True,
        db_index=True,
        help_text='Session key for anonymous cart'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'shop_carts'
        ordering = ['-created_at']

    def __str__(self):
        return f"Cart {self.session_key[:8]}"

    @property
    def total_items(self):
        """Get total number of items in cart."""
        return self.items.aggregate(
            total=Sum('quantity')
        )['total'] or 0

    @property
    def subtotal(self):
        """Get subtotal of all items in cart."""
        return self.items.aggregate(
            total=Sum(F('quantity') * F('unit_price'))
        )['total'] or 0

    @property
    def item_count(self):
        """Get count of unique items in cart."""
        return self.items.count()

    def clear(self):
        """Clear all items from cart."""
        self.items.all().delete()
        self.updated_at = timezone.now()
        self.save(update_fields=['updated_at'])

    def get_cart_data(self):
        """Get structured cart data for display."""
        items = self.items.select_related('product').all()
        return {
            'items': items,
            'total_items': self.total_items,
            'item_count': self.item_count,
            'subtotal': self.subtotal,
        }