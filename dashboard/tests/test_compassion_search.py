"""Tests for the dashboard global search service — including the
compassion pipeline (donations, in-kind pledges, schedule calls,
outreach stories, payment methods).

The search service powers the dashboard topbar's command-palette
modal. It's admin-only (`@login_required`), but the search logic
itself is exercised at the service level here.
"""

from datetime import date
from decimal import Decimal

from django.test import TestCase

from compassion.models import (
    Donation, InKindDonation, ScheduleCall, OutreachStory, PaymentMethod,
)
from dashboard.services.global_search_service import (
    search_everything, search_models,
)


class DashboardCompassionSearchTests(TestCase):
    """Compassion content surfaces in the dashboard search."""

    def setUp(self) -> None:
        self.story = OutreachStory.objects.create(
            title="Bedside visits at Kenyatta",
            slug="bedside-kenyatta",
            category=OutreachStory.Category.HOSPITAL,
            summary="Comfort and prayer for patients waiting for treatment.",
            body="We sat with six patients at Kenyatta National Hospital.",
            location="Kenyatta National Hospital, Nairobi",
            event_date=date(2026, 4, 12),
            people_served=6,
            is_published=True,
        )
        self.donation = Donation.objects.create(
            reference="DON-TEST-001",
            donor_name="Mary Wanjiku",
            donor_email="mary@example.com",
            donor_phone="0712345678",
            amount_ksh=Decimal("2500"),
            purpose=Donation.Purpose.HOSPITAL,
            status=Donation.Status.PENDING,
        )
        self.pledge = InKindDonation.objects.create(
            donor_name="John Mwangi",
            donor_email="john@example.com",
            donor_phone="0723456789",
            item_type="Food",
            item_description="Bags of maize flour for the kitchen",
            quantity_estimate="50kg",
            delivery_mode=InKindDonation.DeliveryMode.PICKUP,
            address="Karen, Nairobi",
            status=InKindDonation.Status.PLEDGED,
        )
        self.call = ScheduleCall.objects.create(
            name="Pastor Samuel",
            email="samuel@example.com",
            phone="0734567890",
            topic="Partnership",
            preferred_time="Tomorrow afternoon",
            message="Want to discuss a larger gift",
            status=ScheduleCall.Status.NEW,
        )
        self.paybill = PaymentMethod.objects.create(
            method=PaymentMethod.Method.PAYBILL,
            label="M-Pesa Paybill — Donations",
            account_number="247247",
            account_name="CALDAN Compassion Ministry",
            instructions="Paybill 247247 → Account: CALDAN",
            display_order=0,
            is_active=True,
        )

    # ───── Pages (Compassion admin links) ─────

    def test_compassion_pages_listed(self) -> None:
        result = search_everything("donations")
        cats = {c["category"]: c for c in result["categories"]}
        # "Pages" is the category the static page catalog falls under.
        self.assertIn("Pages", cats)
        page_titles = {item["title"] for item in cats["Pages"]["items"]}
        # At least one of the compassion admin links appears for "donations".
        self.assertIn("Donations", page_titles)

    def test_compassion_admin_links_all_resolve(self) -> None:
        """Every compassion admin link in STATIC_PAGES reverses to a
        real /dashboard/compassion/... URL."""
        for q in ("donations", "inkind", "calls", "stories", "payment", "ministry", "compassion"):
            result = search_everything(q)
            for cat in result["categories"]:
                if cat["category"] != "Pages":
                    continue
                for item in cat["items"]:
                    if item["title"] in (
                        "Compassion Dashboard", "Donations",
                        "In-Kind Pledges", "Schedule Calls",
                        "Outreach Stories", "Payment Methods",
                        "New Outreach Story", "New Payment Method",
                        "Ministry Settings",
                    ):
                        self.assertTrue(
                            item["url"].startswith("/dashboard/compassion/"),
                            msg=f"compassion link should be under /dashboard/, got {item['url']!r}",
                        )

    # ───── Stories ─────

    def test_story_title_match_links_to_admin_edit(self) -> None:
        result = search_everything("Kenyatta")
        all_items = [
            item for cat in result["categories"] for item in cat["items"]
        ]
        story_hits = [i for i in all_items if "Kenyatta" in (i.get("title") or "")]
        self.assertGreater(len(story_hits), 0)
        for hit in story_hits:
            self.assertIn("/dashboard/compassion/stories/", hit["url"])

    def test_story_body_match(self) -> None:
        result = search_everything("comfort")
        all_items = [
            item for cat in result["categories"] for item in cat["items"]
        ]
        self.assertTrue(
            any("Kenyatta" in (i.get("title") or "") for i in all_items),
            msg=f"expected story title to match 'comfort' body query, got {all_items}",
        )

    # ───── Donations ─────

    def test_donation_by_donor_name(self) -> None:
        result = search_everything("Mary")
        cats = {c["category"]: c for c in result["categories"]}
        self.assertIn("Compassion donations", cats)
        titles = {i["title"] for i in cats["Compassion donations"]["items"]}
        self.assertIn("Donation DON-TEST-001", titles)

    def test_donation_by_reference(self) -> None:
        result = search_everything("DON-TEST-001")
        all_items = [
            item for cat in result["categories"] for item in cat["items"]
        ]
        self.assertTrue(any("DON-TEST-001" in (i.get("title") or "") for i in all_items))

    def test_donation_by_purpose(self) -> None:
        result = search_everything("hospital")
        cats = {c["category"]: c for c in result["categories"]}
        self.assertIn("Compassion donations", cats)

    def test_donation_links_to_admin_detail(self) -> None:
        result = search_everything("DON-TEST-001")
        for cat in result["categories"]:
            if cat["category"] == "Compassion donations":
                for item in cat["items"]:
                    if "DON-TEST-001" in item["title"]:
                        self.assertTrue(item["url"].startswith("/dashboard/compassion/donations/"))

    # ───── In-kind pledges ─────

    def test_pledge_by_item_type(self) -> None:
        result = search_everything("food")
        cats = {c["category"]: c for c in result["categories"]}
        self.assertIn("In-kind pledges", cats)
        for item in cats["In-kind pledges"]["items"]:
            self.assertTrue(item["url"].startswith("/dashboard/compassion/inkind/"))

    def test_pledge_by_donor_name(self) -> None:
        result = search_everything("Mwangi")
        cats = {c["category"]: c for c in result["categories"]}
        self.assertIn("In-kind pledges", cats)

    def test_pledge_by_description_word(self) -> None:
        result = search_everything("maize")
        cats = {c["category"]: c for c in result["categories"]}
        self.assertIn("In-kind pledges", cats)

    # ───── Schedule calls ─────

    def test_call_by_topic(self) -> None:
        result = search_everything("partnership")
        cats = {c["category"]: c for c in result["categories"]}
        self.assertIn("Schedule calls", cats)
        for item in cats["Schedule calls"]["items"]:
            self.assertTrue(item["url"].startswith("/dashboard/compassion/calls/"))

    def test_call_by_caller_name(self) -> None:
        result = search_everything("Samuel")
        cats = {c["category"]: c for c in result["categories"]}
        self.assertIn("Schedule calls", cats)

    # ───── Payment methods ─────

    def test_payment_method_by_label(self) -> None:
        result = search_everything("Paybill")
        cats = {c["category"]: c for c in result["categories"]}
        self.assertIn("Payment methods", cats)
        for item in cats["Payment methods"]["items"]:
            # No pk_field on PaymentMethod — link goes to the list page.
            self.assertEqual(item["url"], "/dashboard/compassion/payment-methods/")

    def test_payment_method_by_account_number(self) -> None:
        result = search_everything("247247")
        cats = {c["category"]: c for c in result["categories"]}
        self.assertIn("Payment methods", cats)

    def test_payment_method_by_bank_account_name(self) -> None:
        result = search_everything("CALDAN")
        cats = {c["category"]: c for c in result["categories"]}
        self.assertIn("Payment methods", cats)

    # ───── Order / behavior ─────

    def test_compassion_results_have_admin_urls_only(self) -> None:
        """No result should link to the public /compassion/... site — only
        the admin /dashboard/compassion/... surface. The donor-facing
        site has its own (separate) search bar at the public navbar."""
        for q in ("hospital", "donate", "food", "partnership", "Kenyatta", "Mwangi"):
            result = search_everything(q)
            for cat in result["categories"]:
                for item in cat["items"]:
                    url = item.get("url", "")
                    if url.startswith("/dashboard/compassion/"):
                        # OK
                        continue
                    if "/admin-projects/" in url or "/blog/admin/" in url:
                        # OK — other admin surfaces
                        continue
                    if url.startswith("/dashboard/"):
                        # OK — any other dashboard URL
                        continue
                    if url in ("#",):
                        continue
                    # The dashboard search must never link to the public site.
                    self.assertFalse(
                        url.startswith("/compassion/"),
                        msg=f"dashboard result leaked to public compassion URL: q={q!r} url={url!r}",
                    )
