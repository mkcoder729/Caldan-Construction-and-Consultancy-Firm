import logging
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.contrib import messages
from django.db.models import Q, Count
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from projects.models import Project
from services.models import Service
from team.models import TeamMember
from website.forms.contact_form import ContactForm
from website.forms.quote_form import QuoteForm
from website.forms.newsletter_form import NewsletterForm
from website.services import ContactService, QuoteService
from website.models.contact import ContactSubmission
from website.models.newsletter import NewsletterSubscriber
from notifications.services.email_service import EmailService
from accounts.services.audit_service import AuditService

logger = logging.getLogger(__name__)


def index(request: HttpRequest) -> HttpResponse:
    """Landing page - the most important page on the site."""
    # Get featured projects
    featured_projects = Project.objects.filter(
        is_archived=False,
        status__in=["ACTIVE", "COMPLETED"],
    ).order_by("-created_at")[:6]

    # Get services for the preview (first 6)
    services_preview = Service.objects.filter(is_active=True).order_by("display_order", "name")[:6]

    # Get testimonials
    try:
        from website.models.testimonial import Testimonial
        testimonials = Testimonial.objects.filter(is_active=True).order_by("display_order")[:6]
    except (ImportError, AttributeError):
        testimonials = []

    context = {
        "featured_projects": featured_projects,
        "services_preview": services_preview,
        "testimonials": testimonials,
    }

    return render(request, "website/index.html", context)


def about(request: HttpRequest) -> HttpResponse:
    """About page - company story, mission, vision, and team."""
    team_members = TeamMember.objects.filter(is_active=True).order_by("display_order", "name")

    # Get stats for the stats bar
    project_count = Project.objects.filter(is_archived=False).count()
    active_projects = Project.objects.filter(status="ACTIVE").count()
    completed_projects = Project.objects.filter(status="COMPLETED").count()

    context = {
        "team_members": team_members,
        "project_count": project_count,
        "active_projects": active_projects,
        "completed_projects": completed_projects,
    }

    return render(request, "website/about.html", context)


def services(request: HttpRequest) -> HttpResponse:
    """Services page - all 9 service categories."""
    services_list = Service.objects.filter(is_active=True).order_by("display_order", "name")

    # Get category choices for display
    categories = Service.Category.choices

    context = {
        "services": services_list,
        "categories": categories,
    }

    return render(request, "website/services.html", context)


def service_detail(request: HttpRequest, slug: str) -> HttpResponse:
    """Service detail page with related projects."""
    service = get_object_or_404(Service, slug=slug, is_active=True)

    # Get related projects
    related_projects = service.projects.filter(
        is_archived=False,
        status__in=["ACTIVE", "COMPLETED"],
    ).order_by("-created_at")[:6]

    context = {
        "service": service,
        "related_projects": related_projects,
    }

    return render(request, "website/service_detail.html", context)


def projects(request: HttpRequest) -> HttpResponse:
    """Projects gallery with filtering."""
    projects_list = Project.objects.filter(is_archived=False)

    # Filter by status
    status_filter = request.GET.get("status", "")
    if status_filter and status_filter in ["ACTIVE", "COMPLETED", "PLANNING", "ON_HOLD"]:
        projects_list = projects_list.filter(status=status_filter)

    # Filter by category via the M2M to services.Service.category.
    # Project itself has no `category` field — categories come from the
    # linked services. Validate against the Service.Category enum so a
    # bogus query string (e.g. ?category=Residential) is silently ignored
    # instead of raising FieldError.
    category_filter = request.GET.get("category", "")
    valid_categories = {key for key, _ in Service.Category.choices}
    if category_filter and category_filter in valid_categories:
        projects_list = projects_list.filter(services__category=category_filter).distinct()

    # Get unique counties for the filter dropdown
    counties = Project.objects.filter(is_archived=False).values_list("county", flat=True).distinct().order_by("county")

    # Pagination
    paginator = Paginator(projects_list, 12)
    page = request.GET.get("page", 1)

    try:
        projects_page = paginator.page(page)
    except PageNotAnInteger:
        projects_page = paginator.page(1)
    except EmptyPage:
        projects_page = paginator.page(paginator.num_pages)

    # Get status counts
    status_counts = Project.objects.filter(is_archived=False).values("status").annotate(count=Count("status"))

    # Featured projects for the spotlight partial.
    # Now backed by the explicit `is_featured` flag (set from the dashboard
    # or admin). If no projects are flagged, the partial collapses entirely
    # via the `{% if featured_projects %}` guard — so we DON'T fall back
    # to a `created_at` ordering here. Editorial intent wins.
    featured_projects = Project.objects.filter(
        is_archived=False,
        status__in=["ACTIVE", "COMPLETED"],
        is_featured=True,
    ).order_by("-created_at")[:3]

    context = {
        "projects": projects_page,
        "counties": [c for c in counties if c],
        "current_status": status_filter,
        "current_category": category_filter,
        "status_counts": {item["status"]: item["count"] for item in status_counts},
        "categories": Service.Category.choices,
        "featured_projects": featured_projects,
        "total_projects": projects_list.count(),
    }

    return render(request, "website/projects.html", context)


