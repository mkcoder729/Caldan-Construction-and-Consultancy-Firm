"""
URL Configuration for the Notifications app.
Caldan Construction - "Building Kenya's Future, One Project at a Time."
"""

from django.urls import path

from notifications.views import notification_views

app_name = 'notifications'

urlpatterns = [
    # ================================================================
    # MAIN NOTIFICATION PAGES
    # ================================================================
    path('', notification_views.notification_list, name='list'),
    path('page/<int:page>/', notification_views.notification_list, name='list_page'),

    # ================================================================
    # NOTIFICATION ACTIONS (AJAX + Standard)
    # ================================================================
    path('mark-read/<int:notification_id>/', notification_views.notification_mark_read, name='mark_read'),
    path('mark-all-read/', notification_views.notification_mark_all_read, name='mark_all_read'),
    path('delete/<int:notification_id>/', notification_views.notification_delete, name='delete'),
    path('unread-count/', notification_views.notification_unread_count, name='unread_count'),

    # ================================================================
    # API ENDPOINTS (for JavaScript fetch)
    # ================================================================
    path('api/mark-read/<int:notification_id>/', notification_views.notification_mark_read, name='api_mark_read'),
    path('api/mark-all-read/', notification_views.notification_mark_all_read, name='api_mark_all_read'),
    path('api/delete/<int:notification_id>/', notification_views.notification_delete, name='api_delete'),
    path('api/unread-count/', notification_views.notification_unread_count, name='api_unread_count'),
]