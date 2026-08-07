"""
URL Configuration for Services app.
Caldan Construction - "Building Kenya's Future, One Project at a Time."
"""

from django.urls import path

from services.views import _admin_views as admin_views
from services.views import _public_views as public_views

app_name = 'services'

urlpatterns = [
    # =====================================================================
    # ADMIN URLS (for dashboard)
    # =====================================================================
    path('', admin_views.service_list, name='service_list'),
    path('create/', admin_views.service_create, name='service_create'),
    path('categories/', admin_views.category_list, name='category_list'),
    path('<int:service_id>/', admin_views.service_detail, name='service_detail'),
    path('<int:service_id>/edit/', admin_views.service_edit, name='service_edit'),
    path('<int:service_id>/delete/', admin_views.service_delete, name='service_delete'),

    # =====================================================================
    # PUBLIC API URLS (for website to consume)
    # =====================================================================
    path('public/all/', public_views.public_services, name='public_services'),
    path('public/<slug:slug>/', public_views.public_service_detail, name='public_service_detail'),
    path('public/categories/', public_views.public_categories, name='public_categories'),
]