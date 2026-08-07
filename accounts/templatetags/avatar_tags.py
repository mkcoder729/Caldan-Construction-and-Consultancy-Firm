"""
Reusable template tags for rendering user avatars.
The {% user_avatar %} tag returns the full <img> markup (or initial-letter
fallback) so the same look-and-feel is shared by every template.
"""
from django import template
from django.utils.safestring import mark_safe

register = template.Library()


def _initial_for(user):
    name = (user.full_name or user.email or '?').strip()
    return name[0].upper()


@register.simple_tag
def user_avatar(user, size=40, css_class='avatar', style=''):
    """
    Render a user avatar. If the user has uploaded one, returns
    an <img>; otherwise returns the initial-letter tile.

    Usage:
        {% load avatar_tags %}
        {% user_avatar request.user size=40 css_class='avatar-md' %}
    """
    if not user:
        return ''

    avatar = None
    url = None
    try:
        avatar = getattr(user, 'avatar', None)
        if avatar:
            url = avatar.url
            # Cloudinary supports resizing via query params
            if 'res.cloudinary.com' in url:
                # Insert a width transformation
                url = url.replace('/upload/', f'/upload/w_{size},h_{size},c_fill,q_auto,f_auto/')
    except Exception:
        url = None

    initial = _initial_for(user)
    inline_style = style if style else f"width:{size}px;height:{size}px;"

    if url:
        html = (
            f'<span class="{css_class} avatar-img" style="{inline_style}">'
            f'<img src="{url}" alt="{user.full_name or user.email}" loading="lazy" />'
            f'</span>'
        )
    else:
        html = (
            f'<span class="{css_class} avatar-initial" style="{inline_style}">'
            f'{initial}'
            f'</span>'
        )
    return mark_safe(html)


@register.filter
def user_avatar_url(user):
    """Return just the URL (or empty string) for advanced templates."""
    if not user:
        return ''
    avatar = getattr(user, 'avatar', None)
    try:
        if avatar:
            return avatar.url
    except Exception:
        return ''
    return ''


@register.filter
def user_avatar_initial(user):
    """Return the initial letter fallback."""
    if not user:
        return '?'
    return _initial_for(user)