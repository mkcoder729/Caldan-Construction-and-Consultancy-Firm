"""
Search service for the compassion page + global navbar.

The user types into the navbar search bar. The dropdown shows matching
items grouped by type (Stories, Actions, Topics, Payment methods).
The full results page at /search/?q=… shows the same data with more
detail.

The dataset is small (dozens of stories, a handful of static actions),
so we keep it in-memory per request — no need for a search engine. A
text query is matched against a pre-normalized token set per item.

Two public entry points:

  * `search(q)` returns a structured list of result dicts, ordered by
    relevance (title hits > body hits > keyword hits).
  * `format_results_for_dropdown(results)` slices the top N results
    into the dropdown shape used by the navbar autocomplete.

The results are categorised so the UI can render icons + grouping:

  type="story"     — OutreachStory (title + summary + body match)
  type="action"    — Static CTA: give money, give items, schedule call, see stories
  type="topic"     — Static topic: hospital, prison, neighbourhood
  type="payment"   — Active PaymentMethod (bank name, paybill number match)

The donor only sees this — never dashboard URLs.
"""

from __future__ import annotations

import logging
import re
from typing import Iterable

from django.db.models import Q
from django.urls import NoReverseMatch, reverse

from compassion.models import OutreachStory, PaymentMethod

logger = logging.getLogger(__name__)


# ───────────────────────────────────────────────────────────────────
# Static compasssion actions — keyword-driven entries that link to
# specific anchors on the compassion page.
# ───────────────────────────────────────────────────────────────────

# Each action has a unique key, a human title, a short blurb that
# matches donor intent, a list of searchable keywords, and a URL
# (rendered as a reverse('compassion:index') + #anchor).
_COMPASSION_ACTIONS = [
    {
        "key": "give_money",
        "title": "Give money",
        "blurb": "Card or M-Pesa via Paystack — every shilling lands somewhere.",
        "keywords": [
            "give", "money", "donate", "donation", "cash", "shilling",
            "kes", "paystack", "mpesa", "card", "gift", "financial",
            "support", "contribute", "fund", "tithe", "offering",
            "donate money", "give money", "online giving",
        ],
        "icon": "fa-hand-holding-heart",
        "anchor": "giving",
        "badge": "Most gifts",
    },
    {
        "key": "give_items",
        "title": "Give items",
        "blurb": "Food, clothes, essentials — we'll coordinate pickup or delivery.",
        "keywords": [
            "give items", "inkind", "in-kind", "goods", "items",
            "donate items", "donate goods", "food", "clothes", "clothing",
            "essentials", "supplies", "pan donation", "stuff",
            "groceries", "blankets", "soap", "hygiene",
        ],
        "icon": "fa-box-heart",
        "anchor": "giving",
        "badge": "In-kind",
    },
    {
        "key": "schedule_call",
        "title": "Schedule a call",
        "blurb": "Talk to a team member about a larger gift, a partnership, or just a question.",
        "keywords": [
            "schedule", "call", "talk", "phone", "discuss", "reach out",
            "contact", "meeting", "consultation", "chat", "converse",
            "schedule call", "schedule a call", "phone call",
        ],
        "icon": "fa-phone-volume",
        "anchor": "giving",
        "badge": "Talk first",
    },
    {
        "key": "see_stories",
        "title": "Read outreach stories",
        "blurb": "See what your gifts do — hospital bedsides, prison visits, neighbourhood meals.",
        "keywords": [
            "stories", "outreach", "impact", "testimony", "testimonials",
            "reports", "gallery", "stories", "see stories", "read stories",
            "field", "ministry", "stories of hope",
        ],
        "icon": "fa-book-open",
        "anchor": "stories",
        "badge": "Impact",
    },
    {
        "key": "ways_to_give",
        "title": "Ways to give",
        "blurb": "Paystack, M-Pesa paybill, direct bank transfer — pick what works for you.",
        "keywords": [
            "ways to give", "payment", "payments", "paybill", "bank",
            "transfer", "deposit", "payment method", "payment methods",
            "how to give", "give options",
        ],
        "icon": "fa-circle-dollar-to-slot",
        "anchor": "payment",
        "badge": "How to give",
    },
]

