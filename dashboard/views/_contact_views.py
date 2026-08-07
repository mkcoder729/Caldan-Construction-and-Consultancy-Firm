"""
Contact Message Management Views for Dashboard.

Thin views wrapping `ContactService` for the admin interface.
"""
import logging
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.shortcuts import render, redirect, get_object_or_404

from accounts.permissions.decorators import admin_required
from website.models.contact import ContactSubmission
from website.services.contact_service import ContactService

logger = logging.getLogger("caldan.dashboard")


@login_required
@admin_required
def contact_list(request):
    """List all contact messages with search and filters."""
    search = request.GET.get("search", "").strip()
    replied_param = request.GET.get("replied", "").strip()

    replied = None
    if replied_param == "yes":
        replied = True
    elif replied_param == "no":
        replied = False

    messages_qs = ContactService.get_admin_messages(
        user=request.user,
        search=search or None,
        replied=replied,
    )

    stats = ContactService.get_message_stats()

    paginator = Paginator(messages_qs, 20)
    page = request.GET.get("page", 1)
    try:
        messages_page = paginator.page(page)
    except PageNotAnInteger:
        messages_page = paginator.page(1)
    except EmptyPage:
        messages_page = paginator.page(paginator.num_pages)

    context = {
        "messages": messages_page,
        "stats": stats,
        "search": search,
        "replied": replied_param,
        "page_title": "Contact Messages",
    }

    return render(request, "dashboard/messages/list.html", context)


@login_required
@admin_required
def contact_detail(request, contact_id):
    """View a single contact message with reply actions."""
    submission = ContactService.get_message_by_id(contact_id, user=request.user)
    if not submission:
        messages.error(request, "Contact message not found.")
        return redirect("dashboard:contact_list")

    context = {
        "submission": submission,
        "page_title": f"Message from {submission.name}",
    }
    return render(request, "dashboard/messages/detail.html", context)


@login_required
@admin_required
def contact_toggle_replied(request, contact_id):
    """Toggle replied status on a contact message."""
    submission = get_object_or_404(ContactSubmission, id=contact_id)

    if request.method == "POST":
        target_state = not submission.is_replied
        ContactService.mark_replied(request.user, submission, replied=target_state)
        if target_state:
            messages.success(request, f'Message from {submission.name} marked as replied.')
        else:
            messages.success(request, f'Message from {submission.name} marked as awaiting reply.')
    return redirect("dashboard:contact_detail", contact_id=submission.id)


@login_required
@admin_required
def contact_delete(request, contact_id):
    """Delete a contact message. POST-only for the destructive path."""
    submission = get_object_or_404(ContactSubmission, id=contact_id)

    if request.method == "POST":
        ContactService.delete_message(request.user, submission)
        messages.success(request, f'Message from {submission.name} deleted.')
        return redirect("dashboard:contact_list")

    context = {
        "submission": submission,
        "page_title": f"Delete Message from {submission.name}",
    }
    return render(request, "dashboard/messages/delete_confirm.html", context)
