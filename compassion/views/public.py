"""
Public-facing views for Caldan Compassionate Ministry.

All JSON/AJAX endpoints return `{"success": bool, ...}` so the front
end can render success / error states uniformly. Non-AJAX POSTs get
redirected back to the index with a Django message.
"""

import logging

from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.views.decorators.http import require_http_methods

from compassion.forms import (
    DonationForm,
    InKindDonationForm,
    ScheduleCallForm,
)
from compassion.services.donation_service import DonationService
from compassion.services.inkind_service import InKindService
from compassion.services.schedule_service import ScheduleService
from compassion.services.paystack_client import PaystackClient
from compassion.services.ministry_service import MinistryService
from compassion.services.payment_method_service import PaymentMethodService
from compassion.services.stats_service import StatsService
from compassion.models import OutreachStory

logger = logging.getLogger(__name__)


def _is_ajax(request) -> bool:
    return (
        request.META.get("HTTP_X_REQUESTED_WITH") == "XMLHttpRequest"
        or request.accepts("application/json")
    )


def compassion_index(request):
    """The main /compassion/ page — hero, carousel, 3 cards, stats grid."""
    settings = MinistryService.get_solo()
    stories = (
        OutreachStory.objects.filter(is_published=True)
        .order_by("display_order", "-event_date", "-created_at")[:12]
    )
    payment_methods = PaymentMethodService.get_active()

    # Pre-render the forms so initial state is always available even if
    # the user submits before any JS loads.
    donation_form = DonationForm(initial={"amount": 1000})
    inkind_form = InKindDonationForm()
    call_form = ScheduleCallForm()

    # Paystack public key is needed by the inline JS to open the popup
    # over our site. Empty string when not configured — the JS guard
    # falls back to the redirect flow.
    from django.conf import settings as dj_settings
    paystack_public_key = getattr(dj_settings, "PAYSTACK_PUBLIC_KEY", "") or ""

    context = {
        "ministry": settings,
        "stories": stories,
        "payment_methods": payment_methods,
        "donation_form": donation_form,
        "inkind_form": inkind_form,
        "call_form": call_form,
        "paystack_public_key": paystack_public_key,
        "page_title": "Compassionate Ministry",
        "meta_description": (
            "Give money, items, or schedule a call. Every gift reaches a "
            "hospital bedside, a prison visit, or a neighbour in need."
        ),
    }
    return render(request, "compassion/index.html", context)


def donate_page(request):
    """Dedicated full-page donate flow — used when the inline modal isn't available."""
    from django.conf import settings as dj_settings  # local import keeps the
    # module-import surface unchanged and matches the pattern in `index()`.
    settings = MinistryService.get_solo()
    donation_form = DonationForm(initial={"amount": 1000})
    # Mirror the index view's context so the Paystack inline V2 popup
    # can boot on this page too. Without this, the JS handler falls
    # back to a top-level redirect (browser → Paystack → callback),
    # bypassing the celebration modal.
    paystack_public_key = getattr(dj_settings, "PAYSTACK_PUBLIC_KEY", "") or ""
    context = {
        "ministry": settings,
        "donation_form": donation_form,
        "paystack_public_key": paystack_public_key,
        "page_title": "Donate — Caldan Compassionate Ministry",
    }
    return render(request, "compassion/donate.html", context)


@require_http_methods(["POST"])
def donate_initiate(request):
    """AJAX endpoint: validate form → create PENDING Donation →
    call Paystack → return authorization_url + access_code JSON.
    """
    form = DonationForm(request.POST)
    if not form.is_valid():
        return JsonResponse(
            {"success": False, "errors": form.errors, "error": "Please correct the highlighted fields."},
            status=400,
        )

    cleaned = form.cleaned_data

    try:
        donation = DonationService.create_pending_donation(
            name=cleaned["name"],
            email=cleaned["email"],
            phone=cleaned["phone"],
            amount=cleaned["amount"],
            purpose=cleaned["purpose"],
            note=cleaned.get("note", ""),
            request=request,
        )
    except Exception as exc:
        logger.exception("create_pending_donation failed: %s", exc)
        return JsonResponse(
            {"success": False, "error": "We could not record your donation. Please try again."},
            status=500,
        )

    paystack = PaystackClient.initiate_donation(donation)
    if not paystack.get("success"):
        # Roll the donation to FAILED so it doesn't sit PENDING forever.
        DonationService.mark_failed(donation, request=request)
        return JsonResponse(
            {"success": False, "error": paystack.get("error", "Payment initialization failed.")},
            status=502,
        )

    return JsonResponse(
        {
            "success": True,
            "authorization_url": paystack.get("authorization_url"),
            "access_code": paystack.get("access_code"),
            "reference": paystack.get("reference"),
            "donation_id": donation.id,
        }
    )


