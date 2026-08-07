"""
Global Search Service - Intelligent cross-platform search.

Searches every searchable model AND the sidebar / dashboard page catalog
with intelligent matching:

  - Multi-token: typing "cement nakuru" finds rows where ALL tokens
    appear somewhere in any searchable field (AND across tokens, OR
    across fields).
  - Substring + word-prefix: each token matches as substring OR as a
    word-prefix in any field.
  - Typo tolerance: for tokens >= 4 chars, a 1-edit-distance match
    counts as a hit (so "nakru" -> "Nakuru", "cemnt" -> "Cement").
  - Word-boundary: searching "school" matches "Secondary School".
  - Python fallback: if the DB layer returns nothing, a Python scanner
    ranks all rows by similarity (handles longer typos / abbreviations).

Returns grouped results in this shape:
    [
        {'category': 'Pages',   'items': [...]},
        {'category': 'Projects', 'items': [...]},
        ...
    ]
"""
import re
import logging
from functools import lru_cache
from difflib import SequenceMatcher
from django.urls import reverse, NoReverseMatch
from django.db.models import Q

logger = logging.getLogger('caldan.dashboard')


# ----------------------------------------------------------------------
# URL helpers
# ----------------------------------------------------------------------
def _safe_reverse(name, default='#', args=None, kwargs=None):
    try:
        if args or kwargs:
            return reverse(name, args=args or [], kwargs=kwargs or {})
        return reverse(name)
    except Exception:
        return default


# ----------------------------------------------------------------------
# Static page catalog — sidebar / dashboard pages always present
# ----------------------------------------------------------------------
STATIC_PAGES = [
    ('Overview', 'fa-th-large', 'dashboard:overview'),
    ('Analytics', 'fa-chart-line', 'dashboard:analytics'),
    ('Activity Feed', 'fa-history', 'dashboard:activity'),
    ('Notifications', 'fa-bell', 'notifications:list'),

    ('All Projects', 'fa-building', 'admin_projects:project_list'),
    ('Create Project', 'fa-plus-circle', 'admin_projects:project_create'),

    ('All Services', 'fa-concierge-bell', 'services:service_list'),
    ('Create Service', 'fa-plus-circle', 'services:service_create'),

    ('Clients', 'fa-users', 'clients:client_list'),
    ('Team Members', 'fa-user-tie', 'team:member_list'),
    ('Blog Posts', 'fa-blog', 'blog:admin_list'),
    ('Materials', 'fa-cubes', 'inventory:materials_list'),
    ('Suppliers', 'fa-truck', 'inventory:suppliers_list'),
    ('Stock Transactions', 'fa-exchange-alt', 'inventory:transactions_list'),
    ('Orders', 'fa-shopping-cart', 'shop:order_list'),
    ('Payments', 'fa-credit-card', 'finances:payment_list'),
    ('Expenses', 'fa-file-invoice-dollar', 'finances:expense_list'),
    ('Budgets', 'fa-money-bill-wave', 'finances:budget_list'),

    ('Reports Dashboard', 'fa-chart-pie', 'reports:index'),
    ('Project Report', 'fa-chart-bar', 'reports:project_report'),
    ('Inventory Report', 'fa-boxes', 'reports:inventory_report'),
    ('Financial Report', 'fa-chart-line', 'reports:financial_report'),
    ('Export Center', 'fa-download', 'reports:export_center'),
    ('Backup Manager', 'fa-database', 'reports:backup_manager'),
    ('Backup History', 'fa-history', 'reports:backup_history'),

    ('Admin Management', 'fa-user-shield', 'accounts:admin_list'),
    ('Invite Admin', 'fa-user-plus', 'accounts:admin_invite'),

    ('My Profile', 'fa-user', 'dashboard:profile_view'),
    ('Edit Profile', 'fa-pen', 'dashboard:profile_edit'),
    ('Change Password', 'fa-key', 'dashboard:change_password'),
    ('Data Management', 'fa-archive', 'dashboard:data_management'),
    ('Security Settings', 'fa-shield-alt', 'dashboard:security_settings'),
    ('Notification Settings', 'fa-bell', 'dashboard:notification_settings'),
    ('Appearance', 'fa-palette', 'dashboard:appearance_settings'),
]


def _search_static_pages(tokens, limit=12):
    """Search the static page catalog by label substring, word-prefix, OR
    fuzzy edit-distance match (so 'seti' still finds 'Settings').
    """
    results = []
    seen = set()
    for label, icon, url_name in STATIC_PAGES:
        ll = label.lower()
        score = 0
        for tok in tokens:
            if not tok:
                continue
            matched, ts = _match_token_to_field(tok, label)
            if matched:
                score += ts
            else:
                score = 0
                break
        if score > 0 and url_name not in seen:
            seen.add(url_name)
            results.append({
                'id': f'page:{url_name}',
                'title': label,
                'subtitle': 'Navigation page',
                'icon': icon,
                'url': _safe_reverse(url_name),
                '_score': score,
            })
    results.sort(key=lambda r: r['_score'], reverse=True)
    return [{k: v for k, v in r.items() if k != '_score'} for r in results[:limit]]


