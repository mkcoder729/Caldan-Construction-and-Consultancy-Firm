"""Views for the Caldan Compassionate Ministry app.

Three layers:
  * `public`   — anonymous / donor-facing flows (/compassion/, modals)
  * `donations` — Paystack initiate / verify / webhook
  * `dashboard` — admin CRUD for donations, in-kind, calls, stories,
                  payment methods, and ministry settings
"""

from compassion.views.public import (
    compassion_index,
    donate_page,
    donate_initiate,
    inkind_submit,
    schedule_call_submit,
    donation_thank_you,
    story_detail,
)
from compassion.views.donations import (
    donation_verify,
    paystack_webhook,
)
from compassion.views.dashboard import (
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

__all__ = [
    "compassion_index",
    "donate_page",
    "donate_initiate",
    "inkind_submit",
    "schedule_call_submit",
    "donation_thank_you",
    "story_detail",
    "donation_verify",
    "paystack_webhook",
    "dashboard_overview",
    "donation_list",
    "donation_detail",
    "donation_advance",
    "inkind_list",
    "inkind_detail",
    "inkind_advance",
    "call_list",
    "call_detail",
    "call_advance",
    "story_list",
    "story_create",
    "story_edit",
    "payment_method_list",
    "payment_method_create",
    "payment_method_edit",
    "payment_method_toggle_active",
    "ministry_settings_edit",
]