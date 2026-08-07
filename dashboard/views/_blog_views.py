import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta

from accounts.permissions.decorators import admin_required
from blog.services.blog_service import BlogService
from blog.models.blog_post import BlogPost
from accounts.services.audit_service import AuditService


def _normalise_category(raw):
    """Coerce an incoming category string to a valid BlogPost.Category
    value. Returns the default ('news') for empty/missing/invalid input
    so a bad POST never blows up the create view."""
    if not raw:
        return BlogPost.Category.NEWS
    raw = raw.strip().lower()
    valid = {c[0] for c in BlogPost.Category.choices}
    return raw if raw in valid else BlogPost.Category.NEWS

logger = logging.getLogger("caldan.blog")


@login_required
@admin_required
def blog_list(request):
    """
    Admin blog list view with search, filter, and pagination.

    Displays all blog posts (including drafts) with stats cards.
    """
    # Get all posts via service
    posts = BlogService.get_admin_posts(user=request.user)

    # Stats
    total_posts = posts.count()
    published_posts = posts.filter(is_published=True).count()
    draft_posts = posts.filter(is_published=False).count()
    recent_count = posts.filter(
        created_at__gte=timezone.now() - timedelta(days=7)
    ).count()
    posts_with_images = posts.exclude(image__isnull=True).exclude(image="").count()

    # Search
    search_query = request.GET.get("search", "").strip()
    if search_query:
        posts = posts.filter(
            Q(title__icontains=search_query) |
            Q(content__icontains=search_query) |
            Q(excerpt__icontains=search_query)
        )

    # Status filter
    status_filter = request.GET.get("status", "")
    if status_filter == "published":
        posts = posts.filter(is_published=True)
    elif status_filter == "draft":
        posts = posts.filter(is_published=False)

    # Ordering (newest first)
    posts = posts.order_by("-created_at")

    # Pagination
    paginator = Paginator(posts, 15)
    page = request.GET.get("page", 1)

    try:
        posts_page = paginator.page(page)
    except PageNotAnInteger:
        posts_page = paginator.page(1)
    except EmptyPage:
        posts_page = paginator.page(paginator.num_pages)

    context = {
        "posts": posts_page,
        "total_posts": total_posts,
        "published_posts": published_posts,
        "draft_posts": draft_posts,
        "recent_count": recent_count,
        "posts_with_images": posts_with_images,
        "search_query": search_query,
        "status_filter": status_filter,
        "page_title": "Blog Management",
    }

    return render(request, "blog/dashboard/admin/blog/list.html", context)


@login_required
@admin_required
def blog_create(request):
    """
    Admin create blog post view.
    """
    if request.method == "POST":
        action = request.POST.get("action", "save_draft")
        is_published = action == "publish"

        # Get form data
        title = request.POST.get("title", "").strip()
        slug = request.POST.get("slug", "").strip()
        excerpt = request.POST.get("excerpt", "").strip()
        content = request.POST.get("content", "").strip()
        image = request.FILES.get("image")
        category = _normalise_category(request.POST.get("category"))

        # Validate
        if not title:
            messages.error(request, "Title is required.")
            return render(request, "blog/dashboard/admin/blog/create.html", {
                "page_title": "Create Blog Post",
            })

        if not content:
            messages.error(request, "Content is required.")
            return render(request, "blog/dashboard/admin/blog/create.html", {
                "page_title": "Create Blog Post",
            })

        # Prepare data
        data = {
            "title": title,
            "slug": slug or None,
            "excerpt": excerpt,
            "content": content,
            "image": image,
            "category": category,
            "is_published": is_published,
        }

        try:
            # Create post via service
            post = BlogService.create_post(user=request.user, data=data)

            if is_published:
                messages.success(request, f'Blog post "{post.title}" published successfully!')
            else:
                messages.success(request, f'Blog post "{post.title}" saved as draft.')

            # Log audit is handled in service
            return redirect("blog:admin_list")

        except Exception as e:
            logger.error(f"Error creating blog post: {str(e)}")
            messages.error(request, f"Error creating post: {str(e)}")
            return render(request, "blog/dashboard/admin/blog/create.html", {
                "page_title": "Create Blog Post",
            })

    # GET request
    context = {
        "page_title": "Create Blog Post",
    }
    return render(request, "blog/dashboard/admin/blog/create.html", context)


