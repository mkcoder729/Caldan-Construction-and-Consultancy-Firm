"""
Custom template filters for PDF templates.
"""
from django import template

register = template.Library()


@register.filter
def replace(value, args):
    """
    Replace characters in a string.

    Usage:
        {{ value|replace:"_, " }}     -> replace _ with space
    """
    if not value:
        return value

    # Split on the first separator: old, new
    if ',' in args:
        old, new = args.split(',', 1)
    else:
        old, new = args, ''
    return str(value).replace(old.strip(), new.strip())


@register.filter
def underscore_to_space(value):
    """Replace underscores with spaces."""
    return str(value).replace('_', ' ') if value else value


@register.filter
def truncate_chars(value, length):
    """Truncate a string to N characters, appending ellipsis if cut."""
    s = str(value)
    if len(s) > length:
        return s[:length] + '…'
    return s