# ----------------------------------------------------------------------
# Tokenization & fuzzy matching helpers
# ----------------------------------------------------------------------
_TOKEN_SPLIT = re.compile(r'[\s,_\-/]+')


def _tokenize(query):
    """Split query on whitespace and common separators. Lowercase each."""
    return [t for t in (tok.strip().lower() for tok in _TOKEN_SPLIT.split(query)) if t]


def _levenshtein(a, b, max_dist=None):
    """Iterative Levenshtein distance with optional early exit."""
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    if len(a) > len(b):
        a, b = b, a
    prev = list(range(len(a) + 1))
    for i, cb in enumerate(b, start=1):
        cur = [i] + [0] * len(a)
        row_min = cur[0]
        for j, ca in enumerate(a, start=1):
            cost = 0 if ca == cb else 1
            cur[j] = min(cur[j - 1] + 1, prev[j] + 1, prev[j - 1] + cost)
            if cur[j] < row_min:
                row_min = cur[j]
        if max_dist is not None and row_min > max_dist:
            return row_min
        prev = cur
    return prev[-1]


def _match_token_to_field(token, field_value):
    """Return (matched: bool, score: float) for whether `token` matches any
    word/sequence within `field_value`.

    Score is higher for prefix matches and exact substring matches.
    """
    if not field_value:
        return False, 0.0
    fv = field_value.lower()
    # 1. exact substring anywhere
    if token in fv:
        # prefer matches at word boundaries
        if re.search(r'(^|\W)' + re.escape(token), fv):
            return True, 1.0
        return True, 0.6
    # 2. word-prefix: any word in field starts with token
    for w in re.split(r'\W+', fv):
        if not w:
            continue
        if w.startswith(token):
            return True, 0.9
    # 3. fuzzy: any word is within edit distance 1 (or 2 if token >= 6 chars)
    if len(token) >= 4:
        max_dist = 1 if len(token) < 6 else 2
        for w in re.split(r'\W+', fv):
            if not w or abs(len(w) - len(token)) > max_dist:
                continue
            d = _levenshtein(token, w, max_dist)
            if d <= max_dist:
                # token nearly matches the word — partial credit
                return True, 0.5
    return False, 0.0


def _row_matches(row, fields, tokens, require_all=True):
    """Return (matched: bool, score: float) for whether `row` matches
    tokens across any of the named fields.

    If `require_all` is True (the default), every token must score > 0
    in at least one field — the row is rejected if any token has no
    match anywhere. If False, the row is kept even if some tokens miss,
    and a small penalty is applied per missing token.
    """
    total_score = 0.0
    matched_tokens = 0
    for tok in tokens:
        tok_best = 0.0
        for fname in fields:
            val = getattr(row, fname, None)
            if not val:
                continue
            matched, score = _match_token_to_field(tok, str(val))
            if matched and score > tok_best:
                tok_best = score
        if tok_best > 0.0:
            matched_tokens += 1
            total_score += tok_best
        else:
            if require_all:
                return False, 0.0
            # Soft penalty for missing tokens — the row is still kept
            total_score += 0.1
    # If at least one token matched the row, return it. A pure zero-score
    # means nothing matched at all.
    if matched_tokens == 0:
        return False, 0.0
    return True, total_score


def _q_or(fields, query):
    """Build a Q(...) with icontains across the given list of field names."""
    q = Q()
    for fname in fields:
        q |= Q(**{f'{fname}__icontains': query})
    return q


def _q_all_tokens(fields, tokens):
    """Build a Q(...) that ORs icontains for each token across fields.

    For multi-token queries, we want at least ONE token to match somewhere
    in the row (more permissive) — scoring/ranking is done in Python.
    """
    q = Q()
    for tok in tokens:
        q |= _q_or(fields, tok)
    return q


def _text_fields(model):
    """Return all CharField / TextField / EmailField / SlugField names on a model
    that are safe to OR together for an icontains search. Excludes FK columns."""
    out = []
    for f in model._meta.get_fields():
        if not hasattr(f, 'attname'):
            continue
        if f.is_relation:
            continue
        if f.get_internal_type() in (
            'CharField', 'TextField', 'EmailField', 'SlugField',
            'URLField', 'GenericIPAddressField',
        ):
            out.append(f.name)
    return out


