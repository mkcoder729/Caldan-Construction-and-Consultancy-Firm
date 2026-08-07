"""Custom template tags and filters for the accounts app."""

from collections.abc import Mapping, Sequence

from django import template

register = template.Library()


@register.filter(name="get_item")
def get_item(value, key):
    """Return ``value[key]`` for a dict, or ``value[index]`` for a list/tuple.

    Returns ``None`` (or empty string for unknown types) when the lookup
    is invalid so ``|get_item:key|default:0`` degrades gracefully when
    a view forgets to pass the mapping in the context.

    Usage::

        {{ current_permissions|get_item:permission.key }}
    """
    if value is None:
        return None

    if isinstance(value, Mapping):
        return value.get(key, "")

    if isinstance(value, (list, tuple)) or isinstance(value, Sequence):
        try:
            return value[key]
        except (IndexError, TypeError, KeyError):
            return ""

    try:
        return value[key]
    except (TypeError, KeyError, IndexError):
        return ""
