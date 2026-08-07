"""
Signals for Shop app - Auto-sync inventory to product stock.
Caldan Construction - "Building Kenya's Future, One Project at a Time."
"""

import logging

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from inventory.models import Material
from shop.models import Product

logger = logging.getLogger('caldan.shop')


@receiver(post_save, sender=Material)
def update_product_stock_on_material_save(sender, instance, **kwargs):
    """
    Update linked product stock when material stock changes.
    Triggered after a Material is saved.
    """
    try:
        products = Product.objects.filter(inventory_material=instance)
        if not products.exists():
            return

        updated_count = 0
        for product in products:
            product.update_stock()
            updated_count += 1

        logger.info(
            f"Updated {updated_count} product(s) linked to material: {instance.name} "
            f"(ID: {instance.id}) - New stock: {instance.current_quantity}"
        )

    except Exception as e:
        logger.error(f"Failed to update products for material {instance.id}: {str(e)}")


@receiver(post_delete, sender=Material)
def update_product_stock_on_material_delete(sender, instance, **kwargs):
    """
    Set product stock to 0 when linked material is deleted.
    Triggered after a Material is deleted.
    """
    try:
        products = Product.objects.filter(inventory_material_id=instance.id)
        if not products.exists():
            return

        updated_count = 0
        for product in products:
            product.stock_quantity = 0
            product.in_stock = False
            product.save(update_fields=['stock_quantity', 'in_stock'])
            updated_count += 1

        logger.info(
            f"Set {updated_count} product(s) to out of stock after material deletion: {instance.name} "
            f"(ID: {instance.id})"
        )

    except Exception as e:
        logger.error(f"Failed to update products for deleted material {instance.id}: {str(e)}")