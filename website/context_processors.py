import logging
from django.core.cache import cache
from django.conf import settings
from django.utils import timezone
from clients.models.client import Client
from services.models import Service
from projects.models import Project
from website.forms.newsletter_form import NewsletterForm

logger = logging.getLogger(__name__)

logger = logging.getLogger(__name__)


def trust_counter(request):
    """
    Inject the dynamic trust counter into all website templates.

    Counts active clients (status='ACTIVE') and caches the result for 60 seconds.
    Falls back to database query if cache is empty.

    Returns:
        dict: {'trust_counter': int} - Number of active clients
    """
    try:
        cache_timeout = getattr(settings, "CACHE_FALLBACK_TIMEOUT", 60)
        count = cache.get("trust_counter")

        if count is None:
            # Count clients with status 'ACTIVE'
            count = Client.objects.filter(status=Client.Status.ACTIVE).count()
            cache.set("trust_counter", count, cache_timeout)

        return {"trust_counter": count}

    except Exception as e:
        logger.exception(f"Failed to get trust counter: {str(e)}")
        return {"trust_counter": 0}


def site_settings(request):
    """
    Inject global site settings into all website templates.

    Returns:
        dict: Site-wide configuration values
    """
    return {
        "SITE_NAME": getattr(settings, "APP_NAME", "Caldan Construction"),
        "SITE_TAGLINE": getattr(settings, "APP_TAGLINE", "Building Kenya's Future, One Project at a Time."),
        "ADMIN_EMAIL": getattr(settings, "ADMIN_EMAIL", "info.caldanconstruction@gmail.com"),
        "ADMIN_PHONE": getattr(settings, "ADMIN_PHONE", "+254703653010"),
        "CURRENCY_SYMBOL": getattr(settings, "CURRENCY_SYMBOL", "KSh"),
        "YEAR": timezone.now().year,
    }


def newsletter_form(request):
    """
    Inject newsletter subscription form into all website templates.

    Returns:
        dict: {'newsletter_form': NewsletterForm}
    """
    return {
        "newsletter_form": NewsletterForm(),
    }


def years_experience(request):
    """
    Inject the years of experience into all website templates.

    Calculated from 2008 (founding year) to current year.
    Auto-updates when a new year starts.

    Returns:
        dict: {'years_experience': int} - Years since 2008
    """
    try:
        founding_year = 2008
        current_year = timezone.now().year
        years = current_year - founding_year
        return {"years_experience": years}
    except Exception as e:
        logger.exception(f"Failed to calculate years experience: {str(e)}")
        return {"years_experience": 0}


def project_stats(request):
    """
    Inject dynamic project counts into all website templates.

    Counts completed and active projects (cached for 5 min so we don't
    hammer the DB on every request). Returns 0 on any DB error so the
    template never breaks.

    Returns:
        dict: {
            'completed_projects': int,
            'active_projects': int,
        }
    """
    out = {"completed_projects": 0, "active_projects": 0}
    try:
        cache_ttl = 300  # 5 minutes
        completed = cache.get("stats_completed_projects")
        if completed is None:
            completed = (
                Project.objects.filter(status="COMPLETED", is_archived=False).count()
            )
            cache.set("stats_completed_projects", completed, cache_ttl)
        out["completed_projects"] = completed

        active = cache.get("stats_active_projects")
        if active is None:
            active = (
                Project.objects.filter(status="ACTIVE", is_archived=False).count()
            )
            cache.set("stats_active_projects", active, cache_ttl)
        out["active_projects"] = active
    except Exception as e:
        logger.exception(f"Failed to calculate project stats: {e}")
    return out


def services_preview(request):
    """
    Inject the first 6 active services into all website templates.

    Used by the shared footer partial so every page shows the same service list.
    Cached for 5 minutes since the catalog rarely changes; invalidated when
    services are saved/updated via the model save() signals (see apps.services).

    Returns:
        dict: {'services_preview': list[Service]} - Up to 6 active services
    """
    try:
        cache_key = "footer_services_preview"
        services = cache.get(cache_key)

        if services is None:
            services = list(
                Service.objects.filter(is_active=True)
                .order_by("display_order", "name")[:6]
            )
            cache.set(cache_key, services, 300)  # 5 minutes

        return {"services_preview": services}

    except Exception as e:
        logger.exception(f"Failed to get services preview: {str(e)}")
        return {"services_preview": []}


def cart_count(request):
    """
    Inject the current cart item count into every template.

    Reads the session cart for the anonymous user. Returns 0 if there is no
    session, no cart row, or any DB error. The cart must be live (no cache)
    because it changes with every add/remove.
    """
    try:
        session_key = request.session.session_key
        if not session_key:
            return {"cart_count": 0}

        # Local import to avoid app-loading-order surprises at startup.
        from shop.models import Cart
        cart = Cart.objects.filter(session_key=session_key).first()
        if not cart:
            return {"cart_count": 0}
        return {"cart_count": cart.items.count()}
    except Exception as e:
        logger.exception("Failed to get cart count: %s", e)
        return {"cart_count": 0}