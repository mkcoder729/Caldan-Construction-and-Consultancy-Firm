"""
Public-facing views for Caldan Compassionate Ministry.

All JSON/AJAX endpoints return `{"success": bool, ...}` so the front
end can render success / error states uniformly. Non-AJAX POSTs get
redirected back to the index with a Django message.
"""

import logging

from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.views.decorators.http import require_http_methods

from compassion.forms import (
    DonationForm,
    InKindDonationForm,
    ScheduleCallForm,
)
from compassion.models import ScheduleCall
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

    context = {
        "ministry": settings,
        "stories": stories,
        "payment_methods": payment_methods,
        "donation_form": donation_form,
        "inkind_form": inkind_form,
        "call_form": call_form,
        "page_title": "Compassionate Ministry",
        "meta_description": (
            "Give money, items, or schedule a call. Every gift reaches a "
            "hospital bedside, a prison visit, or a neighbour in need."
        ),
    }
    return render(request, "compassion/index.html", context)


def donate_page(request):
    """Dedicated full-page donate flow — used when the inline modal isn't available."""
    settings = MinistryService.get_solo()
    donation_form = DonationForm(initial={"amount": 1000})
    context = {
        "ministry": settings,
        "donation_form": donation_form,
        "page_title": "Donate — Caldan Compassionate Ministry",
    }
    return render(request, "compassion/donate.html", context)


@require_http_methods(["POST"])
def donate_initiate(request):
    """AJAX endpoint: validate form → create PENDING Donation →
    call Paystack → return authorization_url JSON.
    """
    form = DonationForm(request.POST)
    if not form.is_valid():
        return JsonResponse(
            {"success": False, "errors": form.errors, "error": "Please correct the highlighted fields."},
            status=400,
        )

    cleaned = form.cleaned_data

    # If "schedule a call" is ticked, we treat this as a partnership
    # request — create a ScheduleCall row and don't initiate a charge.
    if cleaned.get("schedule_call"):
        try:
            call = ScheduleService.create_call_request(
                name=cleaned["name"],
                email=cleaned["email"],
                phone=cleaned["phone"],
                topic=ScheduleCall.Topic.LARGE_DONATION,
                preferred_time="To be arranged",
                message=(
                    f"Large donation inquiry of KES {cleaned['amount']} "
                    f"for {cleaned['purpose']}. {cleaned.get('note', '')}".strip()
                ),
                request=request,
            )
            return JsonResponse(
                {
                    "success": True,
                    "schedule_call_id": call.id,
                    "message": "Thanks — we'll be in touch to arrange your call.",
                }
            )
        except Exception as exc:
            logger.exception("schedule_call from donate_initiate failed: %s", exc)
            return JsonResponse(
                {"success": False, "error": "We could not save your call request. Please try again."},
                status=500,
            )

    # Otherwise, normal Paystack-initiated donation flow.
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
            "message": "Thanks — we'll be in touch within one business day.",
        }
    )


def donation_thank_you(request):
    """Landing page after a successful Paystack charge.

    The actual verification + mark_paid happens via the verify URL or
    webhook. This page is the donor-facing "we got it" screen:
    when the ref resolves to a real Donation we show the full gift
    summary (amount, designation, donor name, paystack reference).
    Otherwise we fall back to a graceful "thank you" that doesn't
    promise more than we know.
    """
    from compassion.models import Donation  # local import: avoid circular

    ref = request.GET.get("ref", "").strip()
    donation = None
    if ref:
        donation = (
            Donation.objects.filter(reference=ref)
            .select_related()
            .first()
        )

    return render(
        request,
        "compassion/thank_you.html",
        {
            "reference": ref,
            "donation": donation,
            "page_title": "Thank you",
            "meta_description": "Thank you for supporting Caldan Compassionate Ministry.",
        },
    )


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