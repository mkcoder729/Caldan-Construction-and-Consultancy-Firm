"""
Views for Team app.
Caldan Construction - "Building Kenya's Future, One Project at a Time."
"""

from team.views._admin_views import (
    member_list,
    member_create,
    member_edit,
    member_detail,
    member_delete,
    member_toggle_featured,
)

from team.views._public_views import featured_members, active_members

__all__ = [
    'member_list',
    'member_create',
    'member_edit',
    'member_detail',
    'member_delete',
    'member_toggle_featured',
    'featured_members',
    'active_members',
]