"""
Dashboard views for Caldan Compassionate Ministry — admin CRUD for
donations, in-kind pledges, call requests, stories, payment methods,
and ministry settings.

Every view uses a service-layer call for state changes so the audit
trail + email fan-out happens in exactly one place. Views stay thin.
"""

import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.shortcuts import render, redirect, get_object_or_404

from accounts.permissions.decorators import admin_required
from compassion.models import (
    Donation,
    InKindDonation,
    ScheduleCall,
    OutreachStory,
    PaymentMethod,
    MinistrySettings,
)
from compassion.services import (
    DonationService,
    InKindService,
    ScheduleService,
    MinistryService,
    PaymentMethodService,
    StatsService,
)

logger = logging.getLogger("caldan.dashboard")


# ────────── Overview ──────────

@login_required
@admin_required
def dashboard_overview(request):
    """Top-of-dashboard roll-up: counts + totals + latest items."""
    counts = {
        "donations_success": Donation.objects.filter(status=Donation.Status.SUCCESS).count(),
        "donations_pending": Donation.objects.filter(status=Donation.Status.PENDING).count(),
        "inkind_active": InKindDonation.objects.exclude(
            status__in=[InKindDonation.Status.DELIVERED, InKindDonation.Status.CANCELLED]
        ).count(),
        "calls_new": ScheduleCall.objects.filter(status=ScheduleCall.Status.NEW).count(),
        "stories_published": OutreachStory.objects.filter(is_published=True).count(),
    }
    stats = StatsService.get_all_stats()

    latest_donations = Donation.objects.order_by("-created_at")[:5]
    latest_inkind = InKindDonation.objects.order_by("-created_at")[:5]
    latest_calls = ScheduleCall.objects.order_by("-created_at")[:5]

    context = {
        "page_title": "Compassion — Overview",
        "counts": counts,
        "stats": stats,
        "latest_donations": latest_donations,
        "latest_inkind": latest_inkind,
        "latest_calls": latest_calls,
    }
    return render(request, "compassion/dashboard/overview.html", context)


# ────────── Donations ──────────

@login_required
@admin_required
def donation_list(request):
    status = request.GET.get("status", "").strip()
    purpose = request.GET.get("purpose", "").strip()
    search = request.GET.get("search", "").strip()
    qs = DonationService.get_admin_list(
        status=status or None,
        purpose=purpose or None,
        search=search or None,
        request_user=request.user,
    )
    paginator = Paginator(qs, 20)
    page = request.GET.get("page", 1)
    try:
        donations = paginator.page(page)
    except PageNotAnInteger:
        donations = paginator.page(1)
    except EmptyPage:
        donations = paginator.page(paginator.num_pages)

    context = {
        "donations": donations,
        "page_title": "Donations",
        "status": status,
        "purpose": purpose,
        "search": search,
        "status_choices": Donation.Status.choices,
        "purpose_choices": Donation.Purpose.choices,
    }
    return render(request, "compassion/dashboard/donation_list.html", context)


@login_required
@admin_required
def donation_detail(request, donation_id):
    donation = DonationService.get_by_id(donation_id, request_user=request.user)
    if not donation:
        messages.error(request, "Donation not found.")
        return redirect("compassion_dashboard:donation_list")

    context = {
        "donation": donation,
        "page_title": f"Donation {donation.reference}",
    }
    return render(request, "compassion/dashboard/donation_detail.html", context)


@login_required
@admin_required
def donation_advance(request, donation_id):
    if request.method != "POST":
        return redirect("compassion_dashboard:donation_detail", donation_id=donation_id)
    donation = get_object_or_404(Donation, id=donation_id)
    target = request.POST.get("status", "").strip()
    if target not in Donation.Status.values:
        messages.error(request, "Invalid status.")
    else:
        try:
            if target == Donation.Status.SUCCESS:
                DonationService.mark_paid(donation, donation.paystack_reference or donation.reference, request=request)
            elif target == Donation.Status.FAILED:
                DonationService.mark_failed(donation, request=request)
            elif target == Donation.Status.ABANDONED:
                DonationService.mark_abandoned(donation, request=request)
            messages.success(request, f"Donation marked as {target}.")
        except Exception as exc:
            logger.exception("donation_advance failed: %s", exc)
            messages.error(request, "Could not update donation.")
    return redirect("compassion_dashboard:donation_detail", donation_id=donation.id)


# ────────── In-kind ──────────

