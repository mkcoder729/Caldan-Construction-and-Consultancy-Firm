"""Tests for the compassion donation lifecycle."""

from decimal import Decimal

from django.test import TestCase

from compassion.models import Donation
from compassion.services.donation_service import DonationService

# We assemble emails from parts to avoid any source-level email obfuscation
# in tooling that touches this file.
AT = chr(64)
TEST_EMAIL_A = "test_a" + AT + "example.com"
TEST_EMAIL_B = "test_b" + AT + "example.com"
TEST_EMAIL_C = "test_c" + AT + "example.com"
TEST_EMAIL_D = "test_d" + AT + "example.com"


class DonationServiceTests(TestCase):
    def test_create_pending_donation_normalises_fields(self):
        d = DonationService.create_pending_donation(
            name="  Mary Wanjiku  ",
            email=TEST_EMAIL_A,
            phone="0712345678",
            amount=Decimal("1500.00"),
            purpose=Donation.Purpose.GENERAL,
            note="  please use for hospital visits  ",
        )
        self.assertEqual(d.donor_name, "Mary Wanjiku")
        self.assertEqual(d.donor_email, TEST_EMAIL_A)
        self.assertEqual(d.donor_phone, "0712345678")
        self.assertEqual(d.amount_ksh, Decimal("1500.00"))
        self.assertEqual(d.note, "please use for hospital visits")
        self.assertEqual(d.status, Donation.Status.PENDING)
        self.assertTrue(d.reference.startswith("DON-"))

    def test_mark_paid_is_idempotent(self):
        d = DonationService.create_pending_donation(
            name="Test", email=TEST_EMAIL_A, phone="0712345678",
            amount=Decimal("500"), purpose=Donation.Purpose.GENERAL,
        )
        DonationService.mark_paid(d, "PAY-1")
        self.assertEqual(d.status, Donation.Status.SUCCESS)
        self.assertEqual(d.paystack_reference, "PAY-1")

        # A second mark_paid (e.g. webhook redelivery) must NOT overwrite.
        DonationService.mark_paid(d, "PAY-2")
        d.refresh_from_db()
        self.assertEqual(d.paystack_reference, "PAY-1")
        self.assertEqual(d.status, Donation.Status.SUCCESS)

    def test_mark_failed_sets_status(self):
        d = DonationService.create_pending_donation(
            name="Test", email=TEST_EMAIL_A, phone="0712345678",
            amount=Decimal("500"), purpose=Donation.Purpose.GENERAL,
        )
        DonationService.mark_failed(d)
        d.refresh_from_db()
        self.assertEqual(d.status, Donation.Status.FAILED)

    def test_reference_is_unique(self):
        d1 = DonationService.create_pending_donation(
            name="A", email=TEST_EMAIL_B, phone="0712345678",
            amount=Decimal("500"), purpose=Donation.Purpose.GENERAL,
        )
        d2 = DonationService.create_pending_donation(
            name="B", email=TEST_EMAIL_C, phone="0712345678",
            amount=Decimal("500"), purpose=Donation.Purpose.GENERAL,
        )
        self.assertNotEqual(d1.reference, d2.reference)


class DonationFormTests(TestCase):
    def test_phone_validation_rejects_bad_numbers(self):
        from compassion.forms import DonationForm

        bad = DonationForm(data={
            "name": "X", "email": TEST_EMAIL_A, "phone": "abc",
            "amount": "500", "purpose": "GENERAL",
        })
        self.assertFalse(bad.is_valid())
        self.assertIn("phone", bad.errors)

    def test_phone_validation_accepts_kenyan_formats(self):
        from compassion.forms import DonationForm

        good = DonationForm(data={
            "name": "X", "email": TEST_EMAIL_A, "phone": "+254712345678",
            "amount": "500", "purpose": "GENERAL",
        })
        self.assertTrue(good.is_valid(), good.errors)

    def test_amount_below_minimum_rejected(self):
        from compassion.forms import DonationForm

        f = DonationForm(data={
            "name": "X", "email": TEST_EMAIL_A, "phone": "0712345678",
            "amount": "1", "purpose": "GENERAL",
        })
        self.assertFalse(f.is_valid())
        self.assertIn("amount", f.errors)