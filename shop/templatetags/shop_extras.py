"""
Custom template filters and tags for Shop app.
Caldan Construction - "Building Kenya's Future, One Project at a Time."
"""

from decimal import Decimal

from django import template
from django.utils.html import format_html

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """
    Get an item from a dictionary by key.
    Usage: {{ category_counts|get_item:cat.0 }}
    """
    if dictionary is None:
        return 0
    return dictionary.get(key, 0)


@register.filter
def multiply(value, arg):
    """
    Multiply two numbers.
    Usage: {{ price|multiply:quantity }}
    """
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0


@register.filter
def subtract(value, arg):
    """
    Subtract arg from value.
    Usage: {{ total|subtract:discount }}
    """
    try:
        return float(value) - float(arg)
    except (ValueError, TypeError):
        return 0


@register.filter
def divide(value, arg):
    """
    Divide value by arg.
    Usage: {{ total|divide:count }}
    """
    try:
        if float(arg) == 0:
            return 0
        return float(value) / float(arg)
    except (ValueError, TypeError):
        return 0


@register.filter
def currency_format(value):
    """
    Format a number as Kenyan Shillings (KES).
    Usage: {{ price|currency_format }}
    """
    try:
        return f"KES {float(value):,.2f}"
    except (ValueError, TypeError):
        return "KES 0.00"


@register.filter
def status_badge_class(status):
    """
    Get CSS class for order status badge.
    Usage: {{ order.status|status_badge_class }}
    """
    classes = {
        'PENDING': 'badge-warning',
        'PAID': 'badge-info',
        'PROCESSING': 'badge-primary',
        'SHIPPED': 'badge-info',
        'DELIVERED': 'badge-success',
        'COMPLETED': 'badge-success',
        'CANCELLED': 'badge-danger',
    }
    return classes.get(status, 'badge-secondary')


@register.filter
def status_display_class(status):
    """
    Get CSS class for order status display (darker, more prominent).
    Usage: {{ order.status|status_display_class }}
    """
    classes = {
        'PENDING': 'status-pending',
        'PAID': 'status-paid',
        'PROCESSING': 'status-processing',
        'SHIPPED': 'status-shipped',
        'DELIVERED': 'status-delivered',
        'COMPLETED': 'status-completed',
        'CANCELLED': 'status-cancelled',
    }
    return classes.get(status, '')


@register.filter
def stock_status_class(product):
    """
    Get CSS class for product stock status.
    Usage: {{ product|stock_status_class }}
    """
    if not product.in_stock or product.stock_quantity <= 0:
        return 'stock-out'
    elif product.is_low_stock:
        return 'stock-low'
    return 'stock-in'


@register.filter
def status_color(status):
    """
    Get hex color for order status.
    Usage: {{ order.status|status_color }}
    """
    colors = {
        'PENDING': '#D4AF37',
        'PAID': '#0B66C3',
        'PROCESSING': '#8E44AD',
        'SHIPPED': '#2980B9',
        'DELIVERED': '#27AE60',
        'COMPLETED': '#1ABC9C',
        'CANCELLED': '#B9342B',
    }
    return colors.get(status, '#95A5A6')


@register.simple_tag
def order_status_label(status):
    """
    Get human-readable order status label.
    Usage: {% order_status_label order.status %}
    """
    labels = {
        'PENDING': 'Pending Payment',
        'PAID': 'Paid',
        'PROCESSING': 'Processing',
        'SHIPPED': 'Shipped',
        'DELIVERED': 'Delivered',
        'COMPLETED': 'Completed',
        'CANCELLED': 'Cancelled',
    }
    return labels.get(status, status)


@register.filter
def truncate_words(value, num_words):
    """
    Truncate text to a specified number of words.
    Usage: {{ description|truncate_words:20 }}
    """
    if not value:
        return ''
    try:
        words = str(value).split()
        if len(words) <= int(num_words):
            return str(value)
        return ' '.join(words[:int(num_words)]) + '...'
    except (ValueError, TypeError):
        return str(value)