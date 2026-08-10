"""
Paystack-side endpoints for Caldan Compassionate Ministry:

  * /compassion/donate/verify/  — GET after Paystack popup onSuccess,
                                  returns JSON when called via AJAX,
                                  redirects otherwise.
  * /compassion/paystack/webhook/  — POST, signature-verified

Both paths converge on DonationService.mark_paid which is idempotent.
"""

import logging

from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from compassion.models import Donation
from compassion.services.donation_service import DonationService
from compassion.services.paystack_client import PaystackClient

logger = logging.getLogger("caldan.payments")


def _is_ajax(request) -> bool:
    return request.META.get("HTTP_X_REQUESTED_WITH") == "XMLHttpRequest"


@require_http_methods(["GET"])
def donation_verify(request):
    """Paystack callback: verify the reference, mark paid, return JSON or redirect.

    When called via AJAX (X-Requested-With: XMLHttpRequest), returns a JSON
    payload the celebration modal can render. When called via plain browser
    redirect (no JS / popup fallback), redirects back to /compassion/.
    """
    reference = request.GET.get("reference") or request.GET.get("trxref") or ""
    reference = reference.strip()
    if not reference:
        if _is_ajax(request):
            return JsonResponse({"success": False, "error": "missing reference"}, status=400)
        return redirect(reverse("compassion:index"))

    verify = PaystackClient.verify_donation(reference)
    if not verify.get("success"):
        logger.warning("donation_verify failed for %s: %s", reference, verify.get("error"))
        if _is_ajax(request):
            return JsonResponse(
                {"success": False, "error": verify.get("error", "Verification failed.")},
                status=502,
            )
        return redirect(f"{reverse('compassion:index')}?donation=failed")

    if verify.get("status") != "success":
        if _is_ajax(request):
            return JsonResponse(
                {"success": False, "error": "Payment was not successful."},
                status=402,
            )
        return redirect(f"{reverse('compassion:index')}?donation=failed")

    donation = Donation.objects.filter(reference=reference).first()
    if donation is None:
        # Webhook will reconcile via metadata.donation_id shortly. For now
        # we tell the modal to wait briefly — but the modal flow is best-effort
        # and the user can refresh; the webhook is the canonical path.
        logger.warning("donation_verify: no Donation row for reference=%s", reference)
        if _is_ajax(request):
            return JsonResponse(
                {
                    "success": True,
                    "pending": True,
                    "reference": reference,
                    "message": "Your gift is being confirmed. Receipt will arrive by email.",
                }
            )
        return redirect(f"{reverse('compassion:index')}?donation=pending")

    if donation.status != Donation.Status.SUCCESS:
        DonationService.mark_paid(donation, reference, request=request)

    if _is_ajax(request):
        return JsonResponse(
            {
                "success": True,
                "donation_id": donation.id,
                "reference": donation.reference,
                "amount_ksh": str(donation.amount_ksh),
                "purpose": donation.get_purpose_display(),
                "donor_name": donation.donor_name,
                "donor_email": donation.donor_email,
                "paystack_reference": donation.paystack_reference or "",
                "verified_at": donation.verified_at.isoformat() if donation.verified_at else None,
            }
        )

    return redirect(f"{reverse('compassion:index')}?donation=success")


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