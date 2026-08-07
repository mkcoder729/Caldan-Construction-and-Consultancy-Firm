"""
Views for Reports app.
Caldan Construction - "Building Kenya's Future, One Project at a Time."
"""

from reports.views._admin_views import (
    index,
    project_report,
    inventory_report,
    financial_report,
    export_center,
    export_download,
    backup_manager,
    backup_history,
    backup_create,
    backup_restore,
    backup_delete,
)

__all__ = [
    'index',
    'project_report',
    'inventory_report',
    'financial_report',
    'export_center',
    'export_download',
    'backup_manager',
    'backup_history',
    'backup_create',
    'backup_restore',
    'backup_delete',
]