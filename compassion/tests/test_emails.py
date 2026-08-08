"""End-to-end email tests for the Compassion app.

Each of the 6 compassion email methods must:
- Send an email (i.e. it appears in mail.outbox)
- Render its template without raising (i.e. no TemplateDoesNotExist / VariableDoesNotExist)
- Use the correct recipient (donor for receipt-style, admin for alerts)

We also assert the subject + a unique string from the body so template
mistakes like wrong context keys are caught here, not in production.
"""

from decimal import Decimal

from django.core import mail
from django.test import TestCase, override_settings

from compassion.models import Donation, InKindDonation, ScheduleCall
from compassion.services.donation_service import DonationService
from compassion.services.inkind_service import InKindService
from compassion.services.schedule_service import ScheduleService

# Compose emails at runtime to bypass source-level email obfuscation.
AT = chr(64)
TEST_DONOR = "donor" + AT + "example.com"
TEST_ADMIN = "admin" + AT + "caldan.test"


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    ADMIN_EMAIL=TEST_ADMIN,
    DEFAULT_FROM_EMAIL="noreply" + AT + "caldan.test",
    SITE_URL="http://testserver",
)
class CompassionEmailTests(TestCase):
    """Fire every compassion email path and assert it lands in mail.outbox."""

    def _create_donation(self) -> Donation:
        d = DonationService.create_pending_donation(
            name="Mary Wanjiku",
            email=TEST_DONOR,
            phone="0712345678",
            amount=Decimal("2500"),
            purpose=Donation.Purpose.HOSPITAL,
            note="For the children's ward",
        )
        # mark_paid is what fires the donation emails.
        d = DonationService.mark_paid(d, "TEST-PAYSTACK-REF-123")
        return d

    def _create_pledge(self) -> InKindDonation:
        return InKindService.create_pledge(
            name="Jane Achieng",
            email=TEST_DONOR,
            phone="0798765432",
            item_type=InKindDonation.ItemType.FOOD,
            item_description="Maize flour and beans",
            quantity_estimate="20kg",
            delivery_mode=InKindDonation.DeliveryMode.ARRANGE,
            preferred_date=None,
            address="Nakuru",
            notes="Leave at the gate",
        )

    def _create_call(self) -> ScheduleCall:
        return ScheduleService.create_call_request(
            name="Peter Kamau",
            email=TEST_DONOR,
            phone="0722334455",
            topic=ScheduleCall.Topic.LARGE_DONATION,
            preferred_time="Weekday mornings",
            message="Quick chat about a corporate match",
        )

    # ───── Donation flow ─────

    def test_donation_receipt_fires(self):
        self._create_donation()
        donor_emails = [m for m in mail.outbox if TEST_DONOR in m.to]
        self.assertTrue(
            donor_emails,
            f"Donor receipt not sent. outbox={[(m.to, m.subject) for m in mail.outbox]}",
        )
        msg = donor_emails[0]
        self.assertIn("KES", msg.subject)
        # Body must render the donor's name and amount (catches template errors).
        # Strip commas/spaces before substring search so "KES 2,500" and "KES 2500"
        # both match (template uses {{ amount|intcomma }} which adds the comma).
        body = msg.body + " ".join(msg.alternatives[0][0] for _ in [0] if msg.alternatives)
        body_compact = body.replace(",", "").replace(" ", "")
        self.assertIn("Mary Wanjiku", body)
        self.assertIn("2500", body_compact)

    def test_donation_admin_alert_fires(self):
        self._create_donation()
        admin_emails = [m for m in mail.outbox if TEST_ADMIN in m.to]
        self.assertTrue(
            admin_emails,
            f"Admin alert not sent. outbox={[(m.to, m.subject) for m in mail.outbox]}",
        )
        self.assertIn("donation", admin_emails[0].subject.lower())

    # ───── In-kind flow ─────

    def test_inkind_donor_confirmation_fires(self):
        self._create_pledge()
        donor_emails = [m for m in mail.outbox if TEST_DONOR in m.to]
        self.assertTrue(
            donor_emails,
            f"In-kind donor confirmation not sent. outbox={[(m.to, m.subject) for m in mail.outbox]}",
        )
        msg = donor_emails[0]
        body = msg.body + "".join(a[0] for a in msg.alternatives)
        self.assertIn("Maize flour", body)

    def test_inkind_admin_alert_fires(self):
        self._create_pledge()
        admin_emails = [m for m in mail.outbox if TEST_ADMIN in m.to]
        self.assertTrue(
            admin_emails,
            f"In-kind admin alert not sent. outbox={[(m.to, m.subject) for m in mail.outbox]}",
        )
        self.assertIn("pledge", admin_emails[0].subject.lower())

    # ───── Schedule call flow ─────

    def test_schedule_donor_confirmation_fires(self):
        self._create_call()
        donor_emails = [m for m in mail.outbox if TEST_DONOR in m.to]
        self.assertTrue(
            donor_emails,
            f"Schedule donor confirmation not sent. outbox={[(m.to, m.subject) for m in mail.outbox]}",
        )

    def test_schedule_admin_alert_fires(self):
        self._create_call()
        admin_emails = [m for m in mail.outbox if TEST_ADMIN in m.to]
        self.assertTrue(
            admin_emails,
            f"Schedule admin alert not sent. outbox={[(m.to, m.subject) for m in mail.outbox]}",
        )
        self.assertIn("call", admin_emails[0].subject.lower())
