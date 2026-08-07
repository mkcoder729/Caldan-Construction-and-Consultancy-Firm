"""
Topbar-related views: global search API, quick actions, and other
helpers used by the admin topbar's search/notification components.
"""
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_GET

from dashboard.services.global_search_service import search_everything


@login_required
@require_GET
def global_search(request):
    """
    Search across pages, projects, clients, services, materials, etc.

    GET /dashboard/api/search/?q=<query>

    Response:
        {
            "success": true,
            "query": "...",
            "total": 12,
            "categories": [
                {"category": "Pages", "items": [...]},
                {"category": "Projects", "items": [...]},
                ...
            ]
        }
    """
    query = (request.GET.get('q') or '').strip()
    if len(query) < 1:
        return JsonResponse({
            'success': True,
            'query': query,
            'total': 0,
            'categories': [],
            'message': 'Start typing to search.',
        })

    try:
        result = search_everything(query)
        return JsonResponse({
            'success': True,
            'query': result['query'],
            'total': result['total'],
            'categories': result['categories'],
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'query': query,
            'total': 0,
            'categories': [],
            'error': str(e),
        }, status=500)