"""
Views for Services app.
Caldan Construction - "Building Kenya's Future, One Project at a Time."
"""

from services.views._admin_views import (
    service_list,
    service_create,
    service_edit,
    service_detail,
    service_delete,
    category_list,
)

from services.views._public_views import (
    public_services,
    public_service_detail,
    public_categories,
)

__all__ = [
    'service_list',
    'service_create',
    'service_edit',
    'service_detail',
    'service_delete',
    'category_list',
    'public_services',
    'public_service_detail',
    'public_categories',
]