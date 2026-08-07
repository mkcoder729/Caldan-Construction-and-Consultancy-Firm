"""
Seed command for Services - Caldan Construction
Creates all 9 service categories with proper data and FontAwesome icons.
"""

from django.core.management.base import BaseCommand
from django.utils.text import slugify
from services.models import Service


class Command(BaseCommand):
    help = "Seed services data into the database"

    def handle(self, *args, **options):
        self.stdout.write("🌱 Seeding services...")

        services_data = [
            {
                "name": "Design & Construction",
                "category": Service.Category.DESIGN,
                "description": "Full design and construction services from concept to completion. We handle everything from architectural design to final handover.",
                "icon": "fas fa-drafting-compass",
                "display_order": 1,
            },
            {
                "name": "Renovations",
                "category": Service.Category.RENOVATION,
                "description": "Home, office, and commercial renovations with attention to detail. We transform existing spaces into modern, functional environments.",
                "icon": "fas fa-hard-hat",
                "display_order": 2,
            },
            {
                "name": "Interior Design",
                "category": Service.Category.INTERIOR,
                "description": "Beautiful interior fit-out and design for any space. We create stunning interiors that reflect your style and needs.",
                "icon": "fas fa-paint-roller",
                "display_order": 3,
            },
            {
                "name": "Welding & Fabrication",
                "category": Service.Category.WELDING,
                "description": "Metalwork, gates, railings, and structural steel fabrication. Quality craftsmanship for all your metal needs.",
                "icon": "fas fa-wrench",
                "display_order": 4,
            },
            {
                "name": "Concrete Products",
                "category": Service.Category.CONCRETE,
                "description": "Pre-cast concrete, blocks, slabs, and custom concrete products. Durable and reliable construction materials.",
                "icon": "fas fa-cubes",
                "display_order": 5,
            },
            {
                "name": "Industrial Floor Solutions",
                "category": Service.Category.INDUSTRIAL,
                "description": "Epoxy, polished concrete, and industrial flooring solutions. Durable, safe, and easy to maintain.",
                "icon": "fas fa-layer-group",
                "display_order": 6,
            },
            {
                "name": "Waterproofing Works",
                "category": Service.Category.WATERPROOFING,
                "description": "Roof, basement, and tank waterproofing solutions. Protect your structure from water damage.",
                "icon": "fas fa-water",
                "display_order": 7,
            },
            {
                "name": "Roads & Stormwater Infrastructure",
                "category": Service.Category.INFRASTRUCTURE,
                "description": "Roads, drainage systems, culverts, and stormwater management. Building Kenya's infrastructure.",
                "icon": "fas fa-road",
                "display_order": 8,
            },
            {
                "name": "Construction Chemicals",
                "category": Service.Category.CHEMICALS,
                "description": "Admixtures, sealants, grouts, and chemical solutions for construction. Enhance durability and performance.",
                "icon": "fas fa-flask",
                "display_order": 9,
            },
        ]

        created_count = 0
        updated_count = 0

        for data in services_data:
            slug = slugify(data["name"])
            service, created = Service.objects.get_or_create(
                slug=slug,
                defaults={
                    "name": data["name"],
                    "category": data["category"],
                    "description": data["description"],
                    "icon": data["icon"],
                    "display_order": data["display_order"],
                    "is_active": True,
                },
            )

            if created:
                self.stdout.write(f"  ✅ Created: {service.name} ({service.icon})")
                created_count += 1
            else:
                # Update existing
                service.name = data["name"]
                service.category = data["category"]
                service.description = data["description"]
                service.icon = data["icon"]
                service.display_order = data["display_order"]
                service.is_active = True
                service.save()
                self.stdout.write(f"  🔄 Updated: {service.name} ({service.icon})")
                updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"\n✅ Services seeding complete! Created: {created_count}, Updated: {updated_count}"
            )
        )