@require_http_methods(["POST"])
def inkind_submit(request):
    """AJAX endpoint for the Give Items modal."""
    form = InKindDonationForm(request.POST)
    if not form.is_valid():
        return JsonResponse(
            {"success": False, "errors": form.errors, "error": "Please correct the highlighted fields."},
            status=400,
        )
    cleaned = form.cleaned_data
    try:
        pledge = InKindService.create_pledge(
            name=cleaned["name"],
            email=cleaned["email"],
            phone=cleaned["phone"],
            item_type=cleaned["item_type"],
            item_description=cleaned["item_description"],
            quantity_estimate=cleaned.get("quantity_estimate", ""),
            delivery_mode=cleaned.get("delivery_mode", ""),
            preferred_date=cleaned.get("preferred_date"),
            address=cleaned.get("address", ""),
            notes=cleaned.get("notes", ""),
            request=request,
        )
    except Exception as exc:
        logger.exception("create_pledge failed: %s", exc)
        return JsonResponse(
            {"success": False, "error": "We could not save your pledge. Please try again."},
            status=500,
        )

    return JsonResponse(
        {
            "success": True,
            "pledge_id": pledge.id,
            "donor_name": pledge.donor_name,
            "donor_email": pledge.donor_email,
            "item_type": pledge.get_item_type_display(),
            "item_description": pledge.item_description,
            "quantity_estimate": pledge.quantity_estimate or "",
            "delivery_mode": pledge.get_delivery_mode_display() if pledge.delivery_mode else "",
            "purpose": pledge.get_item_type_display(),
            "message": "Thanks — we'll be in touch to coordinate pickup or delivery.",
        }
    )


@require_http_methods(["POST"])
def schedule_call_submit(request):
    """AJAX endpoint for the Schedule a Call modal."""
    form = ScheduleCallForm(request.POST)
    if not form.is_valid():
        logger.warning("schedule_call_submit invalid form: %s", form.errors.as_json())
        return JsonResponse(
            {"success": False, "errors": form.errors, "error": "Please correct the highlighted fields."},
            status=400,
        )
    cleaned = form.cleaned_data
    try:
        call = ScheduleService.create_call_request(
            name=cleaned["name"],
            email=cleaned["email"],
            phone=cleaned["phone"],
            topic=cleaned["topic"],
            preferred_time=cleaned["preferred_time"],
            message=cleaned.get("message", ""),
            request=request,
        )
    except Exception as exc:
        logger.exception("create_call_request failed: %s", exc)
        return JsonResponse(
            {"success": False, "error": "We could not save your call request. Please try again.", "debug": str(exc)},
            status=500,
        )

    return JsonResponse(
        {
            "success": True,
            "call_id": call.id,
            "donor_name": call.name,
            "donor_email": call.email,
            "topic": call.get_topic_display(),
            "preferred_time": call.preferred_time,
            "message": "Thanks — we'll be in touch within one business day.",
        }
    )


