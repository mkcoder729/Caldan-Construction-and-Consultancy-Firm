"""
Seed command for Team Members - Caldan Construction
Creates team members from the company profile.
"""

from django.core.management.base import BaseCommand
from team.models import TeamMember


class Command(BaseCommand):
    help = "Seed team members data into the database"

    def handle(self, *args, **options):
        self.stdout.write("🌱 Seeding team members...")

        team_data = [
            {
                "name": "Dr. Daniel O. Siringi",
                "role": TeamMember.Role.DIRECTOR,
                "title": "Director, Building Construction",
                "bio": "Dr. Daniel O. Siringi has over 30 years of experience in the construction industry. He leads the company with a focus on quality, integrity, and client satisfaction.",
                "display_order": 1,
                "is_featured": True,
            },
            {
                "name": "Mrs. Callen K. Manoti",
                "role": TeamMember.Role.ADMIN,
                "title": "Director, Project Administration",
                "bio": "Mrs. Callen K. Manoti oversees project administration and ensures smooth operations across all projects.",
                "display_order": 2,
                "is_featured": True,
            },
            {
                "name": "Lawrence Njoroge",
                "role": TeamMember.Role.MANAGER,
                "title": "Managing Director",
                "bio": "Lawrence Njoroge leads the management team with a dynamic and motivated approach to construction management.",
                "display_order": 3,
                "is_featured": False,
            },
            {
                "name": "Gerishon Ngugi",
                "role": TeamMember.Role.ENGINEER,
                "title": "Civil Engineer",
                "bio": "Gerishon Ngugi is a dedicated civil engineer with expertise in structural design and project execution.",
                "display_order": 4,
                "is_featured": False,
            },
            {
                "name": "James Ngugi",
                "role": TeamMember.Role.ENGINEER,
                "title": "Civil Engineer",
                "bio": "James Ngugi brings extensive experience in civil engineering and construction project management.",
                "display_order": 5,
                "is_featured": False,
            },
        ]

        created_count = 0
        updated_count = 0

        for data in team_data:
            member, created = TeamMember.objects.get_or_create(
                name=data["name"],
                defaults={
                    "role": data["role"],
                    "title": data["title"],
                    "bio": data["bio"],
                    "display_order": data["display_order"],
                    "is_featured": data["is_featured"],
                    "is_active": True,
                },
            )

            if created:
                self.stdout.write(f"  ✅ Created: {member.name}")
                created_count += 1
            else:
                member.role = data["role"]
                member.title = data["title"]
                member.bio = data["bio"]
                member.display_order = data["display_order"]
                member.is_featured = data["is_featured"]
                member.is_active = True
                member.save()
                self.stdout.write(f"  🔄 Updated: {member.name}")
                updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"\n✅ Team seeding complete! Created: {created_count}, Updated: {updated_count}"
            )
        )