def project_detail(request: HttpRequest, project_id: int) -> HttpResponse:
    """Project detail page with gallery and services."""
    project = get_object_or_404(
        Project,
        id=project_id,
        is_archived=False,
    )

    # Get gallery images (from project.gallery if it exists)
    gallery_images = []
    if hasattr(project, "gallery_images"):
        gallery_images = project.gallery_images.all().order_by("display_order")

    # Get services used on this project
    services_used = project.services.filter(is_active=True)

    context = {
        "project": project,
        "gallery_images": gallery_images,
        "services_used": services_used,
    }

    return render(request, "website/project_detail.html", context)


def contact(request: HttpRequest) -> HttpResponse:
    """Contact page with form."""
    if request.method == "POST":
        form = ContactForm(request.POST)

        if form.is_valid():
            # Extract data
            name = form.cleaned_data["name"]
            email = form.cleaned_data["email"]
            phone = form.cleaned_data["phone"]
            subject = form.cleaned_data["subject"]
            message = form.cleaned_data["message"]

            # Save via service
            ContactService.create_submission(
                name=name,
                email=email,
                phone=phone,
                subject=subject,
                message=message,
                request=request,
            )

            messages.success(request, "Your message has been sent. We'll get back to you within 24 hours.")
            return render(request, "website/thank_you.html", {"form_type": "contact"})

        # Form errors
        messages.error(request, "Please correct the errors below.")
        return render(request, "website/contact.html", {"form": form})

    # GET request
    form = ContactForm()
    return render(request, "website/contact.html", {"form": form})


def quote_request(request: HttpRequest) -> HttpResponse:
    """Quote request form page."""
    if request.method == "POST":
        form = QuoteForm(request.POST)

        if form.is_valid():
            # Extract data
            name = form.cleaned_data["name"]
            email = form.cleaned_data["email"]
            phone = form.cleaned_data["phone"]
            project_type = form.cleaned_data["project_type"]
            budget_range = form.cleaned_data["budget_range"]
            timeline = form.cleaned_data["timeline"]
            details = form.cleaned_data["details"]
            schedule_call = form.cleaned_data.get("schedule_call_requested", False)
            preferred_time = form.cleaned_data.get("preferred_call_time", "")

            # Save via service
            QuoteService.create_quote(
                name=name,
                email=email,
                phone=phone,
                project_type=project_type,
                budget_range=budget_range,
                timeline=timeline,
                details=details,
                schedule_call_requested=schedule_call,
                preferred_call_time=preferred_time,
                request=request,
            )

            messages.success(request, "Your quote request has been submitted. We'll get back to you within 24 hours.")
            return render(request, "website/thank_you.html", {"form_type": "quote"})

        # Form errors
        messages.error(request, "Please correct the errors below.")
        return render(request, "website/quote_request.html", {"form": form})

    # GET request
    form = QuoteForm()
    return render(request, "website/quote_request.html", {"form": form})


def thank_you(request: HttpRequest) -> HttpResponse:
    """Thank you page after form submission."""
    form_type = request.GET.get("type", "contact")
    return render(request, "website/thank_you.html", {"form_type": form_type})


def blog(request: HttpRequest) -> HttpResponse:
    """Public blog listing page."""
    try:
        from blog.models import BlogPost
        from django.core.paginator import Paginator

        posts = BlogPost.objects.filter(is_published=True).order_by("-published_at")
        paginator = Paginator(posts, 10)
        page = request.GET.get("page", 1)
        posts_page = paginator.get_page(page)

        # Get recent posts for sidebar
        recent_posts = BlogPost.objects.filter(is_published=True).order_by("-published_at")[:5]

        context = {
            "posts": posts_page,
            "recent_posts": recent_posts,
            "page_title": "Blog & News",
        }
        return render(request, "website/blog.html", context)
    except ImportError:
        context = {
            "posts": [],
            "recent_posts": [],
            "page_title": "Blog & News",
        }
        return render(request, "website/blog.html", context)


def blog_detail(request: HttpRequest, slug: str) -> HttpResponse:
    """Public blog detail page."""
    try:
        from blog.models import BlogPost

        post = get_object_or_404(BlogPost, slug=slug, is_published=True)

        # Get recent posts for sidebar
        recent_posts = BlogPost.objects.filter(is_published=True).exclude(id=post.id).order_by("-published_at")[:5]

        context = {
            "post": post,
            "recent_posts": recent_posts,
            "page_title": post.title,
        }
        return render(request, "website/blog_detail.html", context)
    except ImportError:
        return redirect("website:blog")


