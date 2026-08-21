"""
URL Configuration for Caldan Construction project.
"""

from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponse, JsonResponse, HttpResponseRedirect
from django.views.decorators.http import require_GET
from django.utils import timezone

from website.sitemaps import WebsiteSitemap


def health_check(request):
    """Health check endpoint for monitoring.

    Returns a noindex JSON response so monitoring endpoints never appear in
    SERPs. The X-Robots-Tag header is set on the response itself since
    robots.txt cannot disallow a request path that already returns 200.
    """
    status = {
        'status': 'healthy',
        'timestamp': timezone.now().isoformat(),
        'version': '1.0.0',
    }
    response = JsonResponse(status)
    response['X-Robots-Tag'] = 'noindex, nofollow'
    return response


@require_GET
def robots_txt(request):
    """
    Serve /robots.txt.

    Allows everything by default and points crawlers at the sitemap so
    Google Search Console picks up every public URL. Blocks admin,
    dashboard, accounts, and any private endpoints.

    The Sitemap directive uses an absolute URL derived from the request
    host — that's what Google requires (relative paths are technically
    valid but rejected by some validators).
    """
    # Build absolute sitemap URL from the request host. Falls back to
    # SITE_URL if the request didn't carry a Host header (rare).
    site_url = getattr(settings, "SITE_URL", None) or f"{request.scheme}://{request.get_host()}"
    sitemap_url = f"{site_url.rstrip('/')}/sitemap.xml"

    # Disallow rules — public crawler should never see these.
    # NOTE: query-string prefix rules like `/?page=` confuse Google's
    # robots.txt parser — they can over-match and block legitimate
    # URLs like /services/. Keep these to path-prefix disallows only.
    blocked_paths = [
        "/admin/",
        "/dashboard/",
        "/accounts/",
        "/setup/",
        "/api/",
        "/media/private/",
    ]

    lines = [
        "# ============================================================",
        "# Caldan Construction — robots.txt",
        "# https://www.caldanconstruction.com/",
        "# ============================================================",
        "",
        "# === Default rules: friendly crawlers ===",
        "User-Agent: *",
        "Allow: /",
        "Disallow: /admin/",
        "Disallow: /admin-services/",
        "Disallow: /admin-projects/",
        "Disallow: /dashboard/",
        "Disallow: /accounts/",
        "Disallow: /setup/",
        "Disallow: /api/",
        "Disallow: /blog/dashboard/",
        "Disallow: /inventory/",
        "Disallow: /finances/",
        "Disallow: /clients/",
        "Disallow: /team/",
        "Disallow: /reports/",
        "Disallow: /notifications/",
        "Disallow: /shop/admin/",
        "Disallow: /shop/checkout/",
        "Disallow: /shop/payment/",
        "Disallow: /newsletter/",
        "Disallow: /health/",
        "Disallow: /thank-you/",
        "Disallow: /media/private/",
    ]

    lines += [
        "",
        f"Sitemap: {sitemap_url}",
        "",
    ]

    # === Specific bots ===
    # Googlebot: respect the same rules but with a helpful crawl delay.
    lines += [
        "# === Googlebot ===",
        "User-Agent: Googlebot",
        "Allow: /",
        "Disallow: /admin/",
        "Disallow: /admin-services/",
        "Disallow: /admin-projects/",
        "Disallow: /dashboard/",
        "Disallow: /accounts/",
        "Disallow: /setup/",
        "Disallow: /api/",
        "Disallow: /blog/dashboard/",
        "Disallow: /inventory/",
        "Disallow: /finances/",
        "Disallow: /clients/",
        "Disallow: /team/",
        "Disallow: /reports/",
        "Disallow: /notifications/",
        "Disallow: /shop/admin/",
        "Disallow: /shop/checkout/",
        "Disallow: /shop/payment/",
        "Disallow: /newsletter/",
        "Disallow: /health/",
        "Disallow: /thank-you/",
        "Disallow: /media/private/",
        "Crawl-delay: 1",
        "",
    ]

    # Bingbot: similar.
    lines += [
        "# === Bingbot ===",
        "User-Agent: Bingbot",
        "Allow: /",
        "Disallow: /admin/",
        "Disallow: /admin-services/",
        "Disallow: /admin-projects/",
        "Disallow: /dashboard/",
        "Disallow: /accounts/",
        "Disallow: /setup/",
        "Disallow: /api/",
        "Disallow: /blog/dashboard/",
        "Disallow: /inventory/",
        "Disallow: /finances/",
        "Disallow: /clients/",
        "Disallow: /team/",
        "Disallow: /reports/",
        "Disallow: /notifications/",
        "Disallow: /shop/admin/",
        "Disallow: /shop/checkout/",
        "Disallow: /shop/payment/",
        "Disallow: /newsletter/",
        "Disallow: /health/",
        "Disallow: /thank-you/",
        "Disallow: /media/private/",
        "Crawl-delay: 1",
        "",
    ]

    # === Bad bots: keep out ===
    bad_bots = [
        "AhrefsBot",
        "SemrushBot",
        "MJ12bot",
        "DotBot",
        "BLEXBot",
    ]
    lines += [
        "# === Aggressive SEO scrapers — keep out ===",
    ]
    for bot in bad_bots:
        lines += [
            f"User-Agent: {bot}",
            "Disallow: /",
            "",
        ]

    return HttpResponse("\n".join(lines), content_type="text/plain")


# ---------------------------------------------------------------------
# Legacy /dashboard/<app>/… redirects.
#
# Earlier iterations of the sidebar produced URLs like
# /dashboard/shop/orders/1/ and /dashboard/finances/payments/1/. The
# apps actually live at /shop/ and /finances/ — keep the old paths
# alive as 301 redirects so any bookmark, slack link, or pasted URL
# still lands users on the right page instead of 404ing.
# ---------------------------------------------------------------------
@require_GET
def _legacy_dashboard_redirect(request, path):
    return HttpResponseRedirect('/' + path)


urlpatterns = [
    # Django Admin
    path('admin/', admin.site.urls),

    # Health Check
    path('health/', health_check, name='health_check'),
    # =================================================================
    # LEGACY /dashboard/<app>/… aliases (see _legacy_dashboard_redirect)
    # =================================================================
    path('dashboard/shop/<path:path>',
         _legacy_dashboard_redirect, {'path': 'shop/'}),
    path('dashboard/shop/',
         _legacy_dashboard_redirect, {'path': 'shop/'}),
    path('dashboard/finances/<path:path>',
         _legacy_dashboard_redirect, {'path': 'finances/'}),
    path('dashboard/finances/',
         _legacy_dashboard_redirect, {'path': 'finances/'}),

    # =================================================================
    # BLOG ADMIN — registered BEFORE the public site so that
    # /blog/dashboard/... routes match before /blog/<slug>/.
    # =================================================================
    path('blog/', include('blog.urls')),

    # =================================================================
    # COMPASSIONATE MINISTRY (public + dashboard)
    # =================================================================
    path('compassion/', include(('compassion.urls_public', 'compassion'), namespace='compassion')),
    path('dashboard/compassion/', include(('compassion.urls_dashboard', 'compassion_dashboard'), namespace='compassion_dashboard')),

    # =================================================================
    # PUBLIC WEBSITE — mounted at root
    # =================================================================
    path('', include('website.urls')),

    # =================================================================
    # ACCOUNTS APP (Authentication + Setup)
    # =================================================================
    path('', include('accounts.urls')),

    # =================================================================
    # SERVICES APP (internal/admin) — dashboard-side service management.
    # Lives at /admin-services/... to free up /services/ for the public site.
    # =================================================================
    path('admin-services/', include('services.urls')),

    # =================================================================
    # SHOP
    # =================================================================
    path('shop/', include('shop.urls')),

    # =================================================================
    # DASHBOARD
    # =================================================================
    path('dashboard/', include('dashboard.urls')),

    # =================================================================
    # PROJECTS (internal admin)
    # Lives at /admin-projects/... to free up /projects/ for the public site
    # (mirrors the services pattern at /admin-services/).
    # =================================================================
    path('admin-projects/', include(('projects.urls', 'admin_projects'), namespace='admin_projects')),

    # =================================================================
    # INVENTORY
    # =================================================================
    path('inventory/', include('inventory.urls')),

    # =================================================================
    # FINANCES
    # =================================================================
    path('finances/', include('finances.urls')),

    # =================================================================
    # CLIENTS
    # =================================================================
    path('clients/', include('clients.urls')),

    # =================================================================
    # TEAM (internal admin) — public about page is at /about/
    # =================================================================
    path('team/', include('team.urls')),

    # =================================================================
    # REPORTS
    # =================================================================
    path('reports/', include('reports.urls')),

    # =================================================================
    # NOTIFICATIONS
    # =================================================================
    path('notifications/', include('notifications.urls')),

    # =================================================================
    # BLOG — admin routes are registered at the top of this file so
    # /blog/dashboard/... matches before the public site's
    # /blog/<slug>/. The public blog index lives under /blog/ inside
    # the website app, so we don't include 'blog.urls' again here.
    # =================================================================

    # =================================================================
    # SEO — sitemap.xml + robots.txt
    # Both are public and unauthenticated. Point Google Search Console
    # at https://<your-domain>/sitemap.xml and it will discover every
    # URL listed there.
    # =================================================================
    path(
        'sitemap.xml',
        sitemap,
        {'sitemaps': WebsiteSitemap},
        name='django.contrib.sitemaps.views.sitemap',
    ),
    path('robots.txt', robots_txt, name='robots_txt'),
]

# ---------------------------------------------------------------------
# Custom error handlers.
#
# Django renders templates/404.html and templates/500.html when DEBUG=False
# and these handlers are declared. The templates extend website/base.html
# so they pick up the brand favicon, nav, and footer for free.
# ---------------------------------------------------------------------
handler404 = 'django.views.defaults.page_not_found'
handler500 = 'django.views.defaults.server_error'

# Static & Media files (Development only)
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)