# ───────────────────────────────────────────────────────────────────
# Static topic pills — match broad category words the donor might
# type ("hospital", "prison", "neighbourhood") and link to the
# giving section filtered by that anchor.
# ───────────────────────────────────────────────────────────────────

_COMPASSION_TOPICS = [
    {
        "key": "hospital",
        "title": "Hospital outreach",
        "category": "HOSPITAL",
        "blurb": "Visits, comfort, and practical help for hospital patients and their families.",
        "keywords": [
            "hospital", "patient", "patients", "medical", "sick",
            "hospital outreach", "hospital visits", "healthcare",
            "bedside", "hospital ministry", "illness",
        ],
        "icon": "fa-hospital",
        "anchor": "giving",
    },
    {
        "key": "prison",
        "title": "Prison ministry",
        "category": "PRISON",
        "blurb": "Visits, letters, and care packages for the incarcerated and their families.",
        "keywords": [
            "prison", "inmate", "inmates", "incarcerated", "jail",
            "prison ministry", "correctional", "prison outreach",
            "behind bars", "prison visit",
        ],
        "icon": "fa-lock",
        "anchor": "giving",
    },
    {
        "key": "neighbourhood",
        "title": "Neighbourhood outreach",
        "category": "NEIGHBOURHOOD",
        "blurb": "Food, essentials, and friendship for those just next door.",
        "keywords": [
            "neighbourhood", "neighborhood", "community", "neighbor",
            "neighbours", "neighbors", "local", "street", "estate",
            "neighbourhood outreach", "community outreach",
            "next door", "nearby",
        ],
        "icon": "fa-people-roof",
        "anchor": "giving",
    },
]


# ───────────────────────────────────────────────────────────────────
# Tokenization — split query into individual words, lowercase,
# strip diacritics. Used to score matches.
# ───────────────────────────────────────────────────────────────────


def _tokenize(text: str) -> set[str]:
    if not text:
        return set()
    # Lowercase + strip punctuation. Keep hyphens inside words so
    # "in-kind" still tokens as "inkind".
    text = text.lower()
    # remove punctuation except hyphens
    text = re.sub(r"[^\w\s-]", " ", text)
    tokens = {t for t in text.split() if t}
    return tokens


def _normalize(text: str) -> str:
    """Lowercase + collapse whitespace. Used for substring matching."""
    if not text:
        return ""
    return re.sub(r"\s+", " ", text.lower().strip())


def _score(query_tokens: set[str], haystack_tokens: set[str], source_weight: int) -> int:
    """Count how many query tokens hit the haystack, weighted by importance."""
    if not query_tokens or not haystack_tokens:
        return 0
    hits = len(query_tokens & haystack_tokens)
    return hits * source_weight


# ───────────────────────────────────────────────────────────────────
# Helpers
# ───────────────────────────────────────────────────────────────────


def _action_url(anchor: str) -> str:
    """Build a URL to the compassion page with a section anchor."""
    try:
        return reverse("compassion:index") + "#" + anchor
    except NoReverseMatch:
        return "/compassion/#" + anchor


def _story_url(story: OutreachStory) -> str:
    try:
        return reverse("compassion:story_detail", kwargs={"slug": story.slug})
    except NoReverseMatch:
        return f"/compassion/stories/{story.slug}/"


# ───────────────────────────────────────────────────────────────────
# Public search entry point
# ───────────────────────────────────────────────────────────────────


