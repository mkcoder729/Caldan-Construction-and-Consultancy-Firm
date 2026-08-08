"""Tests for the Paystack webhook + HMAC signature verification."""

import hashlib
import hmac
import json
from decimal import Decimal

from django.conf import settings
from django.test import TestCase, override_settings

from compassion.models import Donation
from compassion.services.donation_service import DonationService
from compassion.services.paystack_client import PaystackClient


def _sign(body: bytes, secret: str) -> str:
    return hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


@override_settings(PAYSTACK_SECRET_KEY="sk_test_dummy")
class PaystackClientTests(TestCase):
    def test_signature_verify_passes_for_valid_signature(self):
        body = b'{"hello": "world"}'
        sig = _sign(body, "sk_test_dummy")
        self.assertTrue(PaystackClient._verify_webhook_signature(body, sig))

    def test_signature_verify_fails_for_bad_signature(self):
        self.assertFalse(PaystackClient._verify_webhook_signature(b"{}", "deadbeef"))

    def test_signature_verify_returns_false_when_signature_missing(self):
        self.assertFalse(PaystackClient._verify_webhook_signature(b"{}", None))

    @override_settings(PAYSTACK_SECRET_KEY="")
    def test_signature_verify_returns_false_when_secret_unset(self):
        self.assertFalse(PaystackClient._verify_webhook_signature(b"{}", "anything"))

    def _build_signed_payload(self, donation):
        body_dict = {
            "event": "charge.success",
            "data": {
                "reference": donation.reference,
                "amount": 50000,
                "currency": "KES",
                "channel": "mobile_money",
                "paid_at": "2024-01-01T12:00:00.000Z",
                "metadata": {
                    "donation_id": donation.id,
                    "donor_email": donation.donor_email,
                    "purpose": donation.purpose,
                },
            },
        }
        raw = json.dumps(body_dict, separators=(",", ":")).encode("utf-8")
        sig = _sign(raw, settings.PAYSTACK_SECRET_KEY)
        return raw, sig

    def test_webhook_charge_success_marks_donation_paid(self):
        d = DonationService.create_pending_donation(
            name="Web", email="[email protected]", phone="0712345678",
            amount=Decimal("500"), purpose=Donation.Purpose.GENERAL,
        )
        raw, sig = self._build_signed_payload(d)
        result = PaystackClient.handle_webhook(raw, sig)
        self.assertTrue(result["success"])

        d.refresh_from_db()
        self.assertEqual(d.status, Donation.Status.SUCCESS)
        self.assertEqual(d.paystack_reference, d.reference)

    def test_webhook_redelivery_is_idempotent(self):
        d = DonationService.create_pending_donation(
            name="Web", email="[email protected]", phone="0712345678",
            amount=Decimal("500"), purpose=Donation.Purpose.GENERAL,
        )
        raw, sig = self._build_signed_payload(d)

        PaystackClient.handle_webhook(raw, sig)
        PaystackClient.handle_webhook(raw, sig)  # second call must NOT crash

        d.refresh_from_db()
        self.assertEqual(d.status, Donation.Status.SUCCESS)

    def test_webhook_rejects_bad_signature(self):
        d = DonationService.create_pending_donation(
            name="Web", email="[email protected]", phone="0712345678",
            amount=Decimal("500"), purpose=Donation.Purpose.GENERAL,
        )
        raw, _ = self._build_signed_payload(d)
        result = PaystackClient.handle_webhook(raw, signature="wrong-signature")
        self.assertFalse(result["success"])
        self.assertFalse(result["verified"])
        d.refresh_from_db()
        self.assertEqual(d.status, Donation.Status.PENDING)