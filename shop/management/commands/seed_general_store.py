"""
Seed command for the General Store - Caldan Construction
Creates ~20 general-store products across Stationery, Office Supplies,
Household, Personal Care, Snacks/Drinks, Toys/Games, and Electronics.

Every product is tagged shop_section=GENERAL_STORE and has no
inventory_material link (general store stock is managed directly
via stock_quantity, not from the inventory.Material model).

Mirrors the download + get_or_create pattern from seed_products so
re-running the command is idempotent.
"""

from django.core.management.base import BaseCommand
from django.utils.text import slugify

from shop.models import Product
from shop.management.commands.seed_products import download_image


class Command(BaseCommand):
    help = "Seed general-store products (stationery, household, snacks, etc.)"

    def handle(self, *args, **options):
        self.stdout.write("🌱 Seeding general-store products with images and stock...")

        products_data = [
            # ── Stationery ────────────────────────────────────────────────
            {
                "name": "Bic Crystal Ballpoint Pens (Pack of 10)",
                "category": Product.Category.STATIONERY,
                "unit": Product.Unit.PIECE,
                "description": "Smooth-writing blue ballpoint pens from Bic. Pack of 10 — perfect for the office or school.",
                "short_description": "Pack of 10 blue ballpoint pens",
                "price": 250.00,
                "stock_quantity": 80,
                "in_stock": True,
                "is_featured": True,
                "image_url": "https://images.unsplash.com/photo-1585366119954-e973febefa16?w=600&h=400&fit=crop&q=80",
            },
            {
                "name": "A4 Hardcover Notebook - 200 Pages",
                "category": Product.Category.STATIONERY,
                "unit": Product.Unit.PIECE,
                "description": "Premium A4 hardcover notebook, 200 ruled pages. Lay-flat binding, ribbon marker.",
                "short_description": "A4 hardcover notebook, 200 pages",
                "price": 650.00,
                "stock_quantity": 60,
                "in_stock": True,
                "is_featured": False,
                "image_url": "https://images.unsplash.com/photo-1531346878377-a5be20888e57?w=600&h=400&fit=crop&q=80",
            },
            {
                "name": "Heavy-Duty Stapler with 1000 Staples",
                "category": Product.Category.STATIONERY,
                "unit": Product.Unit.PIECE,
                "description": "Staples up to 25 sheets at once. Includes a starter pack of 1000 #26 staples.",
                "short_description": "Heavy-duty stapler + 1000 staples",
                "price": 950.00,
                "stock_quantity": 25,
                "in_stock": True,
                "is_featured": False,
                "image_url": "https://images.unsplash.com/photo-1611532736597-de2d4265fba3?w=600&h=400&fit=crop&q=80",
            },
            # ── Office Supplies ───────────────────────────────────────────
            {
                "name": "Manila File Folders (Pack of 50)",
                "category": Product.Category.OFFICE_SUPPLIES,
                "unit": Product.Unit.PIECE,
                "description": "Letter-size manila file folders, tabbed. Pack of 50 for organizing documents.",
                "short_description": "Tabbed manila folders, pack of 50",
                "price": 1200.00,
                "stock_quantity": 40,
                "in_stock": True,
                "is_featured": False,
                "image_url": "https://images.unsplash.com/photo-1568667256549-094345857637?w=600&h=400&fit=crop&q=80",
            },
            {
                "name": "White Business Envelopes (Pack of 100)",
                "category": Product.Category.OFFICE_SUPPLIES,
                "unit": Product.Unit.PIECE,
                "description": "DL-size white envelopes with peel-and-seal closure. Pack of 100.",
                "short_description": "DL envelopes, pack of 100",
                "price": 850.00,
                "stock_quantity": 35,
                "in_stock": True,
                "is_featured": False,
                "image_url": "https://images.unsplash.com/photo-1583321500900-82807e458f3c?w=600&h=400&fit=crop&q=80",
            },
            {
                "name": "Clear Packing Tape - 48mm x 100m",
                "category": Product.Category.OFFICE_SUPPLIES,
                "unit": Product.Unit.PIECE,
                "description": "Heavy-duty clear packaging tape. 48mm wide, 100m roll. Strong adhesion.",
                "short_description": "Clear packing tape, 100m roll",
                "price": 350.00,
                "stock_quantity": 100,
                "in_stock": True,
                "is_featured": False,
                "image_url": "https://images.unsplash.com/photo-1607082348824-0a96f2a4b9da?w=600&h=400&fit=crop&q=80",
            },
            # ── Household & Cleaning ──────────────────────────────────────
            {
                "name": "Multi-Surface Cleaner - 1 Litre",
                "category": Product.Category.HOUSEHOLD,
                "unit": Product.Unit.LITRE,
                "description": "All-purpose multi-surface cleaner. Cuts grease, safe for floors, counters, and tiles.",
                "short_description": "Multi-surface cleaner, 1L",
                "price": 450.00,
                "stock_quantity": 70,
                "in_stock": True,
                "is_featured": True,
                "image_url": "https://images.unsplash.com/photo-1585421514738-01798e348b17?w=600&h=400&fit=crop&q=80",
            },
            {
                "name": "Laundry Detergent Powder - 2kg",
                "category": Product.Category.HOUSEHOLD,
                "unit": Product.Unit.KILOGRAM,
                "description": "High-foam laundry powder for whites and colours. 2kg pouch.",
                "short_description": "Laundry detergent, 2kg",
                "price": 750.00,
                "stock_quantity": 55,
                "in_stock": True,
                "is_featured": False,
                "image_url": "https://images.unsplash.com/photo-1583947582886-f40ec195ec3e?w=600&h=400&fit=crop&q=80",
            },
            {
                "name": "Bar Soap - Family Pack (6 bars)",
                "category": Product.Category.HOUSEHOLD,
                "unit": Product.Unit.PIECE,
                "description": "Moisturising family-size bar soap. Pack of 6, gentle on skin.",
                "short_description": "Family soap pack of 6",
                "price": 380.00,
                "stock_quantity": 90,
                "in_stock": True,
                "is_featured": False,
                "image_url": "https://images.unsplash.com/photo-1600857544200-b2f666a9a2ec?w=600&h=400&fit=crop&q=80",
            },
            {
                "name": "Soft-Bristle Broom with Handle",
                "category": Product.Category.HOUSEHOLD,
                "unit": Product.Unit.PIECE,
                "description": "Indoor broom with hardwood handle and stiff synthetic bristles. Long-lasting.",
                "short_description": "Indoor broom with handle",
                "price": 550.00,
                "stock_quantity": 30,
                "in_stock": True,
                "is_featured": False,
                "image_url": "https://images.unsplash.com/photo-1583947581924-860bda3c5fe1?w=600&h=400&fit=crop&q=80",
            },
            # ── Personal Care ─────────────────────────────────────────────
            {
                "name": "Fluoride Toothpaste - 150ml (Twin Pack)",
                "category": Product.Category.PERSONAL_CARE,
                "unit": Product.Unit.PIECE,
                "description": "Cavity-protection fluoride toothpaste, fresh mint flavour. Twin pack, 150ml each.",
                "short_description": "Fluoride toothpaste, twin pack",
                "price": 480.00,
                "stock_quantity": 65,
                "in_stock": True,
                "is_featured": True,
                "image_url": "https://images.unsplash.com/photo-1556228852-80b6e5eeff06?w=600&h=400&fit=crop&q=80",
            },
            {
                "name": "Moisturising Shampoo - 400ml",
                "category": Product.Category.PERSONAL_CARE,
                "unit": Product.Unit.PIECE,
                "description": "Daily-use shampoo with coconut oil. Suitable for all hair types. 400ml bottle.",
                "short_description": "Moisturising shampoo, 400ml",
                "price": 650.00,
                "stock_quantity": 50,
                "in_stock": True,
                "is_featured": False,
                "image_url": "https://images.unsplash.com/photo-1556228720-195a672e8a03?w=600&h=400&fit=crop&q=80",
            },
            {
                "name": "Roll-On Deodorant - 50ml",
                "category": Product.Category.PERSONAL_CARE,
                "unit": Product.Unit.PIECE,
                "description": "48-hour protection roll-on deodorant. Fresh scent, alcohol-free.",
                "short_description": "Roll-on deodorant, 50ml",
                "price": 280.00,
                "stock_quantity": 80,
                "in_stock": True,
                "is_featured": False,
                "image_url": "https://images.unsplash.com/photo-1612817288484-6f916006741a?w=600&h=400&fit=crop&q=80",
            },
            # ── Snacks & Drinks ───────────────────────────────────────────
            {
                "name": "Assorted Biscuits - 800g Tin",
                "category": Product.Category.SNACKS_DRINKS,
                "unit": Product.Unit.KILOGRAM,
                "description": "Premium assorted cream biscuits. Sealed tin for freshness. 800g.",
                "short_description": "Assorted biscuits, 800g tin",
                "price": 950.00,
                "stock_quantity": 45,
                "in_stock": True,
                "is_featured": True,
                "image_url": "https://images.unsplash.com/photo-1558961363-fa8fdf82db35?w=600&h=400&fit=crop&q=80",
            },
            {
                "name": "Mango Fruit Juice - 1 Litre",
                "category": Product.Category.SNACKS_DRINKS,
                "unit": Product.Unit.LITRE,
                "description": "100% mango juice, no added sugar. Refrigerate after opening. 1L carton.",
                "short_description": "Mango juice, 1L",
                "price": 320.00,
                "stock_quantity": 60,
                "in_stock": True,
                "is_featured": False,
                "image_url": "https://images.unsplash.com/photo-1546173159-315724a31696?w=600&h=400&fit=crop&q=80",
            },
            {
                "name": "Bottled Drinking Water - 1.5L (Pack of 6)",
                "category": Product.Category.SNACKS_DRINKS,
                "unit": Product.Unit.PIECE,
                "description": "Purified bottled water, 1.5L each. Pack of 6 for home or office.",
                "short_description": "Bottled water 1.5L, pack of 6",
                "price": 480.00,
                "stock_quantity": 120,
                "in_stock": True,
                "is_featured": False,
                "image_url": "https://images.unsplash.com/photo-1564419320461-6870880221ad?w=600&h=400&fit=crop&q=80",
            },
            # ── Electronics & Accessories ─────────────────────────────────
            {
                "name": "AA Alkaline Batteries (Pack of 8)",
                "category": Product.Category.ELECTRONICS,
                "unit": Product.Unit.PIECE,
                "description": "Long-lasting AA alkaline batteries. Pack of 8 — ideal for remotes and toys.",
                "short_description": "AA batteries, pack of 8",
                "price": 550.00,
                "stock_quantity": 75,
                "in_stock": True,
                "is_featured": True,
                # AA batteries — close-up product shot from Unsplash.
                "image_url": "https://images.unsplash.com/photo-1611428813653-321def57a6b8?w=600&h=400&fit=crop&q=80",
            },
            {
                "name": "Dual USB Wall Charger - 2.4A",
                "category": Product.Category.ELECTRONICS,
                "unit": Product.Unit.PIECE,
                "description": "Compact 2-port USB wall charger, 2.4A total output. Smart IC for safe fast charging.",
                "short_description": "Dual USB wall charger",
                "price": 850.00,
                "stock_quantity": 40,
                "in_stock": True,
                "is_featured": False,
                "image_url": "https://images.unsplash.com/photo-1583863788434-e58a36330cf0?w=600&h=400&fit=crop&q=80",
            },
            {
                "name": "Braided USB-C Cable - 1m",
                "category": Product.Category.ELECTRONICS,
                "unit": Product.Unit.PIECE,
                "description": "Durable braided USB-C to USB-A cable, 1 metre. Tangle-free, fast charging.",
                "short_description": "USB-C cable, 1m braided",
                "price": 450.00,
                "stock_quantity": 55,
                "in_stock": True,
                "is_featured": False,
                "image_url": "https://images.unsplash.com/photo-1583863788434-e58a36330cf0?w=600&h=400&fit=crop&q=80",
            },
            # ── Toys & Games ──────────────────────────────────────────────
            {
                "name": "Wooden Building Blocks (50 pieces)",
                "category": Product.Category.TOYS_GAMES,
                "unit": Product.Unit.PIECE,
                "description": "Coloured wooden building blocks, 50-piece set. Safe, non-toxic paint. Ages 3+.",
                "short_description": "Wooden blocks, 50 pieces",
                "price": 1450.00,
                "stock_quantity": 20,
                "in_stock": True,
                "is_featured": True,
                "image_url": "https://images.unsplash.com/photo-1558060370-d644479cb6f7?w=600&h=400&fit=crop&q=80",
            },
        ]

        created_count = 0
        updated_count = 0

        for data in products_data:
            slug = slugify(data["name"])

            # Download image (reuses the helper from seed_products)
            image_file = None
            if data.get("image_url"):
                image_file = download_image(data["image_url"], stdout=self.stdout)
                if image_file:
                    self.stdout.write(f"  📷 Downloaded image for: {data['name']}")

            product, created = Product.objects.get_or_create(
                slug=slug,
                defaults={
                    "name": data["name"],
                    "shop_section": Product.ShopSection.GENERAL_STORE,
                    "category": data["category"],
                    "unit": data["unit"],
                    "description": data["description"],
                    "short_description": data["short_description"],
                    "price": data["price"],
                    "stock_quantity": data["stock_quantity"],
                    "in_stock": data["in_stock"],
                    "is_featured": data["is_featured"],
                    "is_active": True,
                    # General store products intentionally have NO inventory link
                    "inventory_material": None,
                },
            )

            # Save image (always when we got one — refreshes if URL changed)
            if image_file:
                product.image.save(f"{slug}.jpg", image_file, save=True)

            if created:
                self.stdout.write(f"  ✅ Created: {product.name} (Stock: {product.stock_quantity})")
                created_count += 1
            else:
                # Re-write every field so re-running the seed updates prices,
                # stock levels, descriptions, etc.
                product.name = data["name"]
                product.shop_section = Product.ShopSection.GENERAL_STORE
                product.category = data["category"]
                product.unit = data["unit"]
                product.description = data["description"]
                product.short_description = data["short_description"]
                product.price = data["price"]
                product.stock_quantity = data["stock_quantity"]
                product.in_stock = data["in_stock"]
                product.is_featured = data["is_featured"]
                product.is_active = True
                product.inventory_material = None
                product.save()
                self.stdout.write(f"  🔄 Updated: {product.name} (Stock: {product.stock_quantity})")
                updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"\n✅ General store seeding complete! Created: {created_count}, Updated: {updated_count}"
            )
        )