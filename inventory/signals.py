"""
Inventory Signals - Cross-app integration.

Handles automatic updates when stock changes:
1. Sync shop product stock when material quantity changes
2. Send notifications on low stock alerts
3. Clean up resolved alerts when stock is replenished
"""

import logging
from decimal import Decimal
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone

from inventory.models import Material, StockTransaction, StockAlert
from shop.models import Product

logger = logging.getLogger('caldan.inventory')


# =====================================================================
# SHOP INTEGRATION - Sync Product Stock
# =====================================================================

@receiver(post_save, sender=Material)
def sync_product_stock_on_material_update(sender, instance, **kwargs):
    """
    Sync shop product stock when material quantity changes.

    If the material is available in the shop, find all linked products
    and update their stock quantity to match the material's current quantity.
    """
    if not instance.is_available_in_shop:
        return

    # Find all products linked to this material
    products = Product.objects.filter(inventory_material=instance)

    if not products.exists():
        return

    # Update each product's stock
    for product in products:
        product.stock_quantity = instance.current_quantity
        product.in_stock = instance.current_quantity > 0
        product.save(update_fields=['stock_quantity', 'in_stock'])

    logger.info(
        f"Synced {products.count()} product(s) for material {instance.name} "
        f"(stock: {instance.current_quantity})"
    )


# =====================================================================
# SHOP INTEGRATION - Auto-create Product
# =====================================================================

@receiver(post_save, sender=Material)
def auto_create_shop_product(sender, instance, created, **kwargs):
    """
    Automatically create a shop product when a material is marked
    as available in the shop and doesn't have a product yet.
    """
    if not instance.is_available_in_shop:
        return

    # Check if a product already exists
    if Product.objects.filter(inventory_material=instance).exists():
        return

    # Create the product
    from django.utils.text import slugify

    try:
        Product.objects.create(
            name=instance.name,
            slug=slugify(instance.name),
            category=instance.category,
            unit=instance.unit,
            description=instance.description or f"{instance.name} - Construction Material",
            price=instance.shop_price or instance.unit_cost * Decimal('1.2'),
            inventory_material=instance,
            stock_quantity=instance.current_quantity,
            in_stock=instance.current_quantity > 0,
            is_active=True,
        )
        logger.info(f"Auto-created shop product for material {instance.name}")
    except Exception as e:
        logger.error(f"Failed to auto-create product for {instance.name}: {str(e)}")


# =====================================================================
# STOCK TRANSACTION - Update Material Quantity
# =====================================================================

@receiver(post_save, sender=StockTransaction)
def handle_transaction_post_save(sender, instance, created, **kwargs):
    """
    Handle post-save of stock transaction.

    If the transaction is confirmed, update the material's current quantity.
    This is the primary mechanism for stock updates.
    """
    if instance.status != StockTransaction.Status.CONFIRMED:
        return

    # The transaction's _apply_transaction() already updates the material,
    # but we need to ensure any alerts are handled

    material = instance.material

    # Check if we need to resolve any alerts (stock increased above threshold)
    if not material.is_low_stock:
        # Resolve any open alerts for this material
        resolved = material.resolve_low_stock_alert()
        if resolved > 0:
            logger.info(f"Auto-resolved {resolved} alerts for {material.name} (stock replenished)")


@receiver(post_delete, sender=StockTransaction)
def handle_transaction_post_delete(sender, instance, **kwargs):
    """
    Handle post-delete of stock transaction.

    If a transaction is deleted, we need to reverse its effect on the material
    to maintain data integrity.
    """
    # Only handle confirmed transactions
    if instance.status != StockTransaction.Status.CONFIRMED:
        return

    material = instance.material

    # Reverse the effect
    if instance.type == StockTransaction.Type.IN:
        # Reverse IN -> subtract
        material.current_quantity -= instance.quantity
    elif instance.type == StockTransaction.Type.OUT:
        # Reverse OUT -> add back
        material.current_quantity += instance.quantity
    elif instance.type == StockTransaction.Type.RETURN:
        material.current_quantity -= instance.quantity

    # Ensure non-negative
    if material.current_quantity < 0:
        material.current_quantity = 0

    # Update material
    material.total_cost = material.current_quantity * material.unit_cost
    material.is_low_stock = material.current_quantity <= material.minimum_threshold
    material.save()

    logger.warning(
        f"Transaction {instance.id} deleted. Reversed effect on {material.name}. "
        f"New quantity: {material.current_quantity}"
    )


# =====================================================================
# STOCK ALERT - Notification Sending
# =====================================================================

def send_stock_alert_notifications(material):
    """
    Send notifications for a low stock alert.

    This is called from the AlertService when a new alert is created.
    It sends notifications via Email, SMS, and In-App channels.
    """
    from inventory.services.alert_service import AlertService

    # Let AlertService handle the notification
    alert = AlertService.check_and_create_alerts(material)

    if alert:
        logger.info(f"Notifications sent for stock alert on {material.name}")
        return alert

    return None


# =====================================================================
# HANDLE MATERIAL SAVE - Auto-check Alerts
# =====================================================================

@receiver(post_save, sender=Material)
def check_alerts_on_material_save(sender, instance, created, **kwargs):
    """
    Check if a material needs a stock alert after save.

    This runs every time a material is saved to ensure alerts are
    created when stock drops below threshold.
    """
    # Skip if material is not active
    if not instance.is_active:
        return

    # Skip if stock is above threshold
    if not instance.is_low_stock:
        # Resolve any open alerts
        instance.resolve_low_stock_alert()
        return

    # Create alert if needed
    from inventory.services.alert_service import AlertService
    AlertService.check_and_create_alerts(instance)