@login_required
@admin_required
def inkind_list(request):
    status = request.GET.get("status", "").strip()
    item_type = request.GET.get("item_type", "").strip()
    search = request.GET.get("search", "").strip()
    qs = InKindService.get_admin_list(
        status=status or None,
        item_type=item_type or None,
        search=search or None,
        request_user=request.user,
    )
    paginator = Paginator(qs, 20)
    page = request.GET.get("page", 1)
    try:
        pledges = paginator.page(page)
    except PageNotAnInteger:
        pledges = paginator.page(1)
    except EmptyPage:
        pledges = paginator.page(paginator.num_pages)

    context = {
        "pledges": pledges,
        "page_title": "In-Kind Pledges",
        "status": status,
        "item_type": item_type,
        "search": search,
        "status_choices": InKindDonation.Status.choices,
        "item_type_choices": InKindDonation.ItemType.choices,
    }
    return render(request, "compassion/dashboard/inkind_list.html", context)


@login_required
@admin_required
def inkind_detail(request, pledge_id):
    pledge = get_object_or_404(InKindDonation, id=pledge_id)
    context = {"pledge": pledge, "page_title": f"In-Kind Pledge #{pledge.id}"}
    return render(request, "compassion/dashboard/inkind_detail.html", context)


@login_required
@admin_required
def inkind_advance(request, pledge_id):
    if request.method != "POST":
        return redirect("compassion_dashboard:inkind_detail", pledge_id=pledge_id)
    pledge = get_object_or_404(InKindDonation, id=pledge_id)
    target = request.POST.get("status", "").strip()
    try:
        InKindService.advance_status(pledge, target, user=request.user, request=request)
        messages.success(request, f"Pledge status changed to {target}.")
    except ValueError as exc:
        messages.error(request, str(exc))
    except Exception as exc:
        logger.exception("inkind_advance failed: %s", exc)
        messages.error(request, "Could not update pledge status.")
    return redirect("compassion_dashboard:inkind_detail", pledge_id=pledge.id)


# ────────── Schedule calls ──────────

@login_required
@admin_required
def call_list(request):
    status = request.GET.get("status", "").strip()
    topic = request.GET.get("topic", "").strip()
    search = request.GET.get("search", "").strip()
    qs = ScheduleService.get_admin_list(
        status=status or None,
        topic=topic or None,
        search=search or None,
        request_user=request.user,
    )
    paginator = Paginator(qs, 20)
    page = request.GET.get("page", 1)
    try:
        calls = paginator.page(page)
    except PageNotAnInteger:
        calls = paginator.page(1)
    except EmptyPage:
        calls = paginator.page(paginator.num_pages)

    context = {
        "calls": calls,
        "page_title": "Schedule Calls",
        "status": status,
        "topic": topic,
        "search": search,
        "status_choices": ScheduleCall.Status.choices,
        "topic_choices": ScheduleCall.Topic.choices,
    }
    return render(request, "compassion/dashboard/call_list.html", context)


@login_required
@admin_required
def call_detail(request, call_id):
    call = get_object_or_404(ScheduleCall, id=call_id)
    context = {"call": call, "page_title": f"Call Request — {call.name}"}
    return render(request, "compassion/dashboard/call_detail.html", context)


@login_required
@admin_required
def call_advance(request, call_id):
    if request.method != "POST":
        return redirect("compassion_dashboard:call_detail", call_id=call_id)
    call = get_object_or_404(ScheduleCall, id=call_id)
    target = request.POST.get("status", "").strip()
    try:
        ScheduleService.advance_status(call, target, user=request.user, request=request)
        messages.success(request, f"Call status changed to {target}.")
    except ValueError as exc:
        messages.error(request, str(exc))
    except Exception as exc:
        logger.exception("call_advance failed: %s", exc)
        messages.error(request, "Could not update call status.")
    return redirect("compassion_dashboard:call_detail", call_id=call.id)


# ────────── Outreach stories ──────────

@login_required
@admin_required
def story_list(request):
    qs = OutreachStory.objects.all().order_by("display_order", "-event_date", "-created_at")
    paginator = Paginator(qs, 20)
    page = request.GET.get("page", 1)
    try:
        stories = paginator.page(page)
    except PageNotAnInteger:
        stories = paginator.page(1)
    except EmptyPage:
        stories = paginator.page(paginator.num_pages)

    context = {"stories": stories, "page_title": "Outreach Stories"}
    return render(request, "compassion/dashboard/story_list.html", context)


@login_required
@admin_required
def story_create(request):
    if request.method == "POST":
        story = _save_story_from_form(request, OutreachStory())
        messages.success(request, f"Story '{story.title}' created.")
        return redirect("compassion_dashboard:story_list")
    context = {
        "story": OutreachStory(),
        "page_title": "New Outreach Story",
        "categories": OutreachStory.Category.choices,
    }
    return render(request, "compassion/dashboard/story_form.html", context)


