"""
Admin registrations for all compassion models.

We use the standard ModelAdmin with list_display / list_filter /
search_fields / raw_id_fields so the chief admin can manage everything
from /admin/compassion/. CRUD views in the dashboard (/dashboard/compassion/)
read from these same querysets via the service layer.
"""

from django.contrib import admin
from django.utils.html import format_html

from .models import (
    Donation,
    InKindDonation,
    MinistrySettings,
    OutreachStory,
    PaymentMethod,
    ScheduleCall,
)


# Helper to keep list_display readable
def _kes(obj):
    try:
        return f"KES {obj.amount_ksh:,.2f}"
    except Exception:
        return "—"
_kes.short_description = "Amount"


@admin.register(Donation)
class DonationAdmin(admin.ModelAdmin):
    list_display = ("reference", "donor_name", "donor_email", "purpose", _kes, "status", "created_at")
    list_filter = ("status", "purpose", "created_at")
    search_fields = ("reference", "paystack_reference", "donor_name", "donor_email", "donor_phone")
    readonly_fields = ("reference", "paystack_reference", "verified_at", "ip_address", "user_agent", "created_at", "updated_at")
    date_hierarchy = "created_at"
    ordering = ("-created_at",)
    list_select_related = ()


@admin.register(InKindDonation)
class InKindDonationAdmin(admin.ModelAdmin):
    list_display = ("donor_name", "item_type", "quantity_estimate", "delivery_mode", "status", "preferred_date", "created_at")
    list_filter = ("status", "item_type", "delivery_mode", "created_at")
    search_fields = ("donor_name", "donor_email", "donor_phone", "item_description")
    readonly_fields = ("ip_address", "user_agent", "created_at", "updated_at", "status_changed_at")
    date_hierarchy = "created_at"
    ordering = ("-created_at",)


@admin.register(ScheduleCall)
class ScheduleCallAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "topic", "preferred_time", "status", "created_at")
    list_filter = ("status", "topic", "created_at")
    search_fields = ("name", "email", "phone", "message")
    readonly_fields = ("ip_address", "user_agent", "created_at", "updated_at", "status_changed_at")
    date_hierarchy = "created_at"
    ordering = ("-created_at",)


@admin.register(OutreachStory)
class OutreachStoryAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "location", "event_date", "people_served", "is_published", "display_order")
    list_filter = ("is_published", "category", "event_date")
    search_fields = ("title", "slug", "location", "summary", "body")
    prepopulated_fields = {"slug": ("title",)}
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "event_date"
    ordering = ("display_order", "-event_date")


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ("label", "method", "account_number", "account_name", "bank_name", "is_active", "display_order")
    list_filter = ("is_active", "method")
    search_fields = ("label", "account_number", "account_name", "bank_name", "instructions")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("display_order", "method", "label")


@admin.register(MinistrySettings)
class MinistrySettingsAdmin(admin.ModelAdmin):
    """Singleton — block add/delete so admins can only edit the one row."""

    list_display = ("hero_title", "hero_cta_label", "contact_phone", "contact_email", "default_currency", "updated_at")
    readonly_fields = ("updated_at",)

    def has_add_permission(self, request):
        # Only one row ever exists; hide the +Add button.
        return not MinistrySettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
