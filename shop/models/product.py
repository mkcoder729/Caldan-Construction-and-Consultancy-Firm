"""
Product model for the online shop.
Caldan Construction - "Building Kenya's Future, One Project at a Time."
"""

from django.db import models
from django.utils.text import slugify
from django.utils import timezone
from django.conf import settings


class Product(models.Model):
    """
    Product model for the online shop. Houses both the Construction Shop
    (cement, steel, sand, …) and the General Store (stationery, household,
    snacks, …) so a single cart, checkout, and admin can serve both.

    The top-level split is `shop_section` (CONSTRUCTION vs GENERAL_STORE);
    the sub-classification is `category` (Cement, Stationery, …).
    """

    class ShopSection(models.TextChoices):
        """
        Top-level storefront grouping. A product lives in exactly one
        section. The section drives the storefront switcher in the
        navbar, the hero copy on the public shop pages, and the
        dashboard product filter.
        """
        CONSTRUCTION = 'CONSTRUCTION', 'Construction Shop'
        GENERAL_STORE = 'GENERAL_STORE', 'General Store'

    class Category(models.TextChoices):
        # ── Construction sub-categories ────────────────────────────────
        CEMENT = 'CEMENT', 'Cement'
        STEEL = 'STEEL', 'Steel'
        SAND = 'SAND', 'Sand'
        AGGREGATE = 'AGGREGATE', 'Aggregate'
        BLOCKS = 'BLOCKS', 'Blocks'
        PAINT = 'PAINT', 'Paint'
        TIMBER = 'TIMBER', 'Timber'
        PLUMBING = 'PLUMBING', 'Plumbing'
        ELECTRICAL = 'ELECTRICAL', 'Electrical'
        TOOLS = 'TOOLS', 'Tools'
        OTHER = 'OTHER', 'Other'
        # ── General Store sub-categories ───────────────────────────────
        STATIONERY = 'STATIONERY', 'Stationery'
        OFFICE_SUPPLIES = 'OFFICE_SUPPLIES', 'Office Supplies'
        HOUSEHOLD = 'HOUSEHOLD', 'Household & Cleaning'
        PERSONAL_CARE = 'PERSONAL_CARE', 'Personal Care'
        SNACKS_DRINKS = 'SNACKS_DRINKS', 'Snacks & Drinks'
        TOYS_GAMES = 'TOYS_GAMES', 'Toys & Games'
        ELECTRONICS = 'ELECTRONICS', 'Electronics & Accessories'

    # Map every Category to its parent ShopSection so forms, templates,
    # and seed commands can derive one from the other without branching.
    CATEGORY_TO_SECTION = {
        Category.CEMENT: ShopSection.CONSTRUCTION,
        Category.STEEL: ShopSection.CONSTRUCTION,
        Category.SAND: ShopSection.CONSTRUCTION,
        Category.AGGREGATE: ShopSection.CONSTRUCTION,
        Category.BLOCKS: ShopSection.CONSTRUCTION,
        Category.PAINT: ShopSection.CONSTRUCTION,
        Category.TIMBER: ShopSection.CONSTRUCTION,
        Category.PLUMBING: ShopSection.CONSTRUCTION,
        Category.ELECTRICAL: ShopSection.CONSTRUCTION,
        Category.TOOLS: ShopSection.CONSTRUCTION,
        Category.OTHER: ShopSection.CONSTRUCTION,
        Category.STATIONERY: ShopSection.GENERAL_STORE,
        Category.OFFICE_SUPPLIES: ShopSection.GENERAL_STORE,
        Category.HOUSEHOLD: ShopSection.GENERAL_STORE,
        Category.PERSONAL_CARE: ShopSection.GENERAL_STORE,
        Category.SNACKS_DRINKS: ShopSection.GENERAL_STORE,
        Category.TOYS_GAMES: ShopSection.GENERAL_STORE,
        Category.ELECTRONICS: ShopSection.GENERAL_STORE,
    }

    class Unit(models.TextChoices):
        BAG = 'BAG', 'Bag'
        TONNE = 'TONNE', 'Tonne'
        PIECE = 'PIECE', 'Piece'
        LITRE = 'LITRE', 'Litre'
        METRE = 'METRE', 'Metre'
        SQUARE_METRE = 'SQUARE_METRE', 'Square Metre'
        CUBIC_METRE = 'CUBIC_METRE', 'Cubic Metre'
        KILOGRAM = 'KILOGRAM', 'Kilogram'
        OTHER = 'OTHER', 'Other'

    # Basic Information
    name = models.CharField(max_length=200, db_index=True)
    slug = models.SlugField(unique=True, max_length=200, db_index=True)
    shop_section = models.CharField(
        max_length=20,
        choices=ShopSection.choices,
        default=ShopSection.CONSTRUCTION,
        db_index=True,
        help_text=(
            'Top-level storefront grouping. CONSTRUCTION for materials, '
            'GENERAL_STORE for stationery, household, snacks, etc.'
        ),
    )
    category = models.CharField(max_length=20, choices=Category.choices, db_index=True)
    unit = models.CharField(max_length=20, choices=Unit.choices)

    # Description
    description = models.TextField()
    short_description = models.CharField(max_length=200, blank=True, default='')

    # Pricing
    price = models.DecimalField(max_digits=10, decimal_places=2)
    compare_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Original price for sale display'
    )

    # Stock - Link to Inventory
    inventory_material = models.ForeignKey(
        'inventory.Material',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='shop_products',
        help_text='Link to inventory material for automatic stock updates'
    )
    stock_quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text='Current stock quantity (auto-updated from inventory)'
    )

    # Images
    image = models.ImageField(
        upload_to='shop/products/',
        null=True,
        blank=True,
        help_text='Main product image (optional — leave blank to use placeholder)',
    )
    additional_images = models.JSONField(
        default=list,
        blank=True,
        help_text='Additional product images (Cloudinary URLs)'
    )

    # Status
    is_active = models.BooleanField(default=True, db_index=True)
    is_featured = models.BooleanField(default=False, db_index=True)
    in_stock = models.BooleanField(default=True, db_index=True)

    # SEO
    meta_title = models.CharField(max_length=200, blank=True, default='')
    meta_description = models.CharField(max_length=200, blank=True, default='')

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'shop_products'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['category', 'is_active']),
            models.Index(fields=['shop_section', 'is_active']),
            models.Index(fields=['is_featured']),
            models.Index(fields=['in_stock']),
            models.Index(fields=['slug']),
        ]

    def __str__(self):
        return f"{self.name} - KES {self.price}"

    def save(self, *args, **kwargs):
        """Auto-generate slug and update stock from inventory."""
        if not self.slug:
            self.slug = slugify(self.name)

        # Update stock from linked inventory
        if self.inventory_material:
            self.stock_quantity = self.inventory_material.current_quantity
            self.in_stock = self.stock_quantity > 0

        super().save(*args, **kwargs)

    def update_stock(self):
        """Manually update stock from linked inventory."""
        if self.inventory_material:
            self.stock_quantity = self.inventory_material.current_quantity
            self.in_stock = self.stock_quantity > 0
            self.save(update_fields=['stock_quantity', 'in_stock'])
            return True
        return False

    @property
    def image_url(self):
        """Return image URL or placeholder."""
        if self.image:
            return self.image.url
        return '/static/images/placeholder-product.png'

    @property
    def has_compare_price(self):
        """Check if product has a compare price."""
        return self.compare_price and self.compare_price > self.price

    @property
    def discount_percentage(self):
        """Calculate discount percentage if compare price exists."""
        if self.has_compare_price:
            return int(((self.compare_price - self.price) / self.compare_price) * 100)
        return 0

    @property
    def is_low_stock(self):
        """Check if product is low on stock."""
        return self.stock_quantity <= 5 and self.stock_quantity > 0

    @property
    def is_out_of_stock(self):
        """Check if product is out of stock."""
        return self.stock_quantity <= 0