@login_required
@admin_required
def story_edit(request, story_id):
    story = get_object_or_404(OutreachStory, id=story_id)
    if request.method == "POST":
        story = _save_story_from_form(request, story)
        messages.success(request, f"Story '{story.title}' updated.")
        return redirect("compassion_dashboard:story_list")
    context = {
        "story": story,
        "page_title": f"Edit — {story.title}",
        "categories": OutreachStory.Category.choices,
    }
    return render(request, "compassion/dashboard/story_form.html", context)


def _save_story_from_form(request, story: OutreachStory) -> OutreachStory:
    story.title = request.POST.get("title", "").strip()
    story.summary = request.POST.get("summary", "").strip()
    story.body = request.POST.get("body", "").strip()
    story.category = request.POST.get("category", OutreachStory.Category.NEIGHBOURHOOD)
    story.location = request.POST.get("location", "").strip()
    story.event_date = request.POST.get("event_date") or None
    try:
        story.people_served = int(request.POST.get("people_served") or 0)
    except (TypeError, ValueError):
        story.people_served = 0
    try:
        story.display_order = int(request.POST.get("display_order") or 0)
    except (TypeError, ValueError):
        story.display_order = 0
    story.is_published = bool(request.POST.get("is_published"))
    if "cover_image" in request.FILES:
        story.cover_image = request.FILES["cover_image"]
    story.save()
    return story


# ────────── Payment methods ──────────

@login_required
@admin_required
def payment_method_list(request):
    qs = PaymentMethod.objects.all().order_by("display_order", "method", "label")
    context = {
        "methods": qs,
        "page_title": "Payment Methods",
        "method_choices": PaymentMethod.Method.choices,
    }
    return render(request, "compassion/dashboard/payment_method_list.html", context)


@login_required
@admin_required
def payment_method_create(request):
    if request.method == "POST":
        method = _save_payment_method_from_form(request, PaymentMethod())
        messages.success(request, "Payment method added.")
        return redirect("compassion_dashboard:payment_method_list")
    context = {
        "method": PaymentMethod(),
        "page_title": "New Payment Method",
        "method_choices": PaymentMethod.Method.choices,
    }
    return render(request, "compassion/dashboard/payment_method_form.html", context)


@login_required
@admin_required
def payment_method_edit(request, method_id):
    method = get_object_or_404(PaymentMethod, id=method_id)
    if request.method == "POST":
        method = _save_payment_method_from_form(request, method)
        messages.success(request, "Payment method updated.")
        return redirect("compassion_dashboard:payment_method_list")
    context = {
        "method": method,
        "page_title": f"Edit — {method.label}",
        "method_choices": PaymentMethod.Method.choices,
    }
    return render(request, "compassion/dashboard/payment_method_form.html", context)


@login_required
@admin_required
def payment_method_toggle_active(request, method_id):
    if request.method != "POST":
        return redirect("compassion_dashboard:payment_method_list")
    method = get_object_or_404(PaymentMethod, id=method_id)
    method.is_active = not method.is_active
    method.save(update_fields=["is_active", "updated_at"])
    messages.success(
        request,
        f"Payment method {'activated' if method.is_active else 'deactivated'}.",
    )
    return redirect("compassion_dashboard:payment_method_list")


def _save_payment_method_from_form(request, method: PaymentMethod) -> PaymentMethod:
    method.method = request.POST.get("method", PaymentMethod.Method.PAYBILL)
    method.label = request.POST.get("label", "").strip()
    method.account_number = request.POST.get("account_number", "").strip()
    method.account_name = request.POST.get("account_name", "").strip()
    method.bank_name = request.POST.get("bank_name", "").strip()
    method.instructions = request.POST.get("instructions", "").strip()
    try:
        method.display_order = int(request.POST.get("display_order") or 0)
    except (TypeError, ValueError):
        method.display_order = 0
    method.is_active = bool(request.POST.get("is_active"))
    method.save()
    return method


# ────────── Ministry settings ──────────

@login_required
@admin_required
def ministry_settings_edit(request):
    settings = MinistryService.get_solo()
    if request.method == "POST":
        settings.hero_title = request.POST.get("hero_title", settings.hero_title).strip()
        settings.hero_subtitle = request.POST.get("hero_subtitle", settings.hero_subtitle).strip()
        settings.hero_cta_label = request.POST.get("hero_cta_label", settings.hero_cta_label).strip()
        settings.mission_statement = request.POST.get("mission_statement", settings.mission_statement).strip()
        settings.contact_phone = request.POST.get("contact_phone", settings.contact_phone).strip()
        settings.contact_email = request.POST.get("contact_email", settings.contact_email).strip()
        settings.default_currency = request.POST.get("default_currency", settings.default_currency).strip() or "KES"
        settings.save()
        messages.success(request, "Ministry settings updated.")
        return redirect("compassion_dashboard:ministry_settings_edit")
    context = {"settings": settings, "page_title": "Ministry Settings"}
    return render(request, "compassion/dashboard/ministry_settings_form.html", context)