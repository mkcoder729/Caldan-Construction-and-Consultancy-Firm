"""
Public Views - Team App (for website)
Caldan Construction - "Building Kenya's Future, One Project at a Time."
"""

import logging

from django.http import JsonResponse

from team.services import TeamService

logger = logging.getLogger('caldan.team')


def featured_members(request):
    """
    API endpoint for featured team members (public).
    Used by the About page to display featured team members.
    """
    limit = request.GET.get('limit', 10)
    try:
        limit = int(limit)
    except ValueError:
        limit = 10

    members = TeamService.get_featured_members(limit=limit)

    # Format for JSON response
    data = []
    for member in members:
        data.append({
            'id': member.id,
            'name': member.name,
            'role': member.get_role_display(),
            'title': member.title,
            'bio': member.bio[:200] if member.bio else '',
            'photo_url': member.photo.url if member.photo else None,
            'linkedin': member.linkedin,
            'twitter': member.twitter,
        })

    return JsonResponse({
        'success': True,
        'count': len(data),
        'members': data,
    })


def active_members(request):
    """
    API endpoint for all active team members (public).
    """
    limit = request.GET.get('limit', 50)
    try:
        limit = int(limit)
    except ValueError:
        limit = 50

    members = TeamService.get_active_members(limit=limit)

    data = []
    for member in members:
        data.append({
            'id': member.id,
            'name': member.name,
            'role': member.get_role_display(),
            'title': member.title,
            'photo_url': member.photo.url if member.photo else None,
        })

    return JsonResponse({
        'success': True,
        'count': len(data),
        'members': data,
    })