import logging
from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from django.views import View
from django.http import Http404

from blog.services.blog_service import BlogService
from blog.models.blog_post import BlogPost

logger = logging.getLogger("caldan.blog")

# Whitelist of category values accepted from ?category=. Any other
# value is treated as "all" (no filter). Keep in sync with
# BlogPost.Category.values.
CATEGORY_VALUES = [choice[0] for choice in BlogPost.Category.choices]


class BlogListView(View):
    """
    Public blog listing page with category filter + pagination.

    The filter is server-side: clicking a pill links to
    /blog/?category=<value>, the queryset is filtered before pagination,
    and the resulting counts in the rail are computed from the live
    BlogPost table (not hardcoded).
    """

    def get(self, request):
        """Render blog list with category filter and pagination."""
        try:
            # Read & validate the requested category from the URL.
            active_category = request.GET.get("category", "").strip().lower()
            if active_category not in CATEGORY_VALUES:
                active_category = ""

            # Get published posts via service, optionally narrowed by category.
            posts = BlogService.get_published_posts()
            if active_category:
                posts = posts.filter(category=active_category)

            # Pagination
            paginator = Paginator(posts, 10)
            page = request.GET.get("page", 1)
            posts_page = paginator.get_page(page)

            # Get recent posts for sidebar
            recent_posts = BlogService.get_recent_posts(limit=5)

            # Live counts (per category, plus the "all" total).
            from blog.models.blog_post import BlogPost
            published_qs = BlogPost.objects.filter(
                is_published=True, published_at__isnull=False
            )
            total_posts = published_qs.count()
            counts = {
                c: published_qs.filter(category=c).count()
                for c in CATEGORY_VALUES
            }

            context = {
                "posts": posts_page,
                "recent_posts": recent_posts,
                "total_posts": total_posts,
                "construction_count": counts["construction"],
                "consultancy_count": counts["consultancy"],
                "news_count": counts["news"],
                "active_category": active_category,
                "page_title": "Blog & News",
                "page_description": "Latest news and updates from Caldan Construction and Consultancy Firm.",
            }

            return render(request, "blog/list.html", context)

        except Exception as e:
            logger.error(f"Error rendering blog list: {str(e)}")
            raise


class BlogDetailView(View):
    """
    Public blog detail page.
    """

    def get(self, request, slug):
        """Render single blog post."""
        try:
            # Get post via service
            post = BlogService.get_published_post_by_slug(slug)

            if not post:
                raise Http404("Blog post not found")

            # Get related posts
            related_posts = BlogService.get_related_posts(post, limit=3)

            context = {
                "post": post,
                "related_posts": related_posts,
                "page_title": post.title,
                "page_description": post.excerpt or post.title,
                "og_image": post.image.url if post.image else None,
            }

            return render(request, "blog/detail.html", context)

        except Http404:
            raise
        except Exception as e:
            logger.error(f"Error rendering blog detail for slug {slug}: {str(e)}")
            raise Http404("Blog post not found")


# Function-based views for URL routing
blog_list = BlogListView.as_view()
blog_detail = BlogDetailView.as_view()