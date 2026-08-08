"""Dashboard URL routes for Caldan Compassionate Ministry."""

from django.urls import path

from compassion.views import (
    dashboard_overview,
    donation_list,
    donation_detail,
    donation_advance,
    inkind_list,
    inkind_detail,
    inkind_advance,
    call_list,
    call_detail,
    call_advance,
    story_list,
    story_create,
    story_edit,
    payment_method_list,
    payment_method_create,
    payment_method_edit,
    payment_method_toggle_active,
    ministry_settings_edit,
)

app_name = "compassion_dashboard"

urlpatterns = [
    path("", dashboard_overview, name="overview"),

    # Donations
    path("donations/", donation_list, name="donation_list"),
    path("donations/<int:donation_id>/", donation_detail, name="donation_detail"),
    path("donations/<int:donation_id>/advance/", donation_advance, name="donation_advance"),

    # In-kind pledges
    path("inkind/", inkind_list, name="inkind_list"),
    path("inkind/<int:pledge_id>/", inkind_detail, name="inkind_detail"),
    path("inkind/<int:pledge_id>/advance/", inkind_advance, name="inkind_advance"),

    # Schedule calls
    path("calls/", call_list, name="call_list"),
    path("calls/<int:call_id>/", call_detail, name="call_detail"),
    path("calls/<int:call_id>/advance/", call_advance, name="call_advance"),

    # Outreach stories
    path("stories/", story_list, name="story_list"),
    path("stories/new/", story_create, name="story_create"),
    path("stories/<int:story_id>/edit/", story_edit, name="story_edit"),

    # Payment methods
    path("payment-methods/", payment_method_list, name="payment_method_list"),
    path("payment-methods/new/", payment_method_create, name="payment_method_create"),
    path("payment-methods/<int:method_id>/edit/", payment_method_edit, name="payment_method_edit"),
    path("payment-methods/<int:method_id>/toggle/", payment_method_toggle_active, name="payment_method_toggle"),

    # Ministry settings
    path("settings/", ministry_settings_edit, name="ministry_settings_edit"),
]