def legal_privacy(request: HttpRequest) -> HttpResponse:
    """Privacy policy page - Kenya DPA compliant."""
    return render(request, "website/legal/privacy.html")


def legal_terms(request: HttpRequest) -> HttpResponse:
    """Terms of service page."""
    return render(request, "website/legal/terms.html")


def legal_refunds(request: HttpRequest) -> HttpResponse:
    """Refund policy page."""
    return render(request, "website/legal/refunds.html")


def legal_cookies(request: HttpRequest) -> HttpResponse:
    """Cookie policy page."""
    return render(request, "website/legal/cookies.html")


# =============================================================
# NEWSLETTER VIEWS
# =============================================================

@require_POST
def newsletter_subscribe(request: HttpRequest) -> HttpResponse:
    """
    Handle newsletter subscription form submission.

    When the request comes in via AJAX/fetch (the modernized forms on the
    site all set data-ajax="true"), respond with JSON so the page does not
    reload and the JS handler can show a toast notification.
    """
    is_ajax = (
        request.headers.get("X-Requested-With") == "XMLHttpRequest"
        or "application/json" in (request.headers.get("Accept") or "")
        or request.POST.get("ajax") == "1"
    )

    form = NewsletterForm(request.POST)

    if form.is_valid():
        email = form.cleaned_data["email"]

        try:
            # Detect "already subscribed" so we can show a friendly message
            # instead of treating it as an error.
            existing = NewsletterSubscriber.objects.filter(email=email).first()
            already_subscribed = bool(existing and existing.is_active)

            # Idempotent: re-use existing row or reactivate a previously unsubscribed one
            subscriber, created = NewsletterSubscriber.objects.get_or_create(
                email=email,
                defaults={"is_active": True},
            )

            if not created and not subscriber.is_active:
                subscriber.is_active = True
                subscriber.unsubscribed_at = None
                subscriber.save(update_fields=["is_active", "unsubscribed_at"])

            # Send confirmation email (skip if they're already actively
            # subscribed — no point sending duplicates).
            if not already_subscribed:
                EmailService.send_newsletter_confirmation(email, subscriber)

            # Log audit
            AuditService.log_action(
                user=None,
                action=(
                    "NEWSLETTER_ALREADY_SUBSCRIBED" if already_subscribed
                    else "NEWSLETTER_SUBSCRIBED" if created
                    else "NEWSLETTER_REACTIVATED"
                ),
                entity_type="NewsletterSubscriber",
                entity_id=subscriber.id,
                details={"email": email},
                request=request
            )

            if already_subscribed:
                message = "You're already subscribed to our newsletter — thanks for being part of the journey!"
            elif created:
                message = "Thank you for subscribing to our newsletter!"
            else:
                message = "Welcome back! Your subscription is active again."

            if is_ajax:
                return JsonResponse({"success": True, "message": message, "created": created})

            messages.success(request, message)

        except Exception as e:
            logger.error(f"Newsletter subscription failed for {email}: {str(e)}")
            if is_ajax:
                return JsonResponse(
                    {"success": False, "message": "Something went wrong. Please try again."},
                    status=500,
                )
            messages.error(request, "Something went wrong. Please try again.")

    else:
        if is_ajax:
            return JsonResponse(
                {"success": False, "message": "Please enter a valid email address."},
                status=400,
            )
        messages.error(request, "Please enter a valid email address.")

    # Fallback (non-AJAX): redirect back to the page they came from.
    referer = request.META.get("HTTP_REFERER", "/")
    response = redirect(referer)
    response["X-Robots-Tag"] = "noindex, nofollow"
    return response


def newsletter_unsubscribe(request: HttpRequest, email: str) -> HttpResponse:
    """
    Handle newsletter unsubscription.

    The unsubscribe URL embeds the subscriber's email in plaintext — these
    pages must NEVER be indexed. We send the noindex directive on the
    rendered response itself (no template dependency).
    """
    try:
        subscriber = get_object_or_404(NewsletterSubscriber, email=email, is_active=True)

        # Deactivate subscriber
        subscriber.is_active = False
        subscriber.unsubscribed_at = timezone.now()
        subscriber.save()

        # Log audit
        AuditService.log_action(
            user=None,
            action="NEWSLETTER_UNSUBSCRIBED",
            entity_type="NewsletterSubscriber",
            entity_id=subscriber.id,
            details={"email": email},
            request=request
        )

        messages.success(request, "You have been unsubscribed from our newsletter.")

    except Exception as e:
        logger.error(f"Newsletter unsubscribe failed for {email}: {str(e)}")
        messages.error(request, "Something went wrong. Please try again.")

    response = render(request, "website/newsletter_unsubscribe.html", {"email": email})
    response["X-Robots-Tag"] = "noindex, nofollow"
    return response