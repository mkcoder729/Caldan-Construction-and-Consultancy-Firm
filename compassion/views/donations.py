"""
Paystack-side endpoints for Caldan Compassionate Ministry:

  * /compassion/donate/verify/  — GET after redirect-back from Paystack
  * /compassion/paystack/webhook/  — POST, signature-verified

Both paths converge on DonationService.mark_paid which is idempotent.
"""

import logging

from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import redirect
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from compassion.models import Donation
from compassion.services.donation_service import DonationService
from compassion.services.paystack_client import PaystackClient

logger = logging.getLogger("caldan.payments")


@require_http_methods(["GET"])
def donation_verify(request):
    """Paystack redirect-back: verify the reference, mark paid, redirect to thank-you."""
    reference = request.GET.get("reference") or request.GET.get("trxref") or ""
    reference = reference.strip()
    if not reference:
        return redirect(reverse("compassion:index"))

    verify = PaystackClient.verify_donation(reference)
    if not verify.get("success"):
        logger.warning("donation_verify failed for %s: %s", reference, verify.get("error"))
        return redirect(f"{reverse('compassion:index')}?donation=failed")

    if verify.get("status") != "success":
        return redirect(f"{reverse('compassion:index')}?donation=failed")

    donation = Donation.objects.filter(reference=reference).first()
    if donation is None:
        # metadata.donation_id is the canonical join — Paystack webhook
        # will pick this up and mark the donation paid shortly. For now,
        # log and bounce to thank-you so the donor isn't left hanging.
        logger.warning("donation_verify: no Donation row for reference=%s", reference)
        return redirect(f"{reverse('compassion:thank_you')}?ref={reference}")

    if donation.status != Donation.Status.SUCCESS:
        DonationService.mark_paid(donation, reference, request=request)

    return redirect(f"{reverse('compassion:thank_you')}?ref={reference}")


@csrf_exempt
@require_http_methods(["POST"])
def paystack_webhook(request):
    """Paystack webhook entry point.

    Signature is verified inside PaystackClient.handle_webhook. We
    always return 200 once we've successfully processed the event so
    Paystack doesn't retry — even on `verified=False`, the response is
    a 200 so retries don't pile up.
    """
    signature = request.META.get("HTTP_X_PAYSTACK_SIGNATURE")
    result = PaystackClient.handle_webhook(request.body, signature)
    status_code = 200 if result.get("success") is not False else 400
    return HttpResponse(status=status_code)