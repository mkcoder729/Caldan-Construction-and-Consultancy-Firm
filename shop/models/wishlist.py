"""
Wishlist model for client wishlists.
Caldan Construction - "Building Kenya's Future, One Project at a Time."
"""

from django.db import models
from django.conf import settings


class Wishlist(models.Model):
    """
    Client wishlist for saving favorite products.
    """

    client = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='wishlist_items'
    )

    product = models.ForeignKey(
        'shop.Product',
        on_delete=models.CASCADE,
        related_name='wishlist_items'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'shop_wishlists'
        unique_together = ['client', 'product']
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.client.email} - {self.product.name}"