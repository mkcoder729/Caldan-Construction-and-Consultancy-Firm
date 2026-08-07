"""
Seed command for Construction Shop Products - Caldan Construction
Creates 24+ construction materials with images and stock.

Every product is tagged shop_section=CONSTRUCTION. For general-store
products (stationery, household, snacks, etc.) run seed_general_store.
"""

from django.core.management.base import BaseCommand
from django.utils.text import slugify
from django.core.files.base import ContentFile
from shop.models import Product
import requests


def download_image(url, stdout=None):
    """
    Module-level helper: fetch an image and return a Django ContentFile.

    Lives at module scope (not a Command method) so it can be reused by
    other seed commands like seed_general_store.

    Args:
        url: Remote image URL.
        stdout: Optional stream to write warnings to. Pass
            ``self.stdout`` from a Command to mirror user-facing logs.

    Returns:
        ContentFile on success, ``None`` on any failure (logged once).
    """
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return ContentFile(response.content, name='product.jpg')
        if stdout is not None:
            stdout.write(f"  ⚠️ Failed to download image: HTTP {response.status_code}")
        return None
    except Exception as exc:
        if stdout is not None:
            stdout.write(f"  ⚠️ Failed to download image: {exc}")
        return None


class Command(BaseCommand):
    help = "Seed construction shop products with images and stock"

    def handle(self, *args, **options):
        self.stdout.write("🌱 Seeding construction shop products with images and stock...")

        products_data = [
            # Cement
            {
                "name": "Portland Cement - 50kg",
                "category": Product.Category.CEMENT,
                "unit": Product.Unit.BAG,
                "description": "High-quality Portland cement for all construction needs. 50kg bag.",
                "short_description": "Premium Portland cement, 50kg bag",
                "price": 850.00,
                "stock_quantity": 150,
                "in_stock": True,
                "is_featured": True,
                "image_url": "https://images.unsplash.com/photo-1581094794329-c8112a89af12?w=600&h=400&fit=crop&q=80",
            },
            {
                "name": "Cement - 25kg",
                "category": Product.Category.CEMENT,
                "unit": Product.Unit.BAG,
                "description": "Quality Portland cement for smaller projects. 25kg bag.",
                "short_description": "Portland cement, 25kg bag",
                "price": 450.00,
                "stock_quantity": 200,
                "in_stock": True,
                "is_featured": False,
                "image_url": "https://images.unsplash.com/photo-1581094794329-c8112a89af12?w=600&h=400&fit=crop&q=80",
            },
            # Steel
            {
                "name": "12mm Reinforcing Steel Bar",
                "category": Product.Category.STEEL,
                "unit": Product.Unit.PIECE,
                "description": "High-quality 12mm reinforcing steel bar for concrete reinforcement.",
                "short_description": "12mm steel bar for reinforcement",
                "price": 1200.00,
                "stock_quantity": 200,
                "in_stock": True,
                "is_featured": False,
                "image_url": "https://images.unsplash.com/photo-1581094794329-c8112a89af12?w=600&h=400&fit=crop&q=80",
            },
            {
                "name": "16mm Reinforcing Steel Bar",
                "category": Product.Category.STEEL,
                "unit": Product.Unit.PIECE,
                "description": "High-quality 16mm reinforcing steel bar for heavy-duty concrete reinforcement.",
                "short_description": "16mm steel bar for heavy reinforcement",
                "price": 1600.00,
                "stock_quantity": 100,
                "in_stock": True,
                "is_featured": False,
                "image_url": "https://images.unsplash.com/photo-1581094794329-c8112a89af12?w=600&h=400&fit=crop&q=80",
            },
            {
                "name": "Steel Mesh - 2.4m x 1.2m",
                "category": Product.Category.STEEL,
                "unit": Product.Unit.PIECE,
                "description": "Welded steel mesh for concrete slab reinforcement.",
                "short_description": "Welded steel mesh, 2.4m x 1.2m",
                "price": 3500.00,
                "stock_quantity": 50,
                "in_stock": True,
                "is_featured": False,
                "image_url": "https://images.unsplash.com/photo-1581094794329-c8112a89af12?w=600&h=400&fit=crop&q=80",
            },
            # Sand
            {
                "name": "River Sand - 1 Tonne",
                "category": Product.Category.SAND,
                "unit": Product.Unit.TONNE,
                "description": "Clean river sand suitable for concrete mixing and plastering.",
                "short_description": "Clean river sand, 1 tonne",
                "price": 2500.00,
                "stock_quantity": 20,
                "in_stock": True,
                "is_featured": False,
                "image_url": "https://images.unsplash.com/photo-1581094794329-c8112a89af12?w=600&h=400&fit=crop&q=80",
            },
            {
                "name": "Building Sand - 1 Tonne",
                "category": Product.Category.SAND,
                "unit": Product.Unit.TONNE,
                "description": "Fine building sand for plastering and finishing work.",
                "short_description": "Fine building sand, 1 tonne",
                "price": 2800.00,
                "stock_quantity": 15,
                "in_stock": True,
                "is_featured": False,
                "image_url": "https://images.unsplash.com/photo-1581094794329-c8112a89af12?w=600&h=400&fit=crop&q=80",
            },
            # Aggregates
            {
                "name": "Ballast - 1 Tonne",
                "category": Product.Category.AGGREGATE,
                "unit": Product.Unit.TONNE,
                "description": "Crushed stone ballast for concrete production.",
                "short_description": "Crushed ballast, 1 tonne",
                "price": 3200.00,
                "stock_quantity": 10,
                "in_stock": True,
                "is_featured": False,
                "image_url": "https://images.unsplash.com/photo-1581094794329-c8112a89af12?w=600&h=400&fit=crop&q=80",
            },
            {
                "name": "Crushed Stone - 1 Tonne",
                "category": Product.Category.AGGREGATE,
                "unit": Product.Unit.TONNE,
                "description": "Crushed stone for drainage and landscaping.",
                "short_description": "Crushed stone, 1 tonne",
                "price": 3000.00,
                "stock_quantity": 12,
                "in_stock": True,
                "is_featured": False,
                "image_url": "https://images.unsplash.com/photo-1581094794329-c8112a89af12?w=600&h=400&fit=crop&q=80",
            },
            # Blocks
            {
                "name": "Concrete Blocks - 6\"",
                "category": Product.Category.BLOCKS,
                "unit": Product.Unit.PIECE,
                "description": "Durable 6-inch concrete blocks for wall construction.",
                "short_description": "6-inch concrete blocks",
                "price": 350.00,
                "stock_quantity": 500,
                "in_stock": True,
                "is_featured": False,
                "image_url": "https://images.unsplash.com/photo-1581094794329-c8112a89af12?w=600&h=400&fit=crop&q=80",
            },
            {
                "name": "Concrete Blocks - 4\"",
                "category": Product.Category.BLOCKS,
                "unit": Product.Unit.PIECE,
                "description": "Durable 4-inch concrete blocks for partition walls.",
                "short_description": "4-inch concrete blocks",
                "price": 280.00,
                "stock_quantity": 400,
                "in_stock": True,
                "is_featured": False,
                "image_url": "https://images.unsplash.com/photo-1581094794329-c8112a89af12?w=600&h=400&fit=crop&q=80",
            },
            # Paint
            {
                "name": "Emulsion Paint - White 20L",
                "category": Product.Category.PAINT,
                "unit": Product.Unit.LITRE,
                "description": "Premium quality white emulsion paint for interior walls. 20L bucket.",
                "short_description": "White emulsion paint, 20L",
                "price": 2800.00,
                "stock_quantity": 30,
                "in_stock": True,
                "is_featured": True,
                "image_url": "https://images.unsplash.com/photo-1581094794329-c8112a89af12?w=600&h=400&fit=crop&q=80",
            },
            {
                "name": "Exterior Paint - 20L",
                "category": Product.Category.PAINT,
                "unit": Product.Unit.LITRE,
                "description": "Weather-resistant exterior paint for outdoor walls. 20L bucket.",
                "short_description": "Exterior paint, 20L",
                "price": 3200.00,
                "stock_quantity": 20,
                "in_stock": True,
                "is_featured": False,
                "image_url": "https://images.unsplash.com/photo-1581094794329-c8112a89af12?w=600&h=400&fit=crop&q=80",
            },
            # Timber
            {
                "name": "Timber - 4x2",
                "category": Product.Category.TIMBER,
                "unit": Product.Unit.METRE,
                "description": "Kiln-dried 4x2 timber for construction and framing.",
                "short_description": "4x2 timber, per metre",
                "price": 450.00,
                "stock_quantity": 300,
                "in_stock": True,
                "is_featured": False,
                "image_url": "https://images.unsplash.com/photo-1581094794329-c8112a89af12?w=600&h=400&fit=crop&q=80",
            },
            {
                "name": "Timber - 6x2",
                "category": Product.Category.TIMBER,
                "unit": Product.Unit.METRE,
                "description": "Kiln-dried 6x2 timber for heavy-duty framing and roofing.",
                "short_description": "6x2 timber, per metre",
                "price": 650.00,
                "stock_quantity": 200,
                "in_stock": True,
                "is_featured": False,
                "image_url": "https://images.unsplash.com/photo-1581094794329-c8112a89af12?w=600&h=400&fit=crop&q=80",
            },
            # Plumbing
            {
                "name": "PVC Pipes - 4\"",
                "category": Product.Category.PLUMBING,
                "unit": Product.Unit.METRE,
                "description": "Durable 4-inch PVC pipes for plumbing and drainage.",
                "short_description": "4-inch PVC pipes",
                "price": 280.00,
                "stock_quantity": 100,
                "in_stock": True,
                "is_featured": False,
                "image_url": "https://images.unsplash.com/photo-1581094794329-c8112a89af12?w=600&h=400&fit=crop&q=80",
            },
            {
                "name": "PVC Pipes - 2\"",
                "category": Product.Category.PLUMBING,
                "unit": Product.Unit.METRE,
                "description": "Durable 2-inch PVC pipes for plumbing and drainage.",
                "short_description": "2-inch PVC pipes",
                "price": 180.00,
                "stock_quantity": 150,
                "in_stock": True,
                "is_featured": False,
                "image_url": "https://images.unsplash.com/photo-1581094794329-c8112a89af12?w=600&h=400&fit=crop&q=80",
            },
            # Electrical
            {
                "name": "Electrical Cable - 2.5mm",
                "category": Product.Category.ELECTRICAL,
                "unit": Product.Unit.METRE,
                "description": "High-quality 2.5mm electrical cable for wiring.",
                "short_description": "2.5mm electrical cable",
                "price": 180.00,
                "stock_quantity": 200,
                "in_stock": True,
                "is_featured": False,
                "image_url": "https://images.unsplash.com/photo-1581094794329-c8112a89af12?w=600&h=400&fit=crop&q=80",
            },
            {
                "name": "Electrical Cable - 1.5mm",
                "category": Product.Category.ELECTRICAL,
                "unit": Product.Unit.METRE,
                "description": "High-quality 1.5mm electrical cable for lighting.",
                "short_description": "1.5mm electrical cable",
                "price": 120.00,
                "stock_quantity": 250,
                "in_stock": True,
                "is_featured": False,
                "image_url": "https://images.unsplash.com/photo-1581094794329-c8112a89af12?w=600&h=400&fit=crop&q=80",
            },
            # Tools
            {
                "name": "Trowel - Professional",
                "category": Product.Category.TOOLS,
                "unit": Product.Unit.PIECE,
                "description": "Professional-grade trowel for plastering and finishing.",
                "short_description": "Professional trowel",
                "price": 650.00,
                "stock_quantity": 25,
                "in_stock": True,
                "is_featured": False,
                "image_url": "https://images.unsplash.com/photo-1581094794329-c8112a89af12?w=600&h=400&fit=crop&q=80",
            },
            {
                "name": "Concrete Mixer - Portable",
                "category": Product.Category.TOOLS,
                "unit": Product.Unit.PIECE,
                "description": "Portable concrete mixer for small to medium projects.",
                "short_description": "Portable concrete mixer",
                "price": 45000.00,
                "stock_quantity": 5,
                "in_stock": True,
                "is_featured": True,
                "image_url": "https://images.unsplash.com/photo-1581094794329-c8112a89af12?w=600&h=400&fit=crop&q=80",
            },
            {
                "name": "Wheelbarrow - Heavy Duty",
                "category": Product.Category.TOOLS,
                "unit": Product.Unit.PIECE,
                "description": "Heavy-duty wheelbarrow for construction sites.",
                "short_description": "Heavy-duty wheelbarrow",
                "price": 8500.00,
                "stock_quantity": 10,
                "in_stock": True,
                "is_featured": False,
                "image_url": "https://images.unsplash.com/photo-1581094794329-c8112a89af12?w=600&h=400&fit=crop&q=80",
            },
            # Other
            {
                "name": "Sandwich Panel - Roofing",
                "category": Product.Category.OTHER,
                "unit": Product.Unit.SQUARE_METRE,
                "description": "Insulated sandwich roofing panels for commercial and industrial buildings.",
                "short_description": "Insulated roofing panels",
                "price": 1800.00,
                "stock_quantity": 80,
                "in_stock": True,
                "is_featured": False,
                "image_url": "https://images.unsplash.com/photo-1581094794329-c8112a89af12?w=600&h=400&fit=crop&q=80",
            },
            {
                "name": "Waterproofing Membrane - 10m Roll",
                "category": Product.Category.OTHER,
                "unit": Product.Unit.PIECE,
                "description": "High-quality waterproofing membrane for roofs and basements.",
                "short_description": "Waterproofing membrane, 10m roll",
                "price": 5500.00,
                "stock_quantity": 20,
                "in_stock": True,
                "is_featured": False,
                "image_url": "https://images.unsplash.com/photo-1581094794329-c8112a89af12?w=600&h=400&fit=crop&q=80",
            },
        ]

        created_count = 0
        updated_count = 0

        for data in products_data:
            slug = slugify(data["name"])

            # Download image
            image_file = None
            if data.get("image_url"):
                image_file = download_image(data["image_url"], stdout=self.stdout)
                if image_file:
                    self.stdout.write(f"  📷 Downloaded image for: {data['name']}")

            product, created = Product.objects.get_or_create(
                slug=slug,
                defaults={
                    "name": data["name"],
                    "shop_section": Product.ShopSection.CONSTRUCTION,
                    "category": data["category"],
                    "unit": data["unit"],
                    "description": data["description"],
                    "short_description": data["short_description"],
                    "price": data["price"],
                    "stock_quantity": data["stock_quantity"],
                    "in_stock": data["in_stock"],
                    "is_featured": data["is_featured"],
                    "is_active": True,
                },
            )

            # Save image (always — refreshes if URL changed; safe no-op otherwise)
            if image_file:
                product.image.save(f"{slug}.jpg", image_file, save=True)

            if created:
                self.stdout.write(f"  ✅ Created: {product.name} (Stock: {product.stock_quantity})")
                created_count += 1
            else:
                product.name = data["name"]
                product.shop_section = Product.ShopSection.CONSTRUCTION
                product.category = data["category"]
                product.unit = data["unit"]
                product.description = data["description"]
                product.short_description = data["short_description"]
                product.price = data["price"]
                product.stock_quantity = data["stock_quantity"]
                product.in_stock = data["in_stock"]
                product.is_featured = data["is_featured"]
                product.is_active = True
                product.save()
                self.stdout.write(f"  🔄 Updated: {product.name} (Stock: {product.stock_quantity})")
                updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"\n✅ Construction products seeding complete! Created: {created_count}, Updated: {updated_count}"
            )
        )