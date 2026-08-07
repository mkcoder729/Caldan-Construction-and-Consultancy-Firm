"""Dashboard template filters and helpers."""

from django import template

register = template.Library()


@register.filter
def url_name(value):
    """Strip namespace from a namespaced URL name.

    Example:
        'admin_projects:project_list' -> 'project_list'
        'dashboard:overview'          -> 'overview'
        'project_list'                -> 'project_list'
    """
    if not value:
        return ''
    return value.split(':', 1)[-1]


@register.simple_tag
def nav_active(item_url, current_view):
    """Return 'active' if `item_url` matches the resolved request view.

    `current_view` is the request's `resolver_match` (not just the URL
    name string). We compare the sidebar item's URL against the fully-
    qualified namespace:url_name so that, e.g., `blog:admin_list` and
    `accounts:admin_list` light up on different pages — not both.

    Bare URL names like `'project_list'` still match correctly: Django's
    URL resolver returns `''` for the namespace in that case, and we
    fall back to comparing just the URL name.
    """
    if not item_url:
        return ''
    # `current_view` may be a resolver_match object, a 2-tuple
    # (namespace, url_name), or just a string (legacy). Handle all.
    cur_namespace = ''
    cur_url_name = ''
    if current_view is None:
        return ''
    if isinstance(current_view, str):
        cur_url_name = current_view
    else:
        # resolver_match — has .namespace and .url_name
        cur_namespace = getattr(current_view, 'namespace', '') or ''
        cur_url_name = getattr(current_view, 'url_name', '') or ''

    item_namespace, _, item_name = item_url.rpartition(':')
    if not item_name:
        # No namespace prefix on the sidebar item — fall back to bare name.
        return 'active' if item_url == cur_url_name else ''

    # Sidebar item has a namespace. Match the fully-qualified name only.
    return 'active' if (item_namespace == cur_namespace and item_name == cur_url_name) else ''


@register.simple_tag
def nav_active_item(item, current_view):
    """Like nav_active but takes the full item dict — header items
    never light up since they have no URL.
    """
    if not item or item.get('type') == 'header':
        return ''
    return nav_active(item.get('url', ''), current_view)


@register.simple_tag
def sidebar_url(item):
    """Resolve a sidebar item's URL, passing any kwargs the URL needs.

    `item` is a dict with `url` (a Django URL name) and optional
    `project_id`, `material_id`, `client_id`, `member_id`, `service_id`,
    `payment_id`, `supplier_id`, `order_id`, `admin_id`, or `post_id`.
    The first kwarg found is passed to `{% url %}`. Items without any
    kwarg render with no args. Header items (`type == 'header'`) return '#'.

    Sentinel kwargs (`'__latest__'`, `'__first__'`) are resolved to a
    real ID at render time, so sidebar "Detail" links always point at
    a record that exists instead of a hardcoded id that may have been
    deleted. If the lookup returns nothing, the link falls back to the
    list view so it never 404s.
    """
    if item.get('type') == 'header':
        return '#'
    if not item.get('url'):
        return '#'
    kwarg_keys = (
        'project_id', 'material_id', 'product_id', 'client_id', 'member_id',
        'service_id', 'payment_id', 'supplier_id', 'order_id', 'admin_id',
        'post_id', 'quote_id', 'contact_id',
    )
    for key in kwarg_keys:
        if key in item and item[key] is not None:
            value = item[key]
            # Resolve dynamic sentinels to a real pk. If no record
            # exists, fall back to the list URL so the sidebar link
            # never 404s.
            if isinstance(value, str) and value in ('__latest__', '__first__'):
                real_id = _resolve_dynamic_id(key, value)
                if real_id is None:
                    return _fallback_list_url(item['url'])
                value = real_id
            try:
                from django.urls import reverse
                return reverse(item['url'], kwargs={key: value})
            except Exception:
                return '#'
    try:
        from django.urls import reverse
        return reverse(item['url'])
    except Exception:
        return '#'


def _resolve_dynamic_id(key, sentinel):
    """Look up a real primary key for a '__latest__' / '__first__'
    sidebar placeholder.

    Returns the pk (int) or None when no record exists. Each entity
    is mapped to its model + ordering; unknown keys return None.
    """
    mapping = {
        'project_id':  ('projects.Project',          '-created_at'),
        'material_id': ('inventory.Material',         '-created_at'),
        'product_id':  ('shop.Product',              '-created_at'),
        'client_id':   ('clients.Client',            '-created_at'),
        'member_id':   ('accounts.User',             '-date_joined'),
        'service_id':  ('services.Service',          '-created_at'),
        'payment_id':  ('finances.Payment',          '-created_at'),
        'supplier_id': ('inventory.Supplier',        '-created_at'),
        'order_id':    ('shop.Order',                '-created_at'),
        'admin_id':    ('accounts.User',             '-date_joined'),
        'post_id':     ('blog.BlogPost',             '-created_at'),
        'quote_id':    ('quotes.Quote',              '-created_at'),
        'contact_id':  ('website.ContactSubmission', '-created_at'),
    }
    spec = mapping.get(key)
    if not spec:
        return None
    model_path, ordering = spec
    try:
        app_label, model_name = model_path.split('.', 1)
        from django.apps import apps
        Model = apps.get_model(app_label, model_name)
        qs = Model._default_manager.all().order_by(ordering)
        obj = qs.first() if sentinel == '__latest__' else qs.last()
        return obj.pk if obj else None
    except Exception:
        # Model doesn't exist (e.g. app not installed), lookup failed,
        # or some other lookup error. Return None so the caller can
        # fall back gracefully.
        return None


def _fallback_list_url(url_name):
    """When a sidebar Detail placeholder can't resolve (no records),
    point the link at the matching list view so the user lands on a
    real page instead of a 404. The mapping is best-effort: any
    unknown URL falls through to '#'.
    """
    fallback_map = {
        'dashboard:contact_detail':    'dashboard:contact_list',
        'dashboard:project_detail':    'admin_projects:project_list',
        'dashboard:material_detail':   'dashboard:material_list',
        'dashboard:product_detail':    'shop:product_list',
        'dashboard:client_detail':     'clients:client_list',
        'dashboard:member_detail':     'accounts:member_list',
        'dashboard:service_detail':    'services:service_list',
        'dashboard:payment_detail':    'finances:payment_list',
        'dashboard:supplier_detail':   'dashboard:supplier_list',
        'dashboard:order_detail':      'shop:order_list',
        'dashboard:admin_detail':      'accounts:admin_list',
        'dashboard:post_detail':       'blog:admin_list',
        'dashboard:quote_detail':      'dashboard:quote_list',
    }
    target = fallback_map.get(url_name)
    if not target:
        return '#'
    try:
        from django.urls import reverse
        return reverse(target)
    except Exception:
        return '#'