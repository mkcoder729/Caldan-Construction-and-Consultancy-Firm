"""
URL Configuration for Reports app.
Caldan Construction - "Building Kenya's Future, One Project at a Time."
"""

from django.urls import path

from reports.views import _admin_views as views

app_name = 'reports'

urlpatterns = [
    # Reports Dashboard
    path('', views.index, name='index'),

    # Individual Reports
    path('project/', views.project_report, name='project_report'),
    path('project/<int:project_id>/', views.project_report, name='project_report_detail'),
    path('inventory/', views.inventory_report, name='inventory_report'),
    path('financial/', views.financial_report, name='financial_report'),

    # Export & Backup
    path('export/', views.export_center, name='export_center'),
    path('export/download/', views.export_download, name='export_download'),
    path('export/data/', views.export, name='export'),
    path('export-all/', views.export, name='export_all'),
    path('export/history/', views.export_history, name='export_history'),
    path('export/history/<int:record_id>/delete/', views.export_history_delete, name='export_history_delete'),
    path('backup/', views.backup_manager, name='backup_manager'),
    path('backup/history/', views.backup_history, name='backup_history'),
    path('backup/create/', views.backup_create, name='backup_create'),
    path('backup/<int:backup_id>/restore/', views.backup_restore, name='backup_restore'),
    path('backup/<int:backup_id>/delete/', views.backup_delete, name='backup_delete'),
]