def search(query: str, *, limit_per_type: int = 8) -> list[dict]:
    """Return a relevance-ordered list of search results.

    Each result is a dict with the keys the navbar dropdown and the
    full results page both consume:

        {
            "type": "story" | "action" | "topic" | "payment",
            "title": str,
            "blurb": str,
            "url": str,
            "icon": str,            # font-awesome class
            "badge": str,           # optional small label
            "category": str,        # for stories: HOSPITAL/PRISON/NEIGHBOURHOOD
            "score": int,           # for debugging / analytics
        }

    Stories are matched against title + summary + body + location.
    Actions, topics, and payment methods are matched against a
    pre-built keyword list. The highest-scoring items per type come
    first; the overall list is sorted by score descending.
    """
    query = (query or "").strip()
    if not query:
        return []

    # Tokenize once and reuse.
    # We also keep the raw substring for "exact phrase" matching.
    query_tokens = _tokenize(query)
    raw = _normalize(query)
    if not query_tokens and not raw:
        return []

    results: list[dict] = []

    # ───── Stories ─────
    # Weighted: title > summary > body > location.
    try:
        title_q = Q()
        summary_q = Q()
        body_q = Q()
        loc_q = Q()
        for tok in (query_tokens or {raw}):
            title_q |= Q(title__icontains=tok)
            summary_q |= Q(summary__icontains=tok)
            body_q |= Q(body__icontains=tok)
            loc_q |= Q(location__icontains=tok)

        stories = (
            OutreachStory.objects.filter(is_published=True)
            .filter(title_q | summary_q | body_q | loc_q)
            .order_by("display_order", "-event_date")[: limit_per_type * 3]
        )

        for story in stories:
            title_tokens = _tokenize(story.title)
            summary_tokens = _tokenize(story.summary)
            body_tokens = _tokenize(story.body)
            loc_tokens = _tokenize(story.location)

            score = (
                _score(query_tokens, title_tokens, 12)
                + _score(query_tokens, summary_tokens, 6)
                + _score(query_tokens, body_tokens, 3)
                + _score(query_tokens, loc_tokens, 4)
            )
            # Bonus for exact substring hit on the title.
            if raw and raw in _normalize(story.title):
                score += 20
            if score == 0:
                continue

            # Build a snippet from the summary if the title alone is
            # short, or from the body if the query hit deeper.
            blurb = story.summary[:160] if story.summary else ""
            if not blurb and story.body:
                blurb = story.body[:160].rsplit(" ", 1)[0] + "…"

            results.append({
                "type": "story",
                "title": story.title,
                "blurb": blurb,
                "url": _story_url(story),
                "icon": "fa-newspaper",
                "badge": story.get_category_display(),
                "category": story.category,
                "score": score,
                "story_id": story.id,
                "slug": story.slug,
                "location": story.location,
                "event_date": story.event_date.isoformat() if story.event_date else None,
            })
    except Exception as exc:
        logger.warning("search: story query failed: %s", exc)

    # ───── Actions + topics (static) ─────
    for action in _COMPASSION_ACTIONS:
        kw_tokens = _tokenize(" ".join(action["keywords"]))
        title_tokens = _tokenize(action["title"])
        blurb_tokens = _tokenize(action["blurb"])

        score = (
            _score(query_tokens, title_tokens, 10)
            + _score(query_tokens, blurb_tokens, 4)
            + _score(query_tokens, kw_tokens, 6)
        )
        if raw and raw in _normalize(action["title"]):
            score += 25
        if raw and raw in _normalize(" ".join(action["keywords"])):
            score += 12
        if score == 0:
            continue

        results.append({
            "type": "action",
            "title": action["title"],
            "blurb": action["blurb"],
            "url": _action_url(action["anchor"]),
            "icon": action["icon"],
            "badge": action["badge"],
            "score": score,
        })

    for topic in _COMPASSION_TOPICS:
        kw_tokens = _tokenize(" ".join(topic["keywords"]))
        title_tokens = _tokenize(topic["title"])
        blurb_tokens = _tokenize(topic["blurb"])

        score = (
            _score(query_tokens, title_tokens, 10)
            + _score(query_tokens, blurb_tokens, 4)
            + _score(query_tokens, kw_tokens, 6)
        )
        if raw and raw in _normalize(topic["title"]):
            score += 25
        if raw and raw in _normalize(" ".join(topic["keywords"])):
            score += 12
        if score == 0:
            continue

        results.append({
            "type": "topic",
            "title": topic["title"],
            "blurb": topic["blurb"],
            "url": _action_url(topic["anchor"]),
            "icon": topic["icon"],
            "badge": None,
            "category": topic["category"],
            "score": score,
        })

    # ───── Payment methods ─────
    try:
        # Build a query that checks debit name, account number, bank
        # name, and any other human-readable fields the model has.
        # We only probe fields that actually exist on PaymentMethod so
        # we don't generate noise from FieldDoesNotExist errors.
        all_field_names = {f.name for f in PaymentMethod._meta.get_fields()}
        fields_to_probe = [
            f for f in (
                "label", "bank_name", "paybill_number", "till_number",
                "account_name", "account_number", "instructions",
                "short_description", "description",
            )
            if f in all_field_names
        ]
        # Method enum is also searchable (e.g. "mpesa", "bank") — but
        # only the raw enum code ("PAYBILL") is stored in the DB, so
        # match against the human-readable display name in Python.
        # We strip hyphens so "mpesa" matches "m-pesa paybill".
        method_q = Q()
        for tok in (query_tokens or {raw}):
            for choice in PaymentMethod.Method:
                label = choice.label.lower().replace("-", "").replace(" ", "")
                enum_val = choice.value.lower().replace("-", "").replace(" ", "")
                tok_clean = tok.replace("-", "").replace(" ", "")
                if tok_clean in label or tok_clean in enum_val:
                    method_q |= Q(method=choice.value)
                    break

        text_q = Q()
        for field in fields_to_probe:
            for tok in (query_tokens or {raw}):
                text_q |= Q(**{f"{field}__icontains": tok})

        methods = (
            PaymentMethod.objects.filter(is_active=True)
            .filter(text_q | method_q)[: limit_per_type]
        )
        for m in methods:
            # Build a one-line blurb from any field that contains the query.
            blurb = ""
            for field in fields_to_probe:
                val = getattr(m, field, "") or ""
                if raw and raw in _normalize(str(val)):
                    blurb = str(val)[:140]
                    break
            if not blurb and raw and raw in _normalize(str(m.method or "")):
                blurb = m.get_method_display()
            if not blurb:
                blurb = m.__str__() if hasattr(m, "__str__") else ""

            label = m.label or f"{m.get_method_display()}"

            results.append({
                "type": "payment",
                "title": str(label),
                "blurb": blurb,
                "url": _action_url("payment"),
                "icon": getattr(m, "icon_class", "fa-credit-card"),
                "badge": m.get_method_display(),
                "score": 5,
                "method_id": m.id,
            })
    except Exception as exc:
        logger.warning("search: payment method query failed: %s", exc)

    # ───── Sort by score, then by type priority ─────
    type_priority = {"story": 0, "action": 1, "topic": 2, "payment": 3}
    results.sort(key=lambda r: (-r["score"], type_priority.get(r["type"], 9)))

    # Cap how many results go back to the client — huge dropdowns
    # are not useful. The full results page can paginate later.
    return results[: max(limit_per_type * 4, 24)]


def format_results_for_dropdown(results: Iterable[dict], max_items: int = 6) -> list[dict]:
    """Slice the top results into a dropdown-friendly shape.

    The dropdown groups by type. Cap each type to keep the list
    scannable, and the total to a number that fits a 4-5 item
    scannable list. The "View all" link in the UI is a backstop
    for the long tail.
    """
    grouped: dict[str, list[dict]] = {"story": [], "action": [], "topic": [], "payment": []}
    for r in results:
        grouped.setdefault(r["type"], []).append(r)

    dropdown = []
    for type_key, label in (
        ("story", "Outreach stories"),
        ("action", "Compassion actions"),
        ("topic", "Topics"),
        ("payment", "Payment methods"),
    ):
        items = grouped.get(type_key, [])[:max_items]
        if items:
            dropdown.append({
                "group": label,
                "type": type_key,
                "items": items,
            })
    return dropdown
