"""
Sitemaps for the public Caldan Construction website.

Aggregates ALL indexable public URLs in one sitemap so Google discovers
service detail, project detail, blog post, compassion story, and legal
pages — not just the marketing landing pages.

Each item exposes `lastmod` so Google's crawl budget targets the freshest
content first.
"""

from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from services.models import Service
from projects.models import Project
from blog.models import BlogPost
from compassion.models import OutreachStory


# =====================================================================
# STATIC MARKETING PAGES
# =====================================================================
class StaticViewSitemap(Sitemap):
    """Landing pages and legal pages with no DB-backed detail content.

    StaticViewSitemap is registered FIRST so the dynamic item sections
    below it have stable `priority` and `changefreq` defaults to fall
    back to. priority/changefreq are overridden per-item below.
    """

    priority = 0.5
    changefreq = "monthly"

    def items(self):
        # Ordered top-to-bottom matching the public nav, with legal pages
        # at the bottom. Each tuple is (url_name, changefreq, priority).
        return [
            ("website:index",          "daily",    1.0),
            ("website:about",          "monthly",  0.9),
            ("website:services",       "weekly",   0.9),
            ("website:projects",       "weekly",   0.9),
            ("compassion:index",       "weekly",   0.8),
            ("website:blog",           "daily",    0.8),
            ("website:contact",        "monthly",  0.7),
            ("website:quote_request",  "monthly",  0.6),
            # Legal — discoverable from footer; not for ranking but for
            # transparency and Knowledge-Graph trust signals.
            ("website:legal_privacy",  "yearly",   0.3),
            ("website:legal_terms",    "yearly",   0.3),
            ("website:legal_refunds",  "yearly",   0.3),
            ("website:legal_cookies",  "yearly",   0.3),
        ]

    def location(self, item):
        # All items are static (url_name, changefreq, priority) tuples.
        return reverse(item[0])

    def lastmod(self, item):
        # Static pages don't have a meaningful DB lastmod.
        return None

    def changefreq(self, item):
        return item[1]

    def priority(self, item):
        return item[2]


# =====================================================================
# SERVICE DETAIL PAGES
# =====================================================================
class ServiceSitemap(Sitemap):
    """Every active service. is_active=True filters admin-disabled rows."""

    priority = 0.7
    changefreq = "monthly"

    def items(self):
        return Service.objects.filter(is_active=True).order_by("display_order", "name")

    def location(self, obj):
        return reverse("website:service_detail", kwargs={"slug": obj.slug})

    def lastmod(self, obj):
        return obj.updated_at


# =====================================================================
# PROJECT DETAIL PAGES
# =====================================================================
class ProjectSitemap(Sitemap):
    """Every public (non-archived) project."""

    priority = 0.7
    changefreq = "weekly"

    def items(self):
        return Project.objects.filter(is_archived=False).order_by("-updated_at")

    def location(self, obj):
        # URL pattern uses <int:project_id>, not slug.
        return reverse("website:project_detail", kwargs={"project_id": obj.id})

    def lastmod(self, obj):
        return obj.updated_at


# =====================================================================
# BLOG POSTS
# =====================================================================
class BlogPostSitemap(Sitemap):
    """Published blog posts only — drafts and unpublished posts are excluded."""

    priority = 0.6
    changefreq = "weekly"

    def items(self):
        return BlogPost.objects.filter(is_published=True).order_by("-updated_at")

    def location(self, obj):
        return reverse("website:blog_detail", kwargs={"slug": obj.slug})

    def lastmod(self, obj):
        return obj.updated_at


# =====================================================================
# COMPASSION STORIES
# =====================================================================
class CompassionStorySitemap(Sitemap):
    """Published compassion field stories — hospital, prison, neighbourhood."""

    priority = 0.6
    changefreq = "monthly"

    def items(self):
        return OutreachStory.objects.filter(is_published=True).order_by("-updated_at")

    def location(self, obj):
        return reverse("compassion:story_detail", kwargs={"slug": obj.slug})

    def lastmod(self, obj):
        return obj.updated_at


# =====================================================================
# COMBINED REGISTRY — passed to the sitemap view
# =====================================================================
WebsiteSitemap = {
    # Static marketing + legal pages first.
    "pages":     StaticViewSitemap,
    # Dynamic detail pages.
    "services":  ServiceSitemap,
    "projects":  ProjectSitemap,
    "posts":     BlogPostSitemap,
    "stories":   CompassionStorySitemap,
}
