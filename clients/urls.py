"""
URL Configuration for Clients app.
Caldan Construction - "Building Kenya's Future, One Project at a Time."
"""

from django.urls import path

from clients.views import _admin_views as admin_views
from clients.views import _public_views as public_views

app_name = 'clients'

urlpatterns = [
    # =====================================================================
    # ADMIN URLS (for dashboard)
    # =====================================================================
    path('', admin_views.client_list, name='client_list'),
    path('create/', admin_views.client_create, name='client_create'),
    path('<int:client_id>/', admin_views.client_detail, name='client_detail'),
    path('<int:client_id>/edit/', admin_views.client_edit, name='client_edit'),
    path('<int:client_id>/delete/', admin_views.client_delete, name='client_delete'),
    path('<int:client_id>/convert/', admin_views.client_convert, name='client_convert'),
    path('leads/', admin_views.lead_list, name='lead_list'),
    path('leads/<int:lead_id>/convert/', admin_views.lead_convert, name='lead_convert'),

    # =====================================================================
    # PUBLIC API URLS (for website contact/quote forms)
    # =====================================================================
    path('public/create-from-contact/', public_views.create_from_contact, name='create_from_contact'),
    path('public/create-from-quote/', public_views.create_from_quote, name='create_from_quote'),
]