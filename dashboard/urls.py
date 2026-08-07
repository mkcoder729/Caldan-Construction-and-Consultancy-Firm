"""
URL Configuration for the Dashboard app.
Caldan Construction - "Building Kenya's Future, One Project at a Time."
"""

from django.urls import path, include
from django.contrib.auth.decorators import login_required

from dashboard.views import (
    _overview_views,
    _analytics_views,
    _activity_views,
    _settings_views,
    _inventory_views,
    _topbar_views,
    _quote_views,
    _contact_views,
)

app_name = 'dashboard'

urlpatterns = [
    # ===== OVERVIEW SECTION =====
    path('', _overview_views.dashboard_home, name='overview'),
    path('analytics/', _analytics_views.analytics_dashboard, name='analytics'),
    path('activity/', _activity_views.activity_feed, name='activity'),
    path('activity/export/pdf/', _activity_views.activity_export_pdf, name='activity_export_pdf'),

    # ===== API ENDPOINTS (JSON) =====
    path('api/search/', _topbar_views.global_search, name='api_search'),

    # ===== NOTIFICATIONS SECTION =====
    # Route to notifications app
    path('notifications/', include('notifications.urls', namespace='notifications')),

    # ===== PROJECTS SECTION =====
    # Route to projects app (under admin-projects namespace)
    path('projects/', include(('projects.urls', 'admin_projects'), namespace='admin_projects')),

    # ===== INVENTORY SECTION =====
    path('inventory/materials/', _inventory_views.material_list, name='material_list'),
    path('inventory/materials/create/', _inventory_views.material_create, name='material_create'),
    path('inventory/materials/<int:pk>/', _inventory_views.material_detail, name='material_detail'),
    path('inventory/materials/<int:pk>/edit/', _inventory_views.material_edit, name='material_edit'),
    path('inventory/stock-in/', _inventory_views.stock_in, name='stock_in'),
    path('inventory/stock-out/', _inventory_views.stock_out, name='stock_out'),
    path('inventory/transactions/', _inventory_views.stock_transactions, name='stock_transactions'),
    path('inventory/alerts/', _inventory_views.stock_alerts, name='stock_alerts'),

    # ===== QUOTES SECTION =====
    path('quotes/', _quote_views.quote_list, name='quote_list'),
    path('quotes/<int:quote_id>/', _quote_views.quote_detail, name='quote_detail'),
    path('quotes/<int:quote_id>/delete/', _quote_views.quote_delete, name='quote_delete'),
    path('quotes/<int:quote_id>/toggle-replied/', _quote_views.quote_toggle_replied, name='quote_toggle_replied'),

    # ===== CONTACT MESSAGES SECTION =====
    path('messages/', _contact_views.contact_list, name='contact_list'),
    path('messages/<int:contact_id>/', _contact_views.contact_detail, name='contact_detail'),
    path('messages/<int:contact_id>/delete/', _contact_views.contact_delete, name='contact_delete'),
    path('messages/<int:contact_id>/toggle-replied/', _contact_views.contact_toggle_replied, name='contact_toggle_replied'),

    # ===== SETTINGS SECTION =====
    path('settings/general/', _settings_views.general_settings, name='general_settings'),
    path('settings/appearance/', _settings_views.appearance_settings, name='appearance_settings'),
    path('settings/profile/', _settings_views.profile_view, name='profile_view'),
    path('settings/profile/edit/', _settings_views.profile_edit, name='profile_edit'),
    path('settings/change-password/', _settings_views.change_password, name='change_password'),
    path('settings/security/', _settings_views.security_settings, name='security_settings'),
    path('settings/notifications/', _settings_views.notification_settings, name='notification_settings'),
    path('settings/data-management/', _settings_views.data_management, name='data_management'),
    path('settings/services/', _settings_views.services_settings, name='services_settings'),
    path('settings/audit-log/', _settings_views.audit_log, name='audit_log'),
    path('settings/audit-log/export/', _settings_views.audit_export, name='audit_export'),
    path('settings/audit-log/verify/', _settings_views.audit_verify, name='audit_verify'),
]