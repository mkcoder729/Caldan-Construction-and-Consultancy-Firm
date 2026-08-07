"""
Public Views - Services App (for website)
Caldan Construction - "Building Kenya's Future, One Project at a Time."
"""

import logging

from django.http import JsonResponse
from django.shortcuts import get_object_or_404

from services.models import Service

logger = logging.getLogger('caldan.services')


def public_services(request):
    """
    API endpoint for all active services (public).
    Used by the website to display services.
    """
    limit = request.GET.get('limit', 20)
    try:
        limit = int(limit)
    except ValueError:
        limit = 20

    services = Service.objects.filter(is_active=True).order_by('display_order', 'name')[:limit]

    data = []
    for service in services:
        data.append({
            'id': service.id,
            'name': service.name,
            'category': service.get_category_display(),
            'slug': service.slug,
            'description': service.description,
            'icon': service.icon,
            'image_url': service.image.url if service.image else None,
            'features': service.features,
        })

    return JsonResponse({
        'success': True,
        'count': len(data),
        'services': data,
    })


def public_service_detail(request, slug):
    """
    API endpoint for a single service (public).
    """
    try:
        service = get_object_or_404(Service, slug=slug, is_active=True)

        data = {
            'id': service.id,
            'name': service.name,
            'category': service.get_category_display(),
            'slug': service.slug,
            'description': service.description,
            'long_description': service.long_description,
            'icon': service.icon,
            'image_url': service.image.url if service.image else None,
            'features': service.features,
            'display_order': service.display_order,
        }

        return JsonResponse({
            'success': True,
            'service': data,
        })

    except Exception as e:
        logger.error(f"Public service detail failed: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Service not found',
        }, status=404)


def public_categories(request):
    """
    API endpoint for all service categories with counts (public).
    """
    categories = []
    for category_code, category_label in Service.Category.choices:
        count = Service.objects.filter(category=category_code, is_active=True).count()
        categories.append({
            'code': category_code,
            'label': category_label,
            'count': count,
        })

    return JsonResponse({
        'success': True,
        'categories': categories,
    })