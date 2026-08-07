"""
Seed command for Clients - Caldan Construction
Creates sample clients from the company profile.
"""

from django.core.management.base import BaseCommand
from clients.models import Client


class Command(BaseCommand):
    help = "Seed clients data into the database"

    def handle(self, *args, **options):
        self.stdout.write("🌱 Seeding clients...")

        clients_data = [
            {
                "name": "Kennedy Onyancha",
                "type": Client.Type.INDIVIDUAL,
                "company_name": "",
                "email": "kennedy.onyancha@example.com",
                "phone": "0712345678",
                "county": "Nakuru",
                "town": "Nakuru",
                "status": Client.Status.ACTIVE,
                "source": "Referral",
                "notes": "Completed 25-unit apartment project.",
            },
            {
                "name": "Dr. Nyangara Naphtali",
                "type": Client.Type.INDIVIDUAL,
                "company_name": "",
                "email": "nyangara.naphtali@example.com",
                "phone": "0723456789",
                "county": "Nakuru",
                "town": "Nakuru",
                "status": Client.Status.ACTIVE,
                "source": "Referral",
                "notes": "Completed 18-unit apartment project.",
            },
            {
                "name": "James Mwangi",
                "type": Client.Type.INDIVIDUAL,
                "company_name": "",
                "email": "james.mwangi@example.com",
                "phone": "0734567890",
                "county": "Nakuru",
                "town": "Nakuru",
                "status": Client.Status.ACTIVE,
                "source": "Website",
                "notes": "Completed massonnaitte project.",
            },
            {
                "name": "Munanda Secondary School",
                "type": Client.Type.INSTITUTION,
                "company_name": "Munanda Secondary School",
                "email": "info@munanda.sc.ke",
                "phone": "0745678901",
                "county": "Nakuru",
                "town": "Gilgil",
                "status": Client.Status.ACTIVE,
                "source": "Direct",
                "notes": "Completed secondary school construction.",
            },
            {
                "name": "Oyarai Primary School",
                "type": Client.Type.INSTITUTION,
                "company_name": "Oyarai Primary School",
                "email": "info@oyaraiprimary.sc.ke",
                "phone": "0756789012",
                "county": "Nakuru",
                "town": "Nakuru",
                "status": Client.Status.ACTIVE,
                "source": "Direct",
                "notes": "Completed classroom construction.",
            },
            {
                "name": "Koto Housing",
                "type": Client.Type.COMPANY,
                "company_name": "Koto Housing",
                "email": "info@kotohousing.co.ke",
                "phone": "0767890123",
                "county": "Nakuru",
                "town": "Gilgil",
                "status": Client.Status.ACTIVE,
                "source": "Direct",
                "notes": "Gilgil Secondary School project.",
            },
            {
                "name": "Ministry of Education",
                "type": Client.Type.INSTITUTION,
                "company_name": "Ministry of Education",
                "email": "info@education.go.ke",
                "phone": "0778901234",
                "county": "Nairobi",
                "town": "Nairobi",
                "status": Client.Status.ACTIVE,
                "source": "Tender",
                "notes": "Oljorai Secondary School project.",
            },
            {
                "name": "Gilgil Secondary School",
                "type": Client.Type.INSTITUTION,
                "company_name": "Gilgil Secondary School",
                "email": "info@gilgilsecondary.sc.ke",
                "phone": "0789012345",
                "county": "Nakuru",
                "town": "Gilgil",
                "status": Client.Status.ACTIVE,
                "source": "Referral",
                "notes": "Koto Housing project.",
            },
        ]

        created_count = 0
        updated_count = 0

        for data in clients_data:
            client, created = Client.objects.get_or_create(
                email=data["email"],
                defaults={
                    "name": data["name"],
                    "type": data["type"],
                    "company_name": data["company_name"],
                    "phone": data["phone"],
                    "county": data["county"],
                    "town": data["town"],
                    "status": data["status"],
                    "source": data["source"],
                    "notes": data["notes"],
                },
            )

            if created:
                self.stdout.write(f"  ✅ Created: {client.name} (status={client.status})")
                created_count += 1
            else:
                # Update existing
                client.name = data["name"]
                client.type = data["type"]
                client.company_name = data["company_name"]
                client.phone = data["phone"]
                client.county = data["county"]
                client.town = data["town"]
                client.status = data["status"]
                client.source = data["source"]
                client.notes = data["notes"]
                client.save()
                self.stdout.write(f"  🔄 Updated: {client.name} (status={client.status})")
                updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"\n✅ Clients seeding complete! Created: {created_count}, Updated: {updated_count}"
            )
        )