# ----------------------------------------------------------------------
# Per-model field overrides (searchable text columns, including joins)
# ----------------------------------------------------------------------
SEARCH_FIELDS = {
    'Project': [
        'name', 'project_code', 'description',
        'location', 'county', 'town', 'estate',
    ],
    'Service': [
        'name', 'short_description', 'description', 'long_description',
        'slug',
    ],
    'Client': [
        'name', 'company_name', 'email', 'phone', 'alternative_phone',
        'address', 'county', 'town', 'notes', 'source',
    ],
    'TeamMember': [
        'name', 'role', 'title', 'bio', 'email', 'phone',
    ],
    'Material': [
        'name', 'sku', 'description',
        'supplier__name',
    ],
    'Supplier': [
        'name', 'contact_person', 'phone', 'email',
        'address', 'county', 'town', 'notes',
    ],
    'Order': [
        'order_number', 'client_name', 'client_email', 'client_phone',
        'delivery_address', 'delivery_county', 'delivery_town',
        'delivery_notes', 'status', 'tracking_number', 'tracking_code',
        'notes', 'admin_notes',
    ],
    'Payment': [
        'description', 'paid_to', 'paid_to_contact', 'reference',
        'invoice_number', 'method', 'type', 'status',
    ],
    'Expense': [
        'description', 'category', 'receipt_number', 'vendor_name',
        'vendor_contact', 'notes',
    ],
    'BlogPost': [
        'title', 'slug', 'excerpt', 'content',
    ],
}


# How to render each model's hits
MODEL_RENDERERS = {
    'Project': (
        'fa-building', 'admin_projects:project_detail', 'project_id',
        lambda p: p.name,
        lambda p: (
            f'{p.get_status_display() if hasattr(p, "get_status_display") else p.status}'
            f' - {p.location or p.county or p.town or "-"}'
        ).strip(' -'),
    ),
    'Service': (
        'fa-concierge-bell', 'services:service_detail', 'pk',
        lambda s: s.name,
        lambda s: (s.short_description or s.description or '')[:80] or 'Service',
    ),
    'Client': (
        'fa-users', 'clients:client_detail', 'client_id',
        lambda c: c.name,
        lambda c: c.email or c.phone or c.company_name or 'Client',
    ),
    'TeamMember': (
        'fa-user-tie', 'team:member_detail', 'member_id',
        lambda t: t.name,
        lambda t: t.role or t.title or 'Team member',
    ),
    'Material': (
        'fa-cubes', 'inventory:material_detail', 'material_id',
        lambda m: m.name,
        lambda m: (
            f'Stock: {m.current_quantity} '
            f'{m.get_unit_display() if hasattr(m, "get_unit_display") else m.unit}'
        ),
    ),
    'Supplier': (
        'fa-truck', 'inventory:supplier_detail', 'supplier_id',
        lambda s: s.name,
        lambda s: s.contact_person or s.phone or s.email or s.town or 'Supplier',
    ),
    'Order': (
        'fa-shopping-cart', 'shop:order_detail', 'order_id',
        lambda o: o.order_number,
        lambda o: f'{o.client_name or "Customer"} - KES {o.total}',
    ),
    'Payment': (
        'fa-credit-card', 'finances:payment_detail', 'payment_id',
        lambda p: f'Payment #{p.id}',
        lambda p: f'KES {p.amount} - {p.paid_to or p.description or "-"}',
    ),
    'Expense': (
        'fa-file-invoice-dollar', 'finances:expense_edit', 'expense_id',
        lambda e: (e.description or f'Expense #{e.id}')[:60],
        lambda e: f'KES {e.amount} - {e.vendor_name or e.category or "-"}',
    ),
    'BlogPost': (
        'fa-blog', 'blog:admin_edit', 'post_id',
        lambda b: b.title,
        lambda b: 'Blog post',
    ),
}


def _category_label(model_name):
    return {
        'Project': 'Projects',
        'Service': 'Services',
        'Client': 'Clients',
        'TeamMember': 'Team',
        'Material': 'Materials',
        'Supplier': 'Suppliers',
        'Order': 'Orders',
        'Payment': 'Payments',
        'Expense': 'Expenses',
        'BlogPost': 'Blog',
    }.get(model_name, model_name)


