"""
Custom template tags/filters for the compassion app.

Currently exposes a single filter `kes` that formats a number as
Kenyan Shillings (e.g. 1234.5 → "KSh 1,234.50"). The prefix is taken
from settings.CURRENCY_SYMBOL so the same filter respects a future
config change.

Usage: {% load compassion_tags %}{{ donation.amount_ksh|kes }}
"""

from decimal import Decimal, InvalidOperation

from django import template
from django.conf import settings

register = template.Library()


@register.filter(name="kes")
def kes(value):
    """Format a numeric value as 'KSh 1,234.50' using settings.CURRENCY_SYMBOL."""
    if value is None or value == "":
        return ""
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return value
    symbol = getattr(settings, "CURRENCY_SYMBOL", "KSh")
    # En-dash style: symbol, then space, then number with thousands sep
    return f"{symbol} {amount:,.2f}"


@register.filter(name="status_badge_class")
def status_badge_class(value):
    """Map a status string to a Bootstrap-ish CSS class for admin badges."""
    mapping = {
        "PENDING": "bg-warning text-dark",
        "SUCCESS": "bg-success",
        "FAILED": "bg-danger",
        "ABANDONED": "bg-secondary",
        "PLEDGED": "bg-info text-dark",
        "SCHEDULED": "bg-primary",
        "RECEIVED": "bg-success",
        "DELIVERED": "bg-success",
        "CANCELLED": "bg-secondary",
        "NEW": "bg-warning text-dark",
        "CONTACTED": "bg-primary",
        "COMPLETED": "bg-success",
    }
    return mapping.get(value, "bg-secondary")


@register.filter(name="split_paragraphs")
def split_paragraphs(value):
    """Split a long-form text block into <p>-ready paragraphs.

    The story body field is a plain-text block written by the admin;
    we treat blank lines as paragraph separators and return a list
    of stripped strings so the template can render:

        {% for p in story.body|split_paragraphs %}<p>{{ p }}</p>{% endfor %}

    Skips empty paragraphs and trims whitespace. Returns [] for
    None/empty input.
    """
    if not value:
        return []
    parts = []
    for chunk in str(value).replace("\r\n", "\n").split("\n\n"):
        cleaned = chunk.strip()
        if cleaned:
            parts.append(cleaned)
    return parts
