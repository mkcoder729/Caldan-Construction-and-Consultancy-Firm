"""
Views for Clients app.
Caldan Construction - "Building Kenya's Future, One Project at a Time."
"""

from clients.views._admin_views import (
    client_list,
    client_create,
    client_detail,
    client_edit,
    client_delete,
    client_convert,
    lead_list,
    lead_convert,
)

from clients.views._public_views import (
    create_from_contact,
    create_from_quote,
)

__all__ = [
    'client_list',
    'client_create',
    'client_detail',
    'client_edit',
    'client_delete',
    'client_convert',
    'lead_list',
    'lead_convert',
    'create_from_contact',
    'create_from_quote',
]