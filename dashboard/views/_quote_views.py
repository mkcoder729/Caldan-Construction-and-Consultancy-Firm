"""
Quote Request Management Views for Dashboard.

Thin views wrapping `QuoteService` for the admin interface.
"""
import logging
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.shortcuts import render, redirect, get_object_or_404

from accounts.permissions.decorators import admin_required
from website.models.quote import QuoteRequest
from website.services.quote_service import QuoteService

logger = logging.getLogger("caldan.dashboard")


@login_required
@admin_required
def quote_list(request):
    """List all quote requests with search and filters."""
    search = request.GET.get("search", "").strip()
    project_type = request.GET.get("project_type", "").strip()
    budget_range = request.GET.get("budget_range", "").strip()
    timeline = request.GET.get("timeline", "").strip()
    replied_param = request.GET.get("replied", "").strip()

    replied = None
    if replied_param == "yes":
        replied = True
    elif replied_param == "no":
        replied = False

    quotes = QuoteService.get_admin_quotes(
        user=request.user,
        search=search or None,
        project_type=project_type or None,
        budget_range=budget_range or None,
        timeline=timeline or None,
        replied=replied,
    )

    stats = QuoteService.get_quote_stats()

    paginator = Paginator(quotes, 20)
    page = request.GET.get("page", 1)
    try:
        quotes_page = paginator.page(page)
    except PageNotAnInteger:
        quotes_page = paginator.page(1)
    except EmptyPage:
        quotes_page = paginator.page(paginator.num_pages)

    context = {
        "quotes": quotes_page,
        "stats": stats,
        "search": search,
        "project_type": project_type,
        "budget_range": budget_range,
        "timeline": timeline,
        "replied": replied_param,
        "project_type_choices": QuoteRequest._meta.get_field("project_type").choices,
        "budget_range_choices": QuoteRequest.BudgetRange.choices,
        "timeline_choices": QuoteRequest.Timeline.choices,
        "page_title": "Quote Requests",
    }

    return render(request, "dashboard/quotes/list.html", context)


@login_required
@admin_required
def quote_detail(request, quote_id):
    """View a single quote request with reply actions."""
    quote = QuoteService.get_quote_by_id(quote_id, user=request.user)
    if not quote:
        messages.error(request, "Quote request not found.")
        return redirect("dashboard:quote_list")

    context = {
        "quote": quote,
        "page_title": f"Quote from {quote.name}",
    }
    return render(request, "dashboard/quotes/detail.html", context)


@login_required
@admin_required
def quote_toggle_replied(request, quote_id):
    """Toggle replied status on a quote."""
    quote = get_object_or_404(QuoteRequest, id=quote_id)

    if request.method == "POST":
        target_state = not quote.is_replied
        QuoteService.mark_replied(request.user, quote, replied=target_state)
        if target_state:
            messages.success(request, f'Quote from {quote.name} marked as replied.')
        else:
            messages.success(request, f'Quote from {quote.name} marked as awaiting reply.')
    return redirect("dashboard:quote_detail", quote_id=quote.id)


@login_required
@admin_required
def quote_delete(request, quote_id):
    """Delete a quote request. POST-only for the destructive path."""
    quote = get_object_or_404(QuoteRequest, id=quote_id)

    if request.method == "POST":
        QuoteService.delete_quote(request.user, quote)
        messages.success(request, f'Quote from {quote.name} deleted.')
        return redirect("dashboard:quote_list")

    context = {
        "quote": quote,
        "page_title": f"Delete Quote from {quote.name}",
    }
    return render(request, "dashboard/quotes/delete_confirm.html", context)