@login_required
@admin_required
def blog_edit(request, post_id):
    """
    Admin edit blog post view.
    """
    # Get post via service
    post = BlogService.get_admin_post_by_id(post_id, user=request.user)

    if not post:
        messages.error(request, "Blog post not found.")
        return redirect("blog:admin_list")

    if request.method == "POST":
        action = request.POST.get("action", "save_draft")
        is_published = action == "publish"

        # Get form data
        title = request.POST.get("title", "").strip()
        slug = request.POST.get("slug", "").strip()
        excerpt = request.POST.get("excerpt", "").strip()
        content = request.POST.get("content", "").strip()
        image = request.FILES.get("image")
        remove_image = request.POST.get("remove_image", "false") == "true"
        category = _normalise_category(request.POST.get("category"))

        # Validate
        if not title:
            messages.error(request, "Title is required.")
            return render(request, "blog/dashboard/admin/blog/edit.html", {
                "post": post,
                "page_title": "Edit Blog Post",
            })

        if not content:
            messages.error(request, "Content is required.")
            return render(request, "blog/dashboard/admin/blog/edit.html", {
                "post": post,
                "page_title": "Edit Blog Post",
            })

        # Prepare data
        data = {
            "title": title,
            "slug": slug or None,
            "excerpt": excerpt,
            "content": content,
            "category": category,
            "is_published": is_published,
        }

        # Handle image
        if remove_image:
            data["image"] = None
        elif image:
            data["image"] = image

        try:
            # Update post via service
            post = BlogService.update_post(user=request.user, post=post, data=data)

            if is_published:
                messages.success(request, f'Blog post "{post.title}" published successfully!')
            else:
                messages.success(request, f'Blog post "{post.title}" updated successfully.')

            # Log audit is handled in service
            return redirect("blog:admin_list")

        except Exception as e:
            logger.error(f"Error updating blog post {post_id}: {str(e)}")
            messages.error(request, f"Error updating post: {str(e)}")
            return render(request, "blog/dashboard/admin/blog/edit.html", {
                "post": post,
                "page_title": "Edit Blog Post",
            })

    # GET request
    context = {
        "post": post,
        "page_title": f"Edit: {post.title}",
    }
    return render(request, "blog/dashboard/admin/blog/edit.html", context)


@login_required
@admin_required
def blog_delete(request, post_id):
    """
    Admin delete blog post view.
    """
    # Get post
    post = get_object_or_404(BlogPost, id=post_id)

    if request.method == "POST":
        title = post.title

        try:
            # Delete via service
            BlogService.delete_post(user=request.user, post=post)

            messages.success(request, f'Blog post "{title}" deleted successfully.')
            return redirect("blog:admin_list")

        except Exception as e:
            logger.error(f"Error deleting blog post {post_id}: {str(e)}")
            messages.error(request, f"Error deleting post: {str(e)}")
            return redirect("blog:admin_list")

    # GET request (show confirmation)
    context = {
        "post": post,
        "page_title": f"Delete: {post.title}",
    }
    return render(request, "blog/dashboard/admin/blog/delete_confirm.html", context)


@login_required
@admin_required
def blog_toggle(request, post_id):
    """
    Toggle publish status of a blog post.
    """
    if request.method != "POST":
        return HttpResponseRedirect(reverse("blog:admin_list"))

    # Get post
    post = get_object_or_404(BlogPost, id=post_id)

    try:
        # Toggle via service
        post = BlogService.toggle_publish(user=request.user, post=post)

        status = "published" if post.is_published else "unpublished"
        messages.success(request, f'Blog post "{post.title}" {status} successfully.')

    except Exception as e:
        logger.error(f"Error toggling blog post {post_id}: {str(e)}")
        messages.error(request, f"Error toggling post: {str(e)}")

    return HttpResponseRedirect(reverse("blog:admin_list"))


@login_required
@admin_required
def blog_broadcast(request, post_id):
    """
    Manually re-broadcast a published blog post to all active newsletter
    subscribers. The first-publish broadcast is automatic via the
    post_save signal — this endpoint exists so admins can re-send the
    email when an already-published post has been materially updated.

    GET → show a confirmation page (so accidental link clicks don't spam).
    POST → perform the broadcast and redirect with a result message.
    """
    post = get_object_or_404(BlogPost, id=post_id)

    if request.method == "POST":
        if not post.is_published:
            messages.error(
                request,
                f'"{post.title}" is not published. Publish it first, then use '
                '"Email Subscribers" to re-broadcast after future edits.',
            )
            return redirect("blog:admin_edit", post_id=post.id)

        try:
            from blog.services.blog_service import BlogService as _BlogSvc
            result = _BlogSvc.broadcast_to_subscribers(user=request.user, post=post)
        except Exception as e:
            logger.exception("Manual broadcast failed for blog post %s", post_id)
            messages.error(request, f"Broadcast failed: {str(e)}")
            return redirect("blog:admin_edit", post_id=post.id)

        if result.get("skipped"):
            messages.warning(
                request,
                f'Broadcast skipped: {result.get("reason", "unknown reason")}',
            )
        else:
            sent = result.get("sent", 0)
            failed = result.get("failed", 0)
            total = result.get("total", 0)
            if sent == 0 and total == 0:
                messages.info(
                    request,
                    f'No active newsletter subscribers — nothing to send for "{post.title}".',
                )
            elif failed == 0:
                messages.success(
                    request,
                    f'Sent "{post.title}" to {sent} subscriber{sent != 1 and "s" or ""}.',
                )
            else:
                messages.warning(
                    request,
                    f'Broadcast partial: {sent} sent, {failed} failed '
                    f'(of {total}) for "{post.title}".',
                )

        return redirect("blog:admin_edit", post_id=post.id)

    # GET → confirmation page
    context = {
        "post": post,
        "page_title": f"Broadcast: {post.title}",
    }
    return render(request, "blog/dashboard/admin/blog/broadcast_confirm.html", context)


@login_required
@admin_required
def blog_detail(request, post_id):
    """
    Admin blog detail view.
    """
    # Get post via service
    post = BlogService.get_admin_post_by_id(post_id, user=request.user)

    if not post:
        messages.error(request, "Blog post not found.")
        return redirect("blog:admin_list")

    context = {
        "post": post,
        "page_title": post.title,
    }
    return render(request, "blog/dashboard/admin/blog/detail.html", context)