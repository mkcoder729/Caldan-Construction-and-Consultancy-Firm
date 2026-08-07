from django.contrib import admin
from django.utils.html import format_html
from .models.blog_post import BlogPost


@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    """Admin interface for blog posts."""

    list_display = ("title", "category", "is_published", "published_at", "created_at", "preview_image")
    list_filter = ("is_published", "category", "created_at")
    search_fields = ("title", "content", "excerpt")
    prepopulated_fields = {"slug": ("title",)}
    readonly_fields = ("created_at", "updated_at")
    ordering = ("-published_at",)

    fieldsets = (
        ("Content", {
            "fields": ("title", "slug", "excerpt", "content", "image", "category")
        }),
        ("Status", {
            "fields": ("is_published", "published_at")
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",)
        }),
    )

    def preview_image(self, obj):
        """Display thumbnail preview in admin list."""
        if obj.image:
            return format_html(
                '<img src="{}" width="80" height="60" style="object-fit:cover; border-radius:4px;" />',
                obj.image.url
            )
        return format_html(
            '<span style="color: #9CA3AF; font-size: 12px;">No image</span>'
        )
    preview_image.short_description = "Image"

    def get_queryset(self, request):
        """Optimize queryset with select_related if needed."""
        return super().get_queryset(request)

    def save_model(self, request, obj, form, change):
        """Audit log for blog post creation/update."""
        if not change:
            # New post created
            from accounts.services.audit_service import AuditService
            AuditService.log_action(
                user=request.user,
                action="BLOG_POST_CREATED",
                entity_type="BlogPost",
                entity_id=obj.id,
                details={
                    "title": obj.title,
                    "slug": obj.slug,
                    "is_published": obj.is_published
                },
                request=request
            )
        else:
            # Post updated
            from accounts.services.audit_service import AuditService
            AuditService.log_action(
                user=request.user,
                action="BLOG_POST_UPDATED",
                entity_type="BlogPost",
                entity_id=obj.id,
                details={
                    "title": obj.title,
                    "slug": obj.slug,
                    "is_published": obj.is_published
                },
                request=request
            )
        super().save_model(request, obj, form, change)

    def delete_model(self, request, obj):
        """Audit log for blog post deletion."""
        from accounts.services.audit_service import AuditService
        AuditService.log_action(
            user=request.user,
            action="BLOG_POST_DELETED",
            entity_type="BlogPost",
            entity_id=obj.id,
            details={
                "title": obj.title,
                "slug": obj.slug
            },
            request=request
        )
        super().delete_model(request, obj)