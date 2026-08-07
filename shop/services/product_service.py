"""
Product Service - Shop product catalogue management.

Caldan Construction - "Building Kenya's Future, One Project at a Time."

All product CRUD goes through this service so that:
  - search, filter, and pagination logic stays in one place
  - audit logging fires from a single chokepoint
  - the product's stock stays in sync with the linked inventory material
  - admin actions (toggle_active) are isolated from the view layer
"""

import logging

from django.db import transaction
from django.db.models import Q, Count, Avg, Min, Max
from django.shortcuts import get_object_or_404

from shop.models import Product
from accounts.services.audit_service import AuditService

logger = logging.getLogger('caldan.shop')


class ProductService:
    """Service for shop product management."""

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------

    @classmethod
    def get_products(cls, filters=None, page=1, per_page=20, ordering=None):
        """
        Get products with optional filters and pagination.

        filters:
            search (str)        - matches name, description, slug
            category (str)      - exact category code (e.g. 'CEMENT')
            section (str)       - exact shop_section code (CONSTRUCTION / GENERAL_STORE)
            is_active (bool)    - filter by active flag
            is_featured (bool)  - filter by featured flag
            in_stock (bool)     - filter by stock availability
            price_min (decimal) - min price
            price_max (decimal) - max price
        """
        queryset = Product.objects.all()

        if filters:
            search = filters.get('search')
            if search:
                queryset = queryset.filter(
                    Q(name__icontains=search)
                    | Q(short_description__icontains=search)
                    | Q(description__icontains=search)
                    | Q(slug__icontains=search)
                )

            category = filters.get('category')
            if category:
                queryset = queryset.filter(category=category)

            section = filters.get('section')
            if section:
                queryset = queryset.filter(shop_section=section)

            if filters.get('is_active') is not None:
                queryset = queryset.filter(is_active=filters['is_active'])

            if filters.get('is_featured') is not None:
                queryset = queryset.filter(is_featured=filters['is_featured'])

            if filters.get('in_stock') is not None:
                queryset = queryset.filter(in_stock=filters['in_stock'])

            price_min = filters.get('price_min')
            if price_min is not None:
                queryset = queryset.filter(price__gte=price_min)

            price_max = filters.get('price_max')
            if price_max is not None:
                queryset = queryset.filter(price__lte=price_max)

        if ordering:
            queryset = queryset.order_by(ordering)
        else:
            queryset = queryset.order_by('-created_at')

        total = queryset.count()
        start = max(0, (page - 1) * per_page)
        end = start + per_page
        products = list(queryset[start:end])

        total_pages = (total + per_page - 1) // per_page if total > 0 else 1

        return {
            'products': products,
            'total': total,
            'page': page,
            'per_page': per_page,
            'total_pages': total_pages,
        }

    @classmethod
    def get_product(cls, product_id):
        """Get a single product by ID."""
        return get_object_or_404(Product, id=product_id)

    @classmethod
    def get_product_by_slug(cls, slug):
        """Get a product by slug."""
        return get_object_or_404(Product, slug=slug)

    @classmethod
    def get_product_stats(cls):
        """Aggregate stats for the product list page."""
        base = Product.objects.all()
        total = base.count()
        active = base.filter(is_active=True).count()
        inactive = base.filter(is_active=False).count()
        featured = base.filter(is_featured=True).count()
        in_stock = base.filter(in_stock=True, stock_quantity__gt=0).count()
        out_of_stock = total - in_stock

        pricing = base.aggregate(
            avg_price=Avg('price'),
            min_price=Min('price'),
            max_price=Max('price'),
        )

        # Inventory value is computed in Python to avoid Django's
        # no-arithmetic-between-aggregates limitation.
        inventory_value = sum(
            float(p.price) * float(p.stock_quantity)
            for p in base.only('price', 'stock_quantity')
        )

        # category breakdown for chart
        category_counts = (
            base.values('category')
            .annotate(count=Count('id'))
            .order_by('-count')
        )

        return {
            'total': total,
            'active': active,
            'inactive': inactive,
            'featured': featured,
            'in_stock': in_stock,
            'out_of_stock': out_of_stock,
            'avg_price': float(pricing['avg_price'] or 0),
            'min_price': float(pricing['min_price'] or 0),
            'max_price': float(pricing['max_price'] or 0),
            'inventory_value': inventory_value,
            'category_counts': list(category_counts),
        }

    # ------------------------------------------------------------------
    # Writes
    # ------------------------------------------------------------------

    @classmethod
    @transaction.atomic
    def create_product(cls, data, user=None):
        """
        Create a new product. Slug uniqueness is enforced by the model.

        Args:
            data: dict matching ProductForm.cleaned_data
            user: optional admin user for audit logging

        Returns: Product instance
        """
        product = Product.objects.create(**data)

        # Pull initial stock from inventory link if present
        if product.inventory_material:
            product.update_stock()

        if user:
            AuditService.log_action(
                user=user,
                action='PRODUCT_CREATED',
                entity_type='Product',
                entity_id=str(product.id),
                details={
                    'name': product.name,
                    'category': product.category,
                    'price': float(product.price),
                }
            )
        logger.info(f"Product created: {product.name} (id={product.id})")
        return product

    @classmethod
    @transaction.atomic
    def update_product(cls, product_id, data, user=None):
        """
        Update an existing product. Keeps the stock in sync with inventory.
        """
        product = cls.get_product(product_id)
        old_name = product.name
        old_price = float(product.price)

        for field, value in data.items():
            setattr(product, field, value)
        product.save()

        # After saving, ensure stock reflects inventory if linked
        if product.inventory_material:
            product.update_stock()

        if user:
            AuditService.log_action(
                user=user,
                action='PRODUCT_UPDATED',
                entity_type='Product',
                entity_id=str(product.id),
                details={
                    'name': product.name,
                    'old_name': old_name,
                    'new_price': float(product.price),
                    'old_price': old_price,
                }
            )
        logger.info(f"Product updated: {product.name} (id={product.id})")
        return product

    @classmethod
    @transaction.atomic
    def delete_product(cls, product_id, user=None):
        """
        Delete a product. Only allowed when there are no order items
        referencing it — protects referential integrity.
        """
        from shop.models import OrderItem

        product = cls.get_product(product_id)

        if OrderItem.objects.filter(product=product).exists():
            raise ValueError(
                f"Cannot delete '{product.name}' — it has been ordered. "
                "Mark it inactive instead."
            )

        name = product.name
        product_id_str = str(product.id)
        product.delete()

        if user:
            AuditService.log_action(
                user=user,
                action='PRODUCT_DELETED',
                entity_type='Product',
                entity_id=product_id_str,
                details={'name': name}
            )
        logger.info(f"Product deleted: {name} (id={product_id_str})")
        return True

    @classmethod
    def toggle_active(cls, product_id, user=None):
        """Flip the product's is_active flag."""
        product = cls.get_product(product_id)
        product.is_active = not product.is_active
        product.save(update_fields=['is_active', 'updated_at'])

        if user:
            AuditService.log_action(
                user=user,
                action='PRODUCT_TOGGLED',
                entity_type='Product',
                entity_id=str(product.id),
                details={'is_active': product.is_active}
            )
        return product

    @classmethod
    def toggle_featured(cls, product_id, user=None):
        """Flip the product's is_featured flag."""
        product = cls.get_product(product_id)
        product.is_featured = not product.is_featured
        product.save(update_fields=['is_featured', 'updated_at'])

        if user:
            AuditService.log_action(
                user=user,
                action='PRODUCT_FEATURED_TOGGLED',
                entity_type='Product',
                entity_id=str(product.id),
                details={'is_featured': product.is_featured}
            )
        return product

    @classmethod
    def sync_stock_from_inventory(cls, product_id, user=None):
        """Re-pull stock from the linked Material."""
        product = cls.get_product(product_id)
        if not product.inventory_material:
            raise ValueError('Product is not linked to any inventory material.')
        product.update_stock()

        if user:
            AuditService.log_action(
                user=user,
                action='PRODUCT_STOCK_SYNCED',
                entity_type='Product',
                entity_id=str(product.id),
                details={'stock_quantity': float(product.stock_quantity)}
            )
        return product
