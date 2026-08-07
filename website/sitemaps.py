from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from projects.models import Project
from services.models import Service


class WebsiteSitemap(Sitemap):
    """
    Sitemap for the public Caldan Construction website.

    Includes all public-facing pages except forms and thank-you pages.
    """

    changefreq = "weekly"
    priority = 0.8

    def items(self):
        """Return all URL items for the sitemap."""
        # Static pages
        static_pages = [
            "website:index",
            "website:about",
            "website:services",
            "website:projects",
            "website:contact",
            "website:legal_privacy",
            "website:legal_terms",
            "website:legal_refunds",
            "website:legal_cookies",
        ]

        # Dynamic pages
        services = Service.objects.filter(is_active=True)
        projects = Project.objects.filter(is_archived=False, status__in=["ACTIVE", "COMPLETED"])

        return static_pages + list(services) + list(projects)

    def location(self, item):
        """Get the URL for a given item."""
        if isinstance(item, str):
            # Static page - reverse by name
            return reverse(item)
        elif isinstance(item, Service):
            # Service detail page
            return reverse("website:service_detail", kwargs={"slug": item.slug})
        elif isinstance(item, Project):
            # Project detail page
            return reverse("website:project_detail", kwargs={"project_id": item.id})
        return "/"

    def lastmod(self, item):
        """Get last modified date for a given item."""
        if isinstance(item, Service):
            return item.updated_at
        elif isinstance(item, Project):
            return item.updated_at
        return None

    def priority(self, item):
        """Get priority for a given item."""
        if isinstance(item, str):
            if item == "website:index":
                return 1.0
            return 0.8
        elif isinstance(item, Service):
            return 0.7
        elif isinstance(item, Project):
            return 0.6
        return 0.5