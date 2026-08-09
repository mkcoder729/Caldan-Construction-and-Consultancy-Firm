from django.contrib.sitemaps import Sitemap
from django.urls import reverse


class WebsiteSitemap(Sitemap):
    """
    Sitemap for the public Caldan Construction website.

    Marketing pages only — does NOT include individual service detail
    pages, individual project pages, or individual blog post pages.
    Aggregate listing pages (/services/, /projects/, /blog/) handle
    crawl discovery for those; the service/project/post detail URLs
    add noise to the sitemap without SEO benefit.
    """

    # Defaults — overridden per-item below.
    changefreq = "weekly"
    priority = 0.5

    def items(self):
        """Return all URL items for the sitemap."""
        # Static pages — ordered to match the public nav top-to-bottom so
        # Google ranks them in the same sequence visitors see them. Legal
        # pages are intentionally excluded (footer-only, not for ranking).
        static_pages = [
            # Homepage — top priority.
            ("website:index", "daily", 1.0),
            # Marketing
            ("website:about", "monthly", 0.9),
            ("website:services", "weekly", 0.9),
            ("website:projects", "weekly", 0.9),
            # Compassionate Ministry — discoverable from the nav after Projects.
            ("compassion:index", "weekly", 0.8),
            # Blog and contact sit at the bottom of the nav.
            ("website:blog", "daily", 0.8),
            ("website:contact", "monthly", 0.7),
        ]

        return static_pages

    def location(self, item):
        """Get the URL for a given item."""
        # All items are static pages (url_name, changefreq, priority).
        return reverse(item[0])

    def lastmod(self, item):
        """Static pages have no meaningful lastmod stamp."""
        return None

    def changefreq(self, item):
        """Per-item changefreq."""
        return item[1]

    def priority(self, item):
        """Per-item priority."""
        return item[2]