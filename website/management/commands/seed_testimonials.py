"""
Seed command for Testimonials - Caldan Construction
Creates client testimonials.
"""

from django.core.management.base import BaseCommand
from website.models import Testimonial


class Command(BaseCommand):
    help = "Seed testimonials data into the database"

    def handle(self, *args, **options):
        self.stdout.write("🌱 Seeding testimonials...")

        testimonials_data = [
            {
                "author_name": "Kennedy Onyancha",
                "author_title": "Property Developer, Nakuru",
                "content": "Caldan Construction delivered our 25-unit apartment project on time and within budget. Their professionalism and attention to detail was exceptional.",
                "rating": 5,
                "display_order": 1,
                "is_active": True,
            },
            {
                "author_name": "Dr. Nyangara Naphtali",
                "author_title": "Client, Nakuru",
                "content": "The team at Caldan Construction completed our 18-unit apartment project to the highest standards. I highly recommend them for any construction project.",
                "rating": 5,
                "display_order": 2,
                "is_active": True,
            },
            {
                "author_name": "James Mwangi",
                "author_title": "Homeowner, Nakuru",
                "content": "Caldan Construction transformed our space with their exceptional work on our massonnaitte project. Professional, reliable, and quality workmanship.",
                "rating": 5,
                "display_order": 3,
                "is_active": True,
            },
            {
                "author_name": "Munanda Secondary School",
                "author_title": "School Administration",
                "content": "Caldan Construction built our modern secondary school facility to exact specifications. The project was completed on time and within budget.",
                "rating": 5,
                "display_order": 4,
                "is_active": True,
            },
            {
                "author_name": "Oyarai Primary School",
                "author_title": "School Administration",
                "content": "We are grateful for Caldan Construction's work on our school buildings. They delivered quality classrooms that have transformed our learning environment.",
                "rating": 5,
                "display_order": 5,
                "is_active": True,
            },
        ]

        created_count = 0
        updated_count = 0

        for data in testimonials_data:
            testimonial, created = Testimonial.objects.get_or_create(
                author_name=data["author_name"],
                defaults={
                    "author_title": data["author_title"],
                    "content": data["content"],
                    "rating": data["rating"],
                    "display_order": data["display_order"],
                    "is_active": data["is_active"],
                },
            )

            if created:
                self.stdout.write(f"  ✅ Created: {testimonial.author_name}")
                created_count += 1
            else:
                testimonial.author_title = data["author_title"]
                testimonial.content = data["content"]
                testimonial.rating = data["rating"]
                testimonial.display_order = data["display_order"]
                testimonial.is_active = data["is_active"]
                testimonial.save()
                self.stdout.write(f"  🔄 Updated: {testimonial.author_name}")
                updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"\n✅ Testimonials seeding complete! Created: {created_count}, Updated: {updated_count}"
            )
        )