"""
Cart Service - Shopping cart operations.
Caldan Construction - "Building Kenya's Future, One Project at a Time."
"""

import logging
from decimal import Decimal

from django.db import transaction
from django.shortcuts import get_object_or_404

from shop.models import Cart, CartItem, Product
from accounts.services.audit_service import AuditService

logger = logging.getLogger('caldan.shop')


class CartService:
    """
    Service for shopping cart operations.
    Handles session-based cart management.
    """

    @classmethod
    def get_or_create_cart(cls, session_key):
        """
        Get cart by session key or create a new one.
        """
        cart, created = Cart.objects.get_or_create(
            session_key=session_key
        )
        return cart

    @classmethod
    def add_item(cls, session_key, product_id, quantity=1):
        """
        Add an item to the cart.
        """
        cart = cls.get_or_create_cart(session_key)
        product = get_object_or_404(Product, id=product_id, is_active=True)

        # Check stock availability
        if product.stock_quantity < quantity:
            raise ValueError(f"Not enough stock. Available: {product.stock_quantity}")

        # Get or create cart item
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={
                'quantity': quantity,
                'unit_price': product.price,
            }
        )

        if not created:
            # Check if adding would exceed stock
            new_quantity = cart_item.quantity + quantity
            if product.stock_quantity < new_quantity:
                raise ValueError(f"Not enough stock. Available: {product.stock_quantity}")
            cart_item.quantity = new_quantity
            cart_item.save()

        # Update cart timestamp
        cart.save(update_fields=['updated_at'])

        logger.info(f"Added {quantity} of {product.name} to cart {session_key}")
        return cart_item

    @classmethod
    def update_quantity(cls, cart_item_id, quantity):
        """
        Update quantity of a cart item.
        """
        cart_item = get_object_or_404(CartItem, id=cart_item_id)

        if quantity <= 0:
            cart_item.delete()
            return None

        # Check stock availability
        if cart_item.product.stock_quantity < quantity:
            raise ValueError(f"Not enough stock. Available: {cart_item.product.stock_quantity}")

        cart_item.quantity = quantity
        cart_item.save()

        logger.info(f"Updated cart item {cart_item_id} to quantity {quantity}")
        return cart_item

    @classmethod
    def remove_item(cls, cart_item_id):
        """
        Remove an item from the cart.
        """
        cart_item = get_object_or_404(CartItem, id=cart_item_id)
        cart_item.delete()
        logger.info(f"Removed cart item {cart_item_id}")
        return True

    @classmethod
    def clear_cart(cls, session_key):
        """
        Clear all items from a cart.
        """
        cart = cls.get_or_create_cart(session_key)
        cart.clear()
        logger.info(f"Cleared cart {session_key}")
        return True

    @classmethod
    def get_cart_data(cls, session_key):
        """
        Get complete cart data for display.
        """
        cart = cls.get_or_create_cart(session_key)
        return cart.get_cart_data()

    @classmethod
    def get_cart_count(cls, session_key):
        """
        Get total number of items in cart.
        """
        cart = cls.get_or_create_cart(session_key)
        return cart.total_items

    @classmethod
    def validate_cart(cls, session_key):
        """
        Validate all items in cart have sufficient stock.
        Returns (is_valid, errors).
        """
        cart = cls.get_or_create_cart(session_key)
        errors = []

        for item in cart.items.select_related('product'):
            if item.product.stock_quantity < item.quantity:
                errors.append({
                    'product': item.product.name,
                    'available': float(item.product.stock_quantity),
                    'requested': float(item.quantity),
                })

        return len(errors) == 0, errors