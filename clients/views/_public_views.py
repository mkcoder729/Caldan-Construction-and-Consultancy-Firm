"""
Public Views - Clients App (for website contact/quote forms)
Caldan Construction - "Building Kenya's Future, One Project at a Time."
"""

import logging

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json

from clients.services import ClientService

logger = logging.getLogger('caldan.clients')


@csrf_exempt
@require_http_methods(['POST'])
def create_from_contact(request):
    """
    API endpoint to create a client from contact form submission.
    Used by the website contact form.
    """
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data',
        }, status=400)

    # Validate required fields
    required_fields = ['name', 'email', 'phone', 'message']
    missing_fields = [f for f in required_fields if f not in data or not data[f]]
    if missing_fields:
        return JsonResponse({
            'success': False,
            'error': f'Missing required fields: {", ".join(missing_fields)}',
        }, status=400)

    try:
        client = ClientService.create_from_contact_form(data)

        return JsonResponse({
            'success': True,
            'message': 'Contact form submitted successfully',
            'client_id': client.id,
        })

    except Exception as e:
        logger.error(f"Contact form submission failed: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Failed to process contact form. Please try again.',
        }, status=500)


@csrf_exempt
@require_http_methods(['POST'])
def create_from_quote(request):
    """
    API endpoint to create a client from quote request form.
    Used by the website quote request form.
    """
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data',
        }, status=400)

    # Validate required fields
    required_fields = ['name', 'email', 'phone', 'project_type', 'details']
    missing_fields = [f for f in required_fields if f not in data or not data[f]]
    if missing_fields:
        return JsonResponse({
            'success': False,
            'error': f'Missing required fields: {", ".join(missing_fields)}',
        }, status=400)

    try:
        client = ClientService.create_from_quote_request(data)

        return JsonResponse({
            'success': True,
            'message': 'Quote request submitted successfully',
            'client_id': client.id,
        })

    except Exception as e:
        logger.error(f"Quote request submission failed: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Failed to process quote request. Please try again.',
        }, status=500)