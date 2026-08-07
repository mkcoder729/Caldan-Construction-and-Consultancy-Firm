"""
URL Configuration for Team app.
Caldan Construction - "Building Kenya's Future, One Project at a Time."
"""

from django.urls import path

from team.views import _admin_views as admin_views
from team.views import _public_views as public_views

app_name = 'team'

urlpatterns = [
    # Admin URLs
    path('', admin_views.member_list, name='member_list'),
    path('create/', admin_views.member_create, name='member_create'),
    path('<int:member_id>/edit/', admin_views.member_edit, name='member_edit'),
    path('<int:member_id>/', admin_views.member_detail, name='member_detail'),
    path('<int:member_id>/delete/', admin_views.member_delete, name='member_delete'),
    path('<int:member_id>/toggle-featured/', admin_views.member_toggle_featured, name='member_toggle_featured'),

    # Public URL (for website about page)
    path('public/featured/', public_views.featured_members, name='public_featured'),
]