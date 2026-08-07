"""
Seed command for Inventory Materials - Caldan Construction
Creates construction materials with stock levels.
"""

from django.core.management.base import BaseCommand
from inventory.models import Material
from inventory.models.supplier import Supplier


class Command(BaseCommand):
    help = "Seed inventory materials data into the database"

    def handle(self, *args, **options):
        self.stdout.write("🌱 Seeding inventory materials...")

        # Create suppliers first
        suppliers_data = [
            {
                "name": "Nakuru Cement Distributors",
                "contact_person": "John Maina",
                "phone": "0712345678",
                "email": "info@nakurucement.co.ke",
            },
            {
                "name": "Kenya Steel Suppliers",
                "contact_person": "Mary Wanjiku",
                "phone": "0723456789",
                "email": "info@kenyasteel.co.ke",
            },
            {
                "name": "Nakuru Building Materials",
                "contact_person": "Peter Ochieng",
                "phone": "0734567890",
                "email": "info@nakurubuild.co.ke",
            },
        ]

        created_suppliers = []
        for data in suppliers_data:
            supplier, created = Supplier.objects.get_or_create(
                name=data["name"],
                defaults={
                    "contact_person": data["contact_person"],
                    "phone": data["phone"],
                    "email": data["email"],
                },
            )
            if created:
                self.stdout.write(f"  ✅ Created supplier: {supplier.name}")
            created_suppliers.append(supplier)

        # Materials data
        materials_data = [
            {
                "name": "Portland Cement",
                "category": Material.Category.CEMENT,
                "unit": Material.Unit.BAG,
                "current_quantity": 150,
                "minimum_threshold": 30,
                "reorder_quantity": 100,
                "unit_cost": 800.00,
                "supplier": created_suppliers[0] if created_suppliers else None,
            },
            {
                "name": "12mm Steel Bar",
                "category": Material.Category.STEEL,
                "unit": Material.Unit.PIECE,
                "current_quantity": 200,
                "minimum_threshold": 50,
                "reorder_quantity": 150,
                "unit_cost": 1200.00,
                "supplier": created_suppliers[1] if created_suppliers else None,
            },
            {
                "name": "River Sand",
                "category": Material.Category.SAND,
                "unit": Material.Unit.TONNE,
                "current_quantity": 10,
                "minimum_threshold": 3,
                "reorder_quantity": 8,
                "unit_cost": 2500.00,
                "supplier": created_suppliers[2] if created_suppliers else None,
            },
            {
                "name": "Concrete Blocks - 6\"",
                "category": Material.Category.BLOCKS,
                "unit": Material.Unit.PIECE,
                "current_quantity": 500,
                "minimum_threshold": 100,
                "reorder_quantity": 300,
                "unit_cost": 350.00,
                "supplier": created_suppliers[2] if created_suppliers else None,
            },
            {
                "name": "Emulsion Paint",
                "category": Material.Category.PAINT,
                "unit": Material.Unit.LITRE,
                "current_quantity": 50,
                "minimum_threshold": 10,
                "reorder_quantity": 30,
                "unit_cost": 140.00,
                "supplier": created_suppliers[2] if created_suppliers else None,
            },
            {
                "name": "Timber - 4x2",
                "category": Material.Category.TIMBER,
                "unit": Material.Unit.METRE,
                "current_quantity": 300,
                "minimum_threshold": 60,
                "reorder_quantity": 200,
                "unit_cost": 450.00,
                "supplier": created_suppliers[2] if created_suppliers else None,
            },
            {
                "name": "PVC Pipes - 4\"",
                "category": Material.Category.PLUMBING,
                "unit": Material.Unit.METRE,
                "current_quantity": 100,
                "minimum_threshold": 20,
                "reorder_quantity": 60,
                "unit_cost": 280.00,
                "supplier": created_suppliers[2] if created_suppliers else None,
            },
            {
                "name": "Electrical Cable - 2.5mm",
                "category": Material.Category.ELECTRICAL,
                "unit": Material.Unit.METRE,
                "current_quantity": 200,
                "minimum_threshold": 40,
                "reorder_quantity": 120,
                "unit_cost": 180.00,
                "supplier": created_suppliers[2] if created_suppliers else None,
            },
            {
                "name": "Ballast",
                "category": Material.Category.AGGREGATE,
                "unit": Material.Unit.TONNE,
                "current_quantity": 8,
                "minimum_threshold": 2,
                "reorder_quantity": 6,
                "unit_cost": 3200.00,
                "supplier": created_suppliers[2] if created_suppliers else None,
            },
            {
                "name": "Trowel",
                "category": Material.Category.TOOLS,
                "unit": Material.Unit.PIECE,
                "current_quantity": 15,
                "minimum_threshold": 3,
                "reorder_quantity": 10,
                "unit_cost": 650.00,
                "supplier": created_suppliers[2] if created_suppliers else None,
            },
        ]

        created_count = 0
        updated_count = 0

        for data in materials_data:
            material, created = Material.objects.get_or_create(
                name=data["name"],
                defaults={
                    "category": data["category"],
                    "unit": data["unit"],
                    "current_quantity": data["current_quantity"],
                    "minimum_threshold": data["minimum_threshold"],
                    "reorder_quantity": data["reorder_quantity"],
                    "unit_cost": data["unit_cost"],
                    "supplier": data["supplier"],
                    "is_active": True,
                },
            )

            if created:
                self.stdout.write(f"  ✅ Created: {material.name}")
                created_count += 1
            else:
                material.category = data["category"]
                material.unit = data["unit"]
                material.current_quantity = data["current_quantity"]
                material.minimum_threshold = data["minimum_threshold"]
                material.reorder_quantity = data["reorder_quantity"]
                material.unit_cost = data["unit_cost"]
                material.supplier = data["supplier"]
                material.is_active = True
                material.save()
                self.stdout.write(f"  🔄 Updated: {material.name}")
                updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"\n✅ Materials seeding complete! Created: {created_count}, Updated: {updated_count}"
            )
        )