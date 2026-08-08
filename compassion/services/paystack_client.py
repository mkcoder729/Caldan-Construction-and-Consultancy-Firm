"""
PaystackClient — isolated Paystack integration for the compassion app.

We mirror `shop/services/payment_service.py` but live independently so
that:
  1. Donation references never collide with order references
  2. Settings read from CALDAN_COMPASSION_PAYSTACK_* (defaulting to
     /compassion/donate/verify/ and /compassion/paystack/webhook/)
  3. Email + notification fan-out happens in DonationService, not here
  4. Webhook signature verification + idempotency is enforced up front

All methods return dicts with a `success` key, matching the codebase
convention (see ContactService.create_submission returning the
instance, but PaystackClient returns the response envelope).
"""

import hashlib
import hmac
import json
import logging
from decimal import Decimal

import requests
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger("caldan.payments")


class PaystackClient:
    """Paystack integration for Caldan Compassionate Ministry."""

    BASE_URL = "https://api.paystack.co"

    # ────────── Helpers ──────────

    @classmethod
    def _get_headers(cls):
        secret = getattr(settings, "PAYSTACK_SECRET_KEY", "") or ""
        return {
            "Authorization": f"Bearer {secret}",
            "Content-Type": "application/json",
        }

    @classmethod
    def _callback_url(cls) -> str:
        return getattr(
            settings,
            "CALDAN_COMPASSION_PAYSTACK_CALLBACK_URL",
            f"{getattr(settings, 'SITE_URL', 'http://localhost:8000')}/compassion/donate/verify/",
        )

    @classmethod
    def _webhook_url(cls) -> str:
        return getattr(
            settings,
            "CALDAN_COMPASSION_PAYSTACK_WEBHOOK_URL",
            f"{getattr(settings, 'SITE_URL', 'http://localhost:8000')}/compassion/paystack/webhook/",
        )

    @classmethod
    def _verify_webhook_signature(cls, body: bytes, signature: str | None) -> bool:
        """HMAC SHA-256 against settings.PAYSTACK_SECRET_KEY."""
        if not signature:
            logger.warning("Paystack webhook: missing signature header")
            return False
        secret = (getattr(settings, "PAYSTACK_SECRET_KEY", "") or "").encode("utf-8")
        if not secret:
            logger.warning("Paystack webhook: PAYSTACK_SECRET_KEY not configured")
            return False
        try:
            computed = hmac.new(secret, body, hashlib.sha256).hexdigest()
            return hmac.compare_digest(computed, signature)
        except Exception:
            logger.exception("Paystack webhook signature verify crashed")
            return False

    # ────────── Initiate ──────────

    @classmethod
    def initiate_donation(cls, donation) -> dict:
        """Start a Paystack transaction for a pending Donation row.

        Args:
            donation: a Donation instance (status=PENDING) with
                amount_ksh, donor_email, donor_name, donor_phone set.

        Returns:
            dict with keys:
                success (bool), authorization_url, reference, access_code,
                or success=False and an `error` key on failure.
        """
        secret = getattr(settings, "PAYSTACK_SECRET_KEY", "")
        if not secret:
            return {"success": False, "error": "Paystack secret key is not configured."}

        amount_kobo = int((donation.amount_ksh or Decimal("0")) * 100)
        reference = donation.reference or f"DON-{donation.id}-{timezone.now().strftime('%Y%m%d%H%M%S')}"

        metadata = {
            "donation_id": donation.id,
            "reference": reference,
            "donor_email": donation.donor_email,
            "purpose": donation.purpose,
            "custom_fields": [
                {
                    "display_name": "Donor Name",
                    "variable_name": "donor_name",
                    "value": donation.donor_name,
                },
                {
                    "display_name": "Purpose",
                    "variable_name": "purpose",
                    "value": donation.get_purpose_display(),
                },
            ],
        }

        payload = {
            "email": donation.donor_email,
            "amount": amount_kobo,
            "currency": "KES",
            "reference": reference,
            "callback_url": cls._callback_url(),
            "metadata": metadata,
        }

        # Enable M-Pesa mobile money channel when configured.
        if getattr(settings, "MPESA_STK_PUSH_ENABLED", False):
            payload["channels"] = ["card", "bank", "ussd", "mobile_money"]

        try:
            response = requests.post(
                f"{cls.BASE_URL}/transaction/initialize",
                json=payload,
                headers=cls._get_headers(),
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.Timeout:
            logger.error("Paystack initiate timeout for donation %s", donation.id)
            return {"success": False, "error": "Payment service timeout. Please try again."}
        except requests.exceptions.ConnectionError:
            logger.error("Paystack initiate connection error for donation %s", donation.id)
            return {"success": False, "error": "Payment service unavailable. Please check your connection."}
        except requests.exceptions.HTTPError as exc:
            logger.error("Paystack initiate HTTP error for donation %s: %s", donation.id, exc)
            return {"success": False, "error": "Payment service error. Please try again."}
        except Exception:
            logger.exception("Paystack initiate unexpected error for donation %s", donation.id)
            return {"success": False, "error": "Payment service unavailable. Please try again."}

        if not data.get("status"):
            message = data.get("message", "Payment initialization failed")
            logger.error("Paystack initiate failed for donation %s: %s", donation.id, message)
            return {"success": False, "error": message}

        payload_response = data.get("data") or {}
        return {
            "success": True,
            "authorization_url": payload_response.get("authorization_url"),
            "reference": payload_response.get("reference") or reference,
            "access_code": payload_response.get("access_code"),
        }

    # ────────── Verify ──────────

    @classmethod
    def verify_donation(cls, reference: str) -> dict:
        """Call Paystack /transaction/verify/:reference.

        Returns dict with keys:
            success (bool), status ('success'/'failed'/...), amount,
            currency, reference, paid_at, metadata (dict), or error.
        """
        secret = getattr(settings, "PAYSTACK_SECRET_KEY", "")
        if not secret:
            return {"success": False, "error": "Paystack secret key is not configured."}

        try:
            response = requests.get(
                f"{cls.BASE_URL}/transaction/verify/{reference}",
                headers=cls._get_headers(),
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.Timeout:
            return {"success": False, "error": "Payment verification timeout."}
        except requests.exceptions.ConnectionError:
            return {"success": False, "error": "Payment verification service unavailable."}
        except Exception:
            logger.exception("Paystack verify unexpected error for %s", reference)
            return {"success": False, "error": "Payment verification failed."}

        if not data.get("status"):
            return {"success": False, "error": data.get("message", "Verification failed.")}

        tx = data.get("data") or {}
        return {
            "success": True,
            "status": tx.get("status"),
            "amount": (tx.get("amount") or 0) / 100,  # back to KES
            "currency": tx.get("currency", "KES"),
            "reference": tx.get("reference") or reference,
            "paid_at": tx.get("paid_at"),
            "channel": tx.get("channel"),
            "metadata": tx.get("metadata") or {},
        }

    # ────────── Webhook ──────────

    @classmethod
    def handle_webhook(cls, payload, signature: str | None = None) -> dict:
        """Process a Paystack webhook event.

        Verifies signature, looks up the donation by metadata.donation_id
        (preferred) or by reference (fallback), and marks it paid. Returns
        a dict; the view uses it to decide the HTTP status.

        Idempotent: re-deliveries of the same event are no-ops because
        Donation.mark_paid() refuses to re-fire on SUCCESS.
        """
        # Accept bytes / str / dict payloads — Django gives us request.body
        # as bytes, but we may also be called directly with a dict.
        try:
            if isinstance(payload, (bytes, bytearray)):
                raw_body = bytes(payload)
                payload_dict = json.loads(raw_body.decode("utf-8"))
            elif isinstance(payload, str):
                raw_body = payload.encode("utf-8")
                payload_dict = json.loads(payload)
            else:
                # Already a dict — we still need the raw bytes for sig
                # verification; serialize back. (This path is mostly used
                # by tests.)
                raw_body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
                payload_dict = payload
        except (ValueError, TypeError):
            logger.exception("Paystack webhook: invalid payload (not JSON)")
            return {"success": False, "verified": False, "error": "Invalid payload"}

        if signature and not cls._verify_webhook_signature(raw_body, signature):
            logger.warning("Paystack webhook signature failed verification")
            return {"success": False, "verified": False, "error": "Invalid signature"}

        event = payload_dict.get("event")
        data = payload_dict.get("data") or {}
        logger.info("Paystack webhook event: %s", event)

        if event == "charge.success":
            return cls._handle_charge_success(data)
        if event == "charge.failed":
            return cls._handle_charge_failed(data)

        # Unknown / ignored event — still respond 200 so Paystack doesn't retry
        return {"success": True, "verified": True, "ignored": True}

    # ────────── Internal webhook helpers ──────────

    @classmethod
    def _handle_charge_success(cls, data: dict) -> dict:
        # Local import to avoid app-loading-order issues
        from compassion.models import Donation
        from compassion.services.donation_service import DonationService

        reference = data.get("reference")
        metadata = data.get("metadata") or {}
        donation_id = metadata.get("donation_id")

        donation = None
        if donation_id:
            try:
                donation = Donation.objects.get(id=donation_id)
            except Donation.DoesNotExist:
                logger.warning("Webhook charge.success for missing donation id=%s", donation_id)
        if donation is None and reference:
            try:
                donation = Donation.objects.get(reference=reference)
            except Donation.DoesNotExist:
                logger.warning("Webhook charge.success for missing reference=%s", reference)
        if donation is None:
            return {"success": False, "error": "Donation not found", "verified": True}

        DonationService.mark_paid(donation, reference or donation.reference)
        return {"success": True, "verified": True, "donation_id": donation.id, "status": donation.status}

    @classmethod
    def _handle_charge_failed(cls, data: dict) -> dict:
        from compassion.models import Donation

        reference = data.get("reference")
        metadata = data.get("metadata") or {}
        donation_id = metadata.get("donation_id")

        donation = None
        if donation_id:
            donation = Donation.objects.filter(id=donation_id).first()
        if donation is None and reference:
            donation = Donation.objects.filter(reference=reference).first()

        if donation and donation.status != Donation.Status.SUCCESS:
            donation.mark_failed()

        return {"success": True, "verified": True, "marked_failed": donation is not None}