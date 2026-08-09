"""Public URL routes for the Caldan Compassionate Ministry app."""

from django.urls import path

from compassion.views import (
    compassion_index,
    donate_page,
    donate_initiate,
    inkind_submit,
    schedule_call_submit,
    donation_thank_you,
    donation_status_json,
    donation_receipt_pdf,
    donation_verify,
    paystack_webhook,
    story_detail,
)

app_name = "compassion"

urlpatterns = [
    path("", compassion_index, name="index"),
    path("donate/", donate_page, name="donate"),
    path("donate/initiate/", donate_initiate, name="donate_initiate"),
    path("donate/verify/", donation_verify, name="donation_verify"),
    path("donate/thank-you/", donation_thank_you, name="thank_you"),
    path("donate/status/", donation_status_json, name="donation_status_json"),
    path("donate/receipt/", donation_receipt_pdf, name="donation_receipt_pdf"),
    path("inkind/submit/", inkind_submit, name="inkind_submit"),
    path("call/submit/", schedule_call_submit, name="schedule_call_submit"),
    path("paystack/webhook/", paystack_webhook, name="paystack_webhook"),
    path("stories/<slug:slug>/", story_detail, name="story_detail"),
]