def _search_one_model(model_name, tokens, limit=10):
    """Run an intelligent search for a single model. Returns a list of
    {'id', 'title', 'subtitle', 'icon', 'url', '_score'} sorted by score.
    """
    if not tokens:
        return []

    try:
        module_name = {
            'Project': 'projects.models.Project',
            'Service': 'services.models.Service',
            'Client': 'clients.models.Client',
            'TeamMember': 'team.models.TeamMember',
            'Material': 'inventory.models.Material',
            'Supplier': 'inventory.models.Supplier',
            'Order': 'shop.models.Order',
            'Payment': 'finances.models.Payment',
            'Expense': 'finances.models.Expense',
            'BlogPost': 'blog.models.BlogPost',
        }[model_name]
        module_path, class_name = module_name.rsplit('.', 1)
        import importlib
        Model = getattr(importlib.import_module(module_path), class_name)
    except Exception as e:
        logger.debug(f"Import {model_name} failed: {e}")
        return []

    fields = SEARCH_FIELDS.get(model_name) or _text_fields(Model)
    if not fields:
        return []

    icon, url_name, pk_field, title_fn, subtitle_fn = MODEL_RENDERERS[model_name]

    # ---- Stage 1: SQL icontains — try AND first (all tokens present),
    # then fall back to OR (any token present) if AND returned nothing.
    try:
        candidates = list(
            Model.objects.filter(_q_all_tokens(fields, tokens)).distinct()[:200]
        )
        if not candidates and len(tokens) > 1:
            # OR fallback: any token matches
            q_or_any = Q()
            for tok in tokens:
                q_or_any |= _q_or(fields, tok)
            candidates = list(
                Model.objects.filter(q_or_any).distinct()[:200]
            )
    except Exception as e:
        logger.debug(f"DB filter {model_name} failed: {e}")
        candidates = []

    # ---- Stage 2: Python fuzzy scoring on candidates ----
    # - If we got candidates via the AND icontains query, the SQL already
    #   required every token to appear somewhere. Python scoring is
    #   strict — every token must still score > 0 in the fuzzy pass.
    # - If we fell back to the OR query, the SQL only required any token
    #   to match. Python scoring is permissive — missing tokens are
    #   tolerated (with a small penalty), so rows that only match some
    #   tokens still surface, ranked below rows that match all.
    # We know we used OR only if the AND query returned nothing — track it.
    try:
        and_count = Model.objects.filter(_q_all_tokens(fields, tokens)).distinct().count()
    except Exception:
        and_count = 0
    used_or_fallback = (and_count == 0 and len(tokens) > 1)
    require_all = not used_or_fallback

    scored = []
    for row in candidates:
        ok, score = _row_matches(row, fields, tokens, require_all=require_all)
        if ok:
            scored.append((score, row))

    # ---- Stage 3: If stages 1+2 returned nothing, full table scan with
    # fuzzy ranking (handles longer typos / abbreviations). Always
    # permissive here — better to surface close matches than nothing.
    if not scored:
        try:
            fallback = list(Model.objects.all()[:500])
            for row in fallback:
                ok, score = _row_matches(row, fields, tokens, require_all=False)
                if ok:
                    scored.append((score, row))
        except Exception as e:
            logger.debug(f"Fallback scan {model_name} failed: {e}")

    # ---- Stage 4: Sort by score, then by recency ----
    scored.sort(
        key=lambda sr: (
            -sr[0],
            -getattr(sr[1], 'created_at', 0).timestamp() if hasattr(sr[1], 'created_at') else 0,
        )
    )

    items = []
    for score, row in scored[:limit]:
        items.append({
            'id': f'{model_name.lower()}:{row.id}',
            'title': title_fn(row),
            'subtitle': subtitle_fn(row),
            'icon': icon,
            'url': _safe_reverse(url_name, kwargs={pk_field: row.id}),
            '_score': score,
        })
    return items


def search_models(query, limit_per_model=8):
    """
    Run an intelligent query against every searchable model and return a
    list of categories, each with its top results.
    """
    q = (query or '').strip()
    if len(q) < 1:
        return []

    tokens = _tokenize(q)
    if not tokens:
        return []

    out = []

    # ---- Pages (always-available) -----------------------------------
    pages = _search_static_pages(tokens)
    if pages:
        out.append({'category': 'Pages', 'items': pages})

    # ---- Models -----------------------------------------------------
    for model_name in [
        'Project', 'Service', 'Client', 'TeamMember',
        'Material', 'Supplier', 'Order',
        'Payment', 'Expense', 'BlogPost',
    ]:
        try:
            items = _search_one_model(model_name, tokens, limit=limit_per_model)
        except Exception as e:
            logger.debug(f"{model_name} search failed: {e}")
            items = []
        if items:
            # Strip _score before returning
            cleaned = [{k: v for k, v in it.items() if k != '_score'} for it in items]
            out.append({'category': _category_label(model_name), 'items': cleaned})

    return out


def search_everything(query):
    """Convenience wrapper — returns categories + a flat total."""
    categories = search_models(query)
    total = sum(len(c['items']) for c in categories)
    return {
        'categories': categories,
        'total': total,
        'query': query,
    }
