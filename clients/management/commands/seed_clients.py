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
            {
                "name": "Lakeside Heights Developers",
                "type": Client.Type.COMPANY,
                "company_name": "Lakeside Heights Developers Ltd",
                "email": "projects@lakesideheights.co.ke",
                "phone": "0790123456",
                "county": "Nakuru",
                "town": "Naivasha",
                "status": Client.Status.ACTIVE,
                "source": "Website",
                "notes": "Residential development partner — 4 active sites.",
            },
            {
                "name": "St. Mary's Academy",
                "type": Client.Type.INSTITUTION,
                "company_name": "St. Mary's Academy",
                "email": "admin@stmarysacademy.sc.ke",
                "phone": "0701234567",
                "county": "Nairobi",
                "town": "Westlands",
                "status": Client.Status.ACTIVE,
                "source": "Referral",
                "notes": "Perimeter wall and classroom block extension.",
            },
            {
                "name": "Ann Wambui",
                "type": Client.Type.INDIVIDUAL,
                "company_name": "",
                "email": "ann.wambui@example.com",
                "phone": "0711223344",
                "county": "Kiambu",
                "town": "Thika",
                "status": Client.Status.LEAD,
                "source": "Referral",
                "notes": "Lead — interested in residential interior fit-out.",
            },
            {
                "name": "Riverside Logistics",
                "type": Client.Type.COMPANY,
                "company_name": "Riverside Logistics Ltd",
                "email": "facilities@riversidelogistics.co.ke",
                "phone": "0733445566",
                "county": "Nakuru",
                "town": "Nakuru",
                "status": Client.Status.ACTIVE,
                "source": "Direct",
                "notes": "Warehouse floor resurfacing and roof waterproofing.",
            },
            {
                "name": "Peter Kamau",
                "type": Client.Type.INDIVIDUAL,
                "company_name": "",
                "email": "peter.kamau@example.com",
                "phone": "0788990011",
                "county": "Nakuru",
                "town": "Nakuru",
                "status": Client.Status.CONVERTED,
                "source": "Website",
                "notes": "Converted lead — completed kitchen renovation.",
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