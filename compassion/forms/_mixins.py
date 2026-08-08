"""Shared form helpers (Kenyan phone validation)."""

import re

from django import forms

# Kenyan phone number patterns — mirrors website/forms/quote_form.py:92-101
KENYAN_PHONE_PATTERNS = [
    r"^07\d{8}$",         # 0712345678
    r"^01\d{8}$",         # 0112345678
    r"^2547\d{8}$",       # 254712345678
    r"^2541\d{8}$",       # 254112345678
    r"^\+2547\d{8}$",     # +254712345678
    r"^\+2541\d{8}$",     # +254112345678
    r"^7\d{8}$",          # 712345678
    r"^1\d{8}$",          # 112345678
]


def clean_kenyan_phone(value: str) -> str:
    """Strip whitespace/separators and assert one of the 8 KE formats.

    Returns the cleaned digits (preserving a leading +).
    """
    cleaned = re.sub(r"[^\d+]", "", (value or "").strip())
    if not any(re.match(p, cleaned) for p in KENYAN_PHONE_PATTERNS):
        from django.core.exceptions import ValidationError
        raise ValidationError(
            "Please enter a valid Kenyan phone number (e.g., 0712345678 or +254712345678)."
        )
    return cleaned


def make_phone_field() -> forms.CharField:
    """Build the standard `phone` CharField used across compassion forms."""
    return forms.CharField(
        max_length=15,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "0712 345 678",
            "inputmode": "tel",
            "autocomplete": "tel",
        }),
        label="Phone number",
    )


def kenyan_phone_clean(form):
    """Stand-alone clean_phone method usable by any compassion form."""
    return clean_kenyan_phone(form.cleaned_data.get("phone", ""))


class KenyanPhoneMixin:
    """Backward-compatible shim.

    The mixin intentionally does NOT declare a `phone` field here — Django's
    DeclarativeFieldsMetaclass only inspects the class body's local attrs, so
    a mixin-level field declaration would be silently dropped. Instead, the
    helper `make_phone_field()` and `kenyan_phone_clean()` are imported
    directly into each form, which is explicit and immune to MRO surprises.
    """