@require_http_methods(["GET"])
def donation_receipt_pdf(request):
    """Stream the donor-facing PDF receipt.

    Generates (or fetches from cache) the branded A5 PDF. Only succeeds
    when the donation is SUCCESS — a pending donation doesn't have a
    receipt to issue.
    """
    from compassion.models import Donation  # local import: avoid circular
    from reports.services.pdf_service import PDFService

    ref = request.GET.get("ref", "").strip()
    if not ref:
        return JsonResponse({"success": False, "error": "missing ref"}, status=400)

    donation = Donation.objects.filter(reference=ref).first()
    if donation is None:
        return JsonResponse({"success": False, "error": "donation not found"}, status=404)
    if donation.status != Donation.Status.SUCCESS:
        return JsonResponse(
            {"success": False, "error": "receipt is only available after Paystack confirms"},
            status=409,
        )

    try:
        pdf_path = PDFService.generate_compassion_donation_receipt(donation)
    except Exception as exc:
        logger.exception("Receipt PDF generation failed for %s: %s", donation.reference, exc)
        return JsonResponse(
            {"success": False, "error": "we could not generate your receipt right now"},
            status=500,
        )

    with open(pdf_path, "rb") as fh:
        pdf_bytes = fh.read()

    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = (
        f'attachment; filename="Caldan-Receipt-{donation.reference}.pdf"'
    )
    response["Content-Length"] = str(len(pdf_bytes))
    return response


@require_http_methods(["GET"])
def inkind_receipt_pdf(request):
    """Stream the donor-facing PDF receipt for an in-kind pledge.

    The ``ref`` query param is the InKindDonation primary key (the model
    has no separate reference string). Always available — there's no
    payment pending state to gate on.
    """
    from compassion.models import InKindDonation
    from reports.services.pdf_service import PDFService

    ref = request.GET.get("ref", "").strip()
    if not ref.isdigit():
        return JsonResponse({"success": False, "error": "invalid ref"}, status=400)
    pledge = InKindDonation.objects.filter(id=int(ref)).first()
    if not pledge:
        return JsonResponse({"success": False, "error": "pledge not found"}, status=404)

    try:
        pdf_path = PDFService.generate_compassion_inkind_receipt(pledge)
    except Exception as exc:
        logger.exception("InKind PDF gen failed for %s: %s", pledge.id, exc)
        return JsonResponse(
            {"success": False, "error": "could not generate your receipt right now"},
            status=500,
        )

    with open(pdf_path, "rb") as fh:
        pdf_bytes = fh.read()
    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = (
        f'attachment; filename="Caldan-InKind-Pledge-{pledge.id}.pdf"'
    )
    response["Content-Length"] = str(len(pdf_bytes))
    return response


@require_http_methods(["GET"])
def call_receipt_pdf(request):
    """Stream the donor-facing PDF receipt for a schedule-call request."""
    from compassion.models import ScheduleCall
    from reports.services.pdf_service import PDFService

    ref = request.GET.get("ref", "").strip()
    if not ref.isdigit():
        return JsonResponse({"success": False, "error": "invalid ref"}, status=400)
    call = ScheduleCall.objects.filter(id=int(ref)).first()
    if not call:
        return JsonResponse({"success": False, "error": "call request not found"}, status=404)

    try:
        pdf_path = PDFService.generate_compassion_call_receipt(call)
    except Exception as exc:
        logger.exception("Call PDF gen failed for %s: %s", call.id, exc)
        return JsonResponse(
            {"success": False, "error": "could not generate your receipt right now"},
            status=500,
        )

    with open(pdf_path, "rb") as fh:
        pdf_bytes = fh.read()
    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = (
        f'attachment; filename="Caldan-Call-Request-{call.id}.pdf"'
    )
    response["Content-Length"] = str(len(pdf_bytes))
    return response


def story_detail(request, slug):
    """Public detail page for a single OutreachStory.

    Linked from the carousel's "Read more" affordance. Renders the
    full `body` text (markdown-light — paragraphs split on blank
    lines), the cover image at full size, and the field metadata
    (location, date, people served).
    """
    story = get_object_or_404(
        OutreachStory.objects.filter(is_published=True),
        slug=slug,
    )
    # Sidebar: up to 4 related stories from the same category, excluding self.
    related = (
        OutreachStory.objects.filter(is_published=True, category=story.category)
        .exclude(pk=story.pk)
        .order_by("display_order", "-event_date")[:4]
    )
    return render(
        request,
        "compassion/story_detail.html",
        {
            "story": story,
            "related_stories": related,
            "page_title": story.title,
            "meta_description": story.summary[:200],
        },
    )