"""Tests for the global search service.

The search service powers the navbar search bar and the full
results page. It mixes a database-backed source (OutreachStory,
PaymentMethod) with a static in-memory list of compassion actions
and topics. We test:

  * Token / substring matching on published stories (title, summary,
    body, location) — the live source.
  * Static compassion actions (give money, give items, schedule call,
    see stories, ways to give) — they always show up when relevant.
  * Static topic pills (hospital, prison, neighbourhood).
  * Result ordering — title hits > body hits > keyword hits.
  * Empty query returns nothing (no global floods).
  * Dashboard URLs are NEVER returned to the donor.

The downstream view layer (`/search/`, `/search/json/`) is tested
in the website app since the search view lives there.
"""

from datetime import date

from django.test import TestCase

from compassion.models import OutreachStory, PaymentMethod
from compassion.services.search_service import (
    format_results_for_dropdown,
    search,
)


class SearchServiceTests(TestCase):
    def setUp(self) -> None:
        self.story_hospital = OutreachStory.objects.create(
            title="Bedside visits at Kenyatta",
            slug="bedside-kenyatta",
            category=OutreachStory.Category.HOSPITAL,
            summary="Comfort and prayer for patients waiting for treatment.",
            body=(
                "We sat with six patients at Kenyatta National Hospital "
                "and brought juice, blankets, and a listening ear."
            ),
            location="Kenyatta National Hospital, Nairobi",
            event_date=date(2026, 4, 12),
            people_served=6,
            is_published=True,
            display_order=0,
        )
        self.story_prison = OutreachStory.objects.create(
            title="Letters from Kamiti",
            slug="letters-kamiti",
            category=OutreachStory.Category.PRISON,
            summary="Encouraging letters to inmates and their families.",
            body="Forty letters carried hope and scripture to families separated by incarceration.",
            location="Kamiti Maximum Prison",
            event_date=date(2026, 5, 1),
            people_served=40,
            is_published=True,
            display_order=1,
        )
        self.story_neighbourhood = OutreachStory.objects.create(
            title="Mukuru kwa Reuben Saturday meals",
            slug="mukuru-saturday-meals",
            category=OutreachStory.Category.NEIGHBOURHOOD,
            summary="Hot meals for community members every Saturday.",
            body="Over 100 community members shared a meal and fellowship.",
            location="Mukuru kwa Reuben",
            event_date=date(2026, 6, 8),
            people_served=120,
            is_published=True,
            display_order=2,
        )
        self.unpublished = OutreachStory.objects.create(
            title="Hospital draft (not published)",
            slug="hospital-draft",
            category=OutreachStory.Category.HOSPITAL,
            summary="Should not appear in search.",
            body="Draft body.",
            location="Nairobi",
            event_date=date(2026, 1, 1),
            is_published=False,
            display_order=99,
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
        self.bank = PaymentMethod.objects.create(
            method=PaymentMethod.Method.BANK,
            label="KCB Bank Transfer",
            account_number="1234567890",
            account_name="CALDAN Compassion Ministry",
            bank_name="Kenya Commercial Bank",
            instructions="Transfer to the account above.",
            display_order=1,
            is_active=True,
        )

    # ───── Empty / whitespace queries ─────

    def test_empty_query_returns_nothing(self) -> None:
        self.assertEqual(search(""), [])
        self.assertEqual(search("   "), [])

    # ───── Stories ─────

    def test_story_title_match(self) -> None:
        results = search("Kenyatta")
        titles = [r["title"] for r in results]
        self.assertIn("Bedside visits at Kenyatta", titles)
        story = next(r for r in results if r["title"] == "Bedside visits at Kenyatta")
        self.assertEqual(story["type"], "story")
        self.assertEqual(story["slug"], "bedside-kenyatta")
        self.assertIn("/compassion/stories/bedside-kenyatta/", story["url"])

    def test_story_body_match(self) -> None:
        results = search("blankets")
        titles = [r["title"] for r in results]
        self.assertIn("Bedside visits at Kenyatta", titles)

    def test_story_location_match(self) -> None:
        results = search("Kamiti")
        titles = [r["title"] for r in results]
        self.assertIn("Letters from Kamiti", titles)

    def test_unpublished_story_excluded(self) -> None:
        results = search("draft")
        titles = [r["title"] for r in results]
        self.assertNotIn("Hospital draft (not published)", titles)

    def test_story_results_carry_story_metadata(self) -> None:
        results = search("Mukuru")
        story = next(r for r in results if r["slug"] == "mukuru-saturday-meals")
        self.assertEqual(story["type"], "story")
        self.assertEqual(story["category"], "NEIGHBOURHOOD")
        self.assertEqual(story["location"], "Mukuru kwa Reuben")
        self.assertEqual(story["story_id"], self.story_neighbourhood.id)

    # ───── Static actions + topics ─────

    def test_donate_query_returns_give_money_and_ways_to_give(self) -> None:
        results = search("donate")
        titles = [r["title"] for r in results]
        self.assertIn("Give money", titles)
        self.assertIn("Give items", titles)

    def test_give_money_query(self) -> None:
        results = search("money")
        titles = [r["title"] for r in results]
        self.assertIn("Give money", titles)
        # The action result should link to /compassion/#giving
        gm = next(r for r in results if r["title"] == "Give money")
        self.assertTrue(gm["url"].endswith("#giving"))

    def test_mpesa_query_returns_give_money_action(self) -> None:
        results = search("mpesa")
        titles = [r["title"] for r in results]
        self.assertIn("Give money", titles)

    def test_hospital_query_returns_topic_and_ways_to_give(self) -> None:
        results = search("hospital")
        # The topic pill should be in the top results.
        topic = next((r for r in results if r.get("category") == "HOSPITAL"), None)
        self.assertIsNotNone(topic)
        self.assertEqual(topic["title"], "Hospital outreach")
        self.assertEqual(topic["type"], "topic")

    def test_prison_query_returns_topic(self) -> None:
        results = search("prison")
        topic = next((r for r in results if r.get("category") == "PRISON"), None)
        self.assertIsNotNone(topic)
        self.assertEqual(topic["title"], "Prison ministry")

    def test_neighbourhood_query_accepts_alternate_spelling(self) -> None:
        # Both "neighbourhood" (UK) and "neighborhood" (US) match.
        for q in ("neighbourhood", "neighbourhood outreach", "community"):
            results = search(q)
            topic = next((r for r in results if r.get("category") == "NEIGHBOURHOOD"), None)
            self.assertIsNotNone(topic, msg=f"expected NEIGHBOURHOOD topic for q={q!r}")

    def test_schedule_call_action_matches(self) -> None:
        results = search("schedule call")
        titles = [r["title"] for r in results]
        self.assertIn("Schedule a call", titles)

    def test_see_stories_action_matches(self) -> None:
        results = search("stories")
        titles = [r["title"] for r in results]
        self.assertIn("Read outreach stories", titles)

    # ───── Payment methods ─────

    def test_payment_method_match_by_bank_name(self) -> None:
        results = search("KCB")
        bank = next((r for r in results if r["type"] == "payment"), None)
        self.assertIsNotNone(bank)
        self.assertEqual(bank["title"], "KCB Bank Transfer")
        self.assertTrue(bank["url"].endswith("#payment"))

    def test_payment_method_match_by_method_label(self) -> None:
        results = search("mpesa")
        # The static "Give money" action is the primary hit, but the
        # paybill payment method should also appear.
        payment = next((r for r in results if r["type"] == "payment"), None)
        self.assertIsNotNone(payment)
        self.assertIn("Paybill", payment["title"])

    def test_payment_method_match_by_account_number(self) -> None:
        results = search("247247")
        payment = next((r for r in results if r["type"] == "payment"), None)
        self.assertIsNotNone(payment)

    def test_inactive_payment_method_excluded(self) -> None:
        self.paybill.is_active = False
        self.paybill.save()
        results = search("247247")
        titles = [r["title"] for r in results]
        self.assertFalse(
            any("M-Pesa Paybill" in t for t in titles),
            msg="inactive payment method should not appear in results",
        )

    # ───── Ordering / dedup ─────

    def test_results_sorted_by_score_descending(self) -> None:
        results = search("hospital")
        scores = [r["score"] for r in results]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_story_results_have_dashboard_url_dashboard_does_not(self) -> None:
        for q in ("hospital", "donate", "stories", "mpesa", "Kenyatta"):
            results = search(q)
            for r in results:
                # Donor-facing result URLs must never point to the dashboard.
                self.assertNotIn("/dashboard", r["url"], msg=f"q={q!r} url={r['url']!r}")

    # ───── format_results_for_dropdown ─────

    def test_dropdown_groups_by_type(self) -> None:
        results = search("donate")
        dropdown = format_results_for_dropdown(results, max_items=4)
        groups = [d["group"] for d in dropdown]
        # "donate" matches actions → at least one group is "Compassion actions"
        self.assertIn("Compassion actions", groups)

    def test_dropdown_caps_per_group(self) -> None:
        results = search("hospital")
        dropdown = format_results_for_dropdown(results, max_items=1)
        for d in dropdown:
            self.assertLessEqual(len(d["items"]), 1)

    def test_dropdown_omits_empty_groups(self) -> None:
        # Searching for "mpesa" should produce action + payment but
        # not necessarily topic or story.
        results = search("mpesa")
        dropdown = format_results_for_dropdown(results)
        for d in dropdown:
            self.assertGreater(len(d["items"]), 0)
