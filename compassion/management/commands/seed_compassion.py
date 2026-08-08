"""
Idempotent seed for Caldan Compassionate Ministry.

Run with: `python manage.py seed_compassion`

Creates / refreshes:
  - 1 MinistrySettings row (singleton)
  - 6 OutreachStories (2 HOSPITAL, 2 PRISON, 2 NEIGHBOURHOOD)
  - 4 InKindDonations spanning the status workflow
  - 2 ScheduleCalls (1 NEW, 1 CONTACTED)
  - 4 Donations (1 PENDING, 3 SUCCESS)
  - 3 PaymentMethods (PAYBILL, BUY_GOODS, BANK)

Safe to re-run: every entity uses get_or_create on a stable key.
"""

from datetime import date, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from compassion.models import (
    Donation,
    InKindDonation,
    ScheduleCall,
    OutreachStory,
    PaymentMethod,
    MinistrySettings,
)


class Command(BaseCommand):
    help = "Seed Caldan Compassionate Ministry with sample data (idempotent)."

    def handle(self, *args, **options):
        self._seed_settings()
        self._seed_stories()
        self._seed_inkind()
        self._seed_calls()
        self._seed_donations()
        self._seed_payment_methods()
        self.stdout.write(self.style.SUCCESS("Compassion seed complete."))

    # ───── Helpers ─────

    def _seed_settings(self):
        obj, created = MinistrySettings.objects.get_or_create(
            pk=1,
            defaults={
                "hero_title": "Every gift lands somewhere it matters.",
                "hero_subtitle": (
                    "Hospital bedsides. Prison visits. Neighbours in need. "
                    "Choose how you'd like to give — money, items, or a conversation."
                ),
                "hero_cta_label": "Donate Now",
                "mission_statement": (
                    "Caldan Compassionate Ministry reaches beyond construction — "
                    "into hospitals, prisons, and neighbourhoods — with practical "
                    "care that meets real, immediate needs. Every shilling, every "
                    "item, every hour of time lands somewhere it matters."
                ),
                "contact_phone": "+254 700 000 000",
                "contact_email": "info.caldanconstruction@gmail.com",
                "default_currency": "KES",
            },
        )
        self.stdout.write(
            f"  • MinistrySettings: {'created' if created else 'kept'} ({obj.hero_title!r})"
        )

    def _seed_stories(self):
        stories = [
            {
                "title": "Kenyatta National Hospital — Paediatric Ward",
                "category": OutreachStory.Category.HOSPITAL,
                "summary": "Distributed blankets, snacks, and reading materials to 47 children during a long Sunday afternoon.",
                "location": "Kenyatta National Hospital, Nairobi",
                "people_served": 47,
                "display_order": 10,
                "days_ago": 12,
            },
            {
                "title": "Mama Lucy Kibaki Hospital — Maternity Support",
                "category": OutreachStory.Category.HOSPITAL,
                "summary": "Delivered 30 new-baby kits and stayed with mothers waiting on overnight results.",
                "location": "Mama Lucy Kibaki Hospital, Nairobi",
                "people_served": 30,
                "display_order": 20,
                "days_ago": 65,
            },
            {
                "title": "Lang'ata Women's Prison — Hygiene Drive",
                "category": OutreachStory.Category.PRISON,
                "summary": "Brought sanitary supplies, soap, and a 90-minute conversation with 22 inmates.",
                "location": "Lang'ata Women's Prison",
                "people_served": 22,
                "display_order": 30,
                "days_ago": 25,
            },
            {
                "title": "Naivasha Maximum — Reading Library",
                "category": OutreachStory.Category.PRISON,
                "summary": "Set up a small lending library with 60 donated books across two blocks.",
                "location": "Naivasha Maximum Security Prison",
                "people_served": 60,
                "display_order": 40,
                "days_ago": 110,
            },
            {
                "title": "Kibera Neighbours — School Kits",
                "category": OutreachStory.Category.NEIGHBOURHOOD,
                "summary": "Gave 85 children a full kit — backpack, books, pencils, and a packed lunch.",
                "location": "Kibera, Nairobi",
                "people_served": 85,
                "display_order": 50,
                "days_ago": 45,
            },
            {
                "title": "Mukuru Kwa Njenga — Family Pantry",
                "category": OutreachStory.Category.NEIGHBOURHOOD,
                "summary": "Stood up a Saturday family pantry serving 120 households with maize flour and cooking oil.",
                "location": "Mukuru Kwa Njenga",
                "people_served": 120,
                "display_order": 60,
                "days_ago": 95,
            },
        ]
        for s in stories:
            obj, created = OutreachStory.objects.get_or_create(
                title=s["title"],
                defaults={
                    "category": s["category"],
                    "summary": s["summary"],
                    "location": s["location"],
                    "people_served": s["people_served"],
                    "display_order": s["display_order"],
                    "event_date": date.today() - timedelta(days=s["days_ago"]),
                    "is_published": True,
                },
            )
            self.stdout.write(
                f"  • Story: {'created' if created else 'kept'} — {obj.title}"
            )

    def _seed_inkind(self):
        pledges = [
            {
                "donor_name": "Mary Wanjiku",
                "donor_email": "[email protected]",
                "donor_phone": "0712345678",
                "item_type": InKindDonation.ItemType.FOOD,
                "item_description": "Maize flour, 20kg bags",
                "quantity_estimate": "5 bags",
                "delivery_mode": InKindDonation.DeliveryMode.DROPOFF,
                "status": InKindDonation.Status.DELIVERED,
                "address": "Westlands, Nairobi",
                "notes": "Delivered to Kibera pantry last Saturday.",
                "days_ago": 9,
            },
            {
                "donor_name": "James Otieno",
                "donor_email": "[email protected]",
                "donor_phone": "0112345678",
                "item_type": InKindDonation.ItemType.CLOTHING,
                "item_description": "Children's winter clothes",
                "quantity_estimate": "30 items",
                "delivery_mode": InKindDonation.DeliveryMode.PICKUP,
                "status": InKindDonation.Status.RECEIVED,
                "address": "Karen, Nairobi",
                "days_ago": 18,
            },
            {
                "donor_name": "Faith Achieng",
                "donor_email": "[email protected]",
                "donor_phone": "+254712345678",
                "item_type": InKindDonation.ItemType.MEDICAL,
                "item_description": "Bandages, antiseptic, gloves",
                "quantity_estimate": "15 boxes",
                "delivery_mode": InKindDonation.DeliveryMode.ARRANGE,
                "preferred_date": date.today() + timedelta(days=4),
                "status": InKindDonation.Status.SCHEDULED,
                "address": "Kileleshwa, Nairobi",
                "days_ago": 3,
            },
            {
                "donor_name": "Peter Kamau",
                "donor_email": "[email protected]",
                "donor_phone": "0719876543",
                "item_type": InKindDonation.ItemType.FOOD,
                "item_description": "Cooking oil and rice",
                "quantity_estimate": "50kg rice, 10L oil",
                "delivery_mode": InKindDonation.DeliveryMode.ARRANGE,
                "status": InKindDonation.Status.PLEDGED,
                "days_ago": 1,
            },
        ]
        for p in pledges:
            obj, created = InKindDonation.objects.get_or_create(
                donor_email=p["donor_email"],
                item_description=p["item_description"],
                defaults={
                    "donor_name": p["donor_name"],
                    "donor_phone": p["donor_phone"],
                    "item_type": p["item_type"],
                    "quantity_estimate": p["quantity_estimate"],
                    "delivery_mode": p["delivery_mode"],
                    "preferred_date": p.get("preferred_date"),
                    "address": p.get("address", ""),
                    "notes": p.get("notes", ""),
                    "status": p["status"],
                    "status_changed_at": timezone.now() - timedelta(days=p["days_ago"]),
                },
            )
            self.stdout.write(
                f"  • In-kind pledge: {'created' if created else 'kept'} — {obj.donor_name} ({obj.status})"
            )

    def _seed_calls(self):
        calls = [
            {
                "name": "Susan Mutiso",
                "email": "[email protected]",
                "phone": "0723456789",
                "topic": ScheduleCall.Topic.LARGE_DONATION,
                "preferred_time": "Weekday mornings",
                "message": "Wants to discuss a KES 250,000 gift split across hospital and prison outreach.",
                "status": ScheduleCall.Status.NEW,
                "days_ago": 2,
            },
            {
                "name": "David Mwangi",
                "email": "[email protected]",
                "phone": "0734567890",
                "topic": ScheduleCall.Topic.PARTNERSHIP,
                "preferred_time": "Saturday afternoon",
                "message": "Corporate partnership inquiry — possible quarterly matching program.",
                "status": ScheduleCall.Status.CONTACTED,
                "days_ago": 5,
            },
        ]
        for c in calls:
            obj, created = ScheduleCall.objects.get_or_create(
                email=c["email"],
                topic=c["topic"],
                defaults={
                    "name": c["name"],
                    "phone": c["phone"],
                    "preferred_time": c["preferred_time"],
                    "message": c["message"],
                    "status": c["status"],
                    "status_changed_at": timezone.now() - timedelta(days=c["days_ago"]),
                },
            )
            self.stdout.write(
                f"  • Schedule call: {'created' if created else 'kept'} — {obj.name} ({obj.status})"
            )

    def _seed_donations(self):
        donations = [
            {
                "donor_name": "Anonymous",
                "donor_email": "[email protected]",
                "donor_phone": "0700000001",
                "amount_ksh": Decimal("500.00"),
                "purpose": Donation.Purpose.GENERAL,
                "status": Donation.Status.SUCCESS,
                "paystack_reference": "DON-PSP-1001",
                "days_ago": 4,
            },
            {
                "donor_name": "Lucy Njeri",
                "donor_email": "[email protected]",
                "donor_phone": "0711223344",
                "amount_ksh": Decimal("2500.00"),
                "purpose": Donation.Purpose.HOSPITAL,
                "status": Donation.Status.SUCCESS,
                "paystack_reference": "DON-PSP-1002",
                "days_ago": 14,
            },
            {
                "donor_name": "Brian Otieno",
                "donor_email": "[email protected]",
                "donor_phone": "0722334455",
                "amount_ksh": Decimal("10000.00"),
                "purpose": Donation.Purpose.PRISON,
                "status": Donation.Status.SUCCESS,
                "paystack_reference": "DON-PSP-1003",
                "days_ago": 22,
            },
            {
                "donor_name": "Anonymous",
                "donor_email": "[email protected]",
                "donor_phone": "0733445566",
                "amount_ksh": Decimal("1500.00"),
                "purpose": Donation.Purpose.NEIGHBOURHOOD,
                "status": Donation.Status.PENDING,
                "paystack_reference": "",
                "days_ago": 1,
            },
        ]
        for d in donations:
            obj, created = Donation.objects.get_or_create(
                donor_email=d["donor_email"],
                amount_ksh=d["amount_ksh"],
                purpose=d["purpose"],
                defaults={
                    "donor_name": d["donor_name"],
                    "donor_phone": d["donor_phone"],
                    "status": d["status"],
                    "paystack_reference": d["paystack_reference"],
                    "verified_at": timezone.now() - timedelta(days=d["days_ago"]) if d["status"] == Donation.Status.SUCCESS else None,
                },
            )
            self.stdout.write(
                f"  • Donation: {'created' if created else 'kept'} — {obj.donor_name} KES {obj.amount_ksh} ({obj.status})"
            )

    def _seed_payment_methods(self):
        methods = [
            {
                "method": PaymentMethod.Method.PAYBILL,
                "label": "M-Pesa Paybill — Donations",
                "account_number": "247247",
                "account_name": "Caldan Compassionate Ministry",
                "instructions": (
                    "Paybill: 247247\n"
                    "Account number: COMPASSION\n"
                    "You'll receive an M-Pesa confirmation SMS instantly."
                ),
                "display_order": 10,
            },
            {
                "method": PaymentMethod.Method.BUY_GOODS,
                "label": "Buy Goods & Services Till",
                "account_number": "6543210",
                "account_name": "Caldan Compassionate Ministry",
                "instructions": (
                    "Till: 6543210\n"
                    "Use at any M-Pesa agent or via STK push."
                ),
                "display_order": 20,
            },
            {
                "method": PaymentMethod.Method.BANK,
                "label": "Equity Bank — Compassion Account",
                "account_number": "0123456789012",
                "account_name": "Caldan Compassionate Ministry",
                "bank_name": "Equity Bank",
                "instructions": (
                    "Bank: Equity Bank\n"
                    "Account: 0123456789012\n"
                    "Branch: Westlands\n"
                    "SWIFT: EQBLKENA\n"
                    "Please email [email protected] after transferring so we can acknowledge."
                ),
                "display_order": 30,
            },
        ]
        for m in methods:
            obj, created = PaymentMethod.objects.get_or_create(
                method=m["method"],
                account_number=m["account_number"],
                defaults={
                    "label": m["label"],
                    "account_name": m["account_name"],
                    "bank_name": m.get("bank_name", ""),
                    "instructions": m["instructions"],
                    "display_order": m["display_order"],
                    "is_active": True,
                },
            )
            self.stdout.write(
                f"  • Payment method: {'created' if created else 'kept'} — {obj.label}"
            )