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
    """Health check endpoint for monitoring."""
    status = {
        'status': 'healthy',
        'timestamp': timezone.now().isoformat(),
        'version': '1.0.0',
    }
    return JsonResponse(status)


@require_GET
def robots_txt(request):
    """
    Serve /robots.txt with sensible defaults.

    Allows everything by default and points crawlers at the sitemap so
    Google Search Console picks up every public URL. Block /admin/,
    /dashboard/, /api/ prefixes just in case.

    NOTE: if you go live and want to control crawl rate, switch this to
    read SITE_URL from settings and replace the hard-coded sitemap URL.
    """
    lines = [
        "User-Agent: *",
        "Disallow: /admin/",
        "Disallow: /dashboard/",
        "Disallow: /accounts/",
        "Allow: /",
        "",
        # The sitemap index — Google reads this from the host header so
        # we leave the path relative-friendly.
        "Sitemap: /sitemap.xml",
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
        {'sitemaps': {'website': WebsiteSitemap}},
        name='django.contrib.sitemaps.views.sitemap',
    ),
    path('robots.txt', robots_txt, name='robots_txt'),
]

# Static & Media files (Development only)
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)