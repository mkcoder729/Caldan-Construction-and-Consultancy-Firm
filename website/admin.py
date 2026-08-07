from django.contrib import admin
from django.utils.html import format_html
from .models.contact import ContactSubmission
from .models.quote import QuoteRequest
from .models.newsletter import NewsletterSubscriber


@admin.register(ContactSubmission)
class ContactSubmissionAdmin(admin.ModelAdmin):
    """Admin interface for contact form submissions."""

    list_display = ("name", "email", "phone", "subject", "created_at", "is_replied")
    list_filter = ("is_replied", "created_at")
    search_fields = ("name", "email", "phone", "subject", "message")
    readonly_fields = ("created_at",)
    ordering = ("-created_at",)

    fieldsets = (
        ("Sender Information", {
            "fields": ("name", "email", "phone")
        }),
        ("Message", {
            "fields": ("subject", "message")
        }),
        ("Status", {
            "fields": ("is_replied", "created_at")
        }),
    )

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return self.readonly_fields + ("name", "email", "phone", "subject", "message")
        return self.readonly_fields


@admin.register(QuoteRequest)
class QuoteRequestAdmin(admin.ModelAdmin):
    """Admin interface for quote request submissions."""

    list_display = ("name", "email", "phone", "project_type", "budget_range", "created_at", "is_replied")
    list_filter = ("project_type", "budget_range", "is_replied", "created_at")
    search_fields = ("name", "email", "phone", "project_type", "details")
    readonly_fields = ("created_at",)
    ordering = ("-created_at",)

    fieldsets = (
        ("Client Information", {
            "fields": ("name", "email", "phone")
        }),
        ("Project Details", {
            "fields": ("project_type", "budget_range", "timeline", "details")
        }),
        ("Status", {
            "fields": ("is_replied", "created_at")
        }),
    )

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return self.readonly_fields + ("name", "email", "phone", "project_type", "budget_range", "timeline",
                                           "details")
        return self.readonly_fields


@admin.register(NewsletterSubscriber)
class NewsletterSubscriberAdmin(admin.ModelAdmin):
    """Admin interface for newsletter subscribers."""

    list_display = ("email", "is_active", "subscribed_at", "unsubscribed_at")
    list_filter = ("is_active", "subscribed_at")
    search_fields = ("email",)
    readonly_fields = ("subscribed_at", "unsubscribed_at")
    ordering = ("-subscribed_at",)
    actions = ["export_as_csv", "bulk_activate", "bulk_deactivate"]

    fieldsets = (
        ("Subscriber Information", {
            "fields": ("email", "is_active")
        }),
        ("Timestamps", {
            "fields": ("subscribed_at", "unsubscribed_at"),
            "classes": ("collapse",)
        }),
    )

    def export_as_csv(self, request, queryset):
        """Export selected subscribers as CSV."""
        import csv
        from django.http import HttpResponse

        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="newsletter_subscribers.csv"'

        writer = csv.writer(response)
        writer.writerow(["Email", "Active", "Subscribed At", "Unsubscribed At"])

        for subscriber in queryset:
            writer.writerow([
                subscriber.email,
                "Yes" if subscriber.is_active else "No",
                subscriber.subscribed_at.strftime("%Y-%m-%d %H:%M") if subscriber.subscribed_at else "",
                subscriber.unsubscribed_at.strftime("%Y-%m-%d %H:%M") if subscriber.unsubscribed_at else "",
            ])

        return response

    export_as_csv.short_description = "Export selected subscribers to CSV"

    def bulk_activate(self, request, queryset):
        """Bulk activate selected subscribers."""
        updated = queryset.update(is_active=True)
        self.message_user(request, f"{updated} subscribers activated.")

    bulk_activate.short_description = "Activate selected subscribers"

    def bulk_deactivate(self, request, queryset):
        """Bulk deactivate selected subscribers."""
        updated = queryset.update(is_active=False)
        self.message_user(request, f"{updated} subscribers deactivated.")

    bulk_deactivate.short_description = "Deactivate selected subscribers"