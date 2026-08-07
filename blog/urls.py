from django.urls import path
from blog.views.public_views import blog_list, blog_detail
from dashboard.views import _blog_views as blog_admin

app_name = "blog"

urlpatterns = [
    # =============================================================
    # ADMIN BLOG PAGES (Dashboard)
    # -------------------------------------------------------------
    # Declared FIRST so that /blog/dashboard/... matches before
    # the public <slug:slug>/ pattern below. Otherwise 'dashboard'
    # would be captured as a slug and routed to the detail view.
    # =============================================================
    path("dashboard/", blog_admin.blog_list, name="admin_list"),
    path("dashboard/create/", blog_admin.blog_create, name="admin_create"),
    path("dashboard/<int:post_id>/", blog_admin.blog_detail, name="admin_detail"),
    path("dashboard/<int:post_id>/edit/", blog_admin.blog_edit, name="admin_edit"),
    path("dashboard/<int:post_id>/delete/", blog_admin.blog_delete, name="admin_delete"),
    path("dashboard/<int:post_id>/toggle/", blog_admin.blog_toggle, name="admin_toggle"),
    path("dashboard/<int:post_id>/broadcast/", blog_admin.blog_broadcast, name="admin_broadcast"),

    # =============================================================
    # PUBLIC BLOG PAGES
    # =============================================================
    path("", blog_list, name="list"),
    path("<slug:slug>/", blog_detail, name="detail"),
]