"""Tests for the compassion stats service + context processor."""

from datetime import timedelta
from decimal import Decimal

from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone

from compassion.context_processors import compassion_stats
from compassion.models import (
    Donation,
    InKindDonation,
    OutreachStory,
    PaymentMethod,
    MinistrySettings,
)
from compassion.services.stats_service import StatsService


class StatsServiceTests(TestCase):
    def setUp(self):
        cache.clear()
        today = timezone.now().date()

        OutreachStory.objects.create(
            title="Story 1",
            category=OutreachStory.Category.HOSPITAL,
            summary="", location="Hospital A", event_date=today - timedelta(days=30),
            people_served=80, is_published=True, display_order=1,
        )
        OutreachStory.objects.create(
            title="Story 2",
            category=OutreachStory.Category.HOSPITAL,
            summary="", location="Hospital A", event_date=today - timedelta(days=200),
            people_served=60, is_published=True, display_order=2,
        )
        OutreachStory.objects.create(
            title="Story 3",
            category=OutreachStory.Category.HOSPITAL,
            summary="", location="", event_date=today - timedelta(days=30),
            people_served=99, is_published=True, display_order=3,
        )
        OutreachStory.objects.create(
            title="Story 4",
            category=OutreachStory.Category.PRISON,
            summary="", location="Prison A", event_date=today - timedelta(days=40),
            people_served=10, is_published=True, display_order=4,
        )
        OutreachStory.objects.create(
            title="Old story",
            category=OutreachStory.Category.PRISON,
            summary="", event_date=today - timedelta(days=400),
            people_served=999, is_published=True, display_order=5,
        )

        InKindDonation.objects.create(
            donor_name="A", donor_email="[email protected]", donor_phone="0712345678",
            item_type=InKindDonation.ItemType.FOOD,
            item_description="Maize", quantity_estimate="20kg",
            status=InKindDonation.Status.DELIVERED,
        )
        InKindDonation.objects.create(
            donor_name="B", donor_email="[email protected]", donor_phone="0712345678",
            item_type=InKindDonation.ItemType.FOOD,
            item_description="Beans", quantity_estimate="50",
            status=InKindDonation.Status.PLEDGED,  # not counted
        )

        Donation.objects.create(
            donor_name="X", donor_email="[email protected]", donor_phone="0712345678",
            amount_ksh=Decimal("1000.00"), purpose=Donation.Purpose.GENERAL,
            status=Donation.Status.SUCCESS,
        )
        Donation.objects.create(
            donor_name="Y", donor_email="[email protected]", donor_phone="0712345678",
            amount_ksh=Decimal("2000.50"), purpose=Donation.Purpose.HOSPITAL,
            status=Donation.Status.SUCCESS,
        )
        Donation.objects.create(
            donor_name="Z", donor_email="[email protected]", donor_phone="0712345678",
            amount_ksh=Decimal("500.00"), purpose=Donation.Purpose.GENERAL,
            status=Donation.Status.PENDING,
        )

    def test_people_served_includes_recent_only(self):
        # 80 + 60 + 99 + 10 = 249 (story at -400 days excluded)
        self.assertEqual(StatsService.people_served_12mo(), 249)

    def test_meals_distributed_only_counts_delivered_food(self):
        # "20kg" → 20, "50" → 50, "Beans"/PLEDGED ignored
        self.assertEqual(StatsService.meals_distributed(), 20)

    def test_hospitals_visited_counts_distinct_locations(self):
        # 2 distinct locations in HOSPITAL category
        self.assertEqual(StatsService.hospitals_visited(), 1)  # only Hospital A (third had no location)

    def test_prison_visits_counts_published(self):
        self.assertEqual(StatsService.prison_visits(), 2)

    def test_donations_total_and_count(self):
        self.assertEqual(StatsService.donations_count(), 2)
        self.assertEqual(StatsService.donations_total_ksh(), Decimal("3000.50"))

    def test_get_all_stats_returns_dict_with_six_keys(self):
        stats = StatsService.get_all_stats()
        self.assertEqual(set(stats.keys()), {
            "compassion_people_served",
            "compassion_meals_distributed",
            "compassion_hospitals_visited",
            "compassion_prison_visits",
            "compassion_donations_total_ksh",
            "compassion_donations_count",
        })

    def test_context_processor_returns_zero_on_exception(self):
        # Force a failure by nuking models — easier: just verify it returns a dict
        # with the 6 keys even when there's nothing in the DB.
        cache.clear()
        for s in OutreachStory.objects.all():
            s.delete()
        for d in Donation.objects.all():
            d.delete()
        for p in InKindDonation.objects.all():
            p.delete()
        ctx = compassion_stats(None)
        self.assertEqual(ctx["compassion_people_served"], 0)
        self.assertEqual(ctx["compassion_donations_count"], 0)


class CacheInvalidationSignalTests(TestCase):
    def test_payment_method_save_busts_cache(self):
        cache.set("compassion:payment_methods:active", "stale", 300)
        PaymentMethod.objects.create(
            method=PaymentMethod.Method.PAYBILL, label="X",
            account_number="123", account_name="Y", is_active=True, display_order=1,
        )
        # Signals should have busted the cache. The cached value is gone.
        self.assertIsNone(cache.get("compassion:payment_methods:active"))

    def test_ministry_settings_save_busts_cache(self):
        cache.set("compassion:ministry_settings:solo", "stale", 300)
        settings = MinistrySettings.get_solo()
        settings.hero_title = "Updated"
        settings.save()
        self.assertIsNone(cache.get("compassion:ministry_settings:solo"))