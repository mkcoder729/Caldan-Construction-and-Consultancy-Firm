"""
Admin Views - Services App
Caldan Construction - "Building Kenya's Future, One Project at a Time."
"""

import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import models
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_http_methods

from accounts.permissions.decorators import admin_required
from services.models import Service

logger = logging.getLogger('caldan.services')


# =====================================================================
# SERVICES LIST
# =====================================================================

@login_required
@admin_required
def service_list(request):
    """
    List all services with filters and pagination.
    Sidebar Page: Services > All Services
    """
    # Get filters
    search = request.GET.get('search')
    category = request.GET.get('category')
    is_active = request.GET.get('is_active')
    page = int(request.GET.get('page', 1))

    # Build queryset
    queryset = Service.objects.all()

    if search:
        queryset = queryset.filter(
            models.Q(name__icontains=search) |
            models.Q(description__icontains=search) |
            models.Q(category__icontains=search)
        )

    if category:
        queryset = queryset.filter(category=category)

    if is_active == 'true':
        queryset = queryset.filter(is_active=True)
    elif is_active == 'false':
        queryset = queryset.filter(is_active=False)

    queryset = queryset.order_by('display_order', 'name')

    # Pagination
    per_page = 20
    total = queryset.count()
    start = (page - 1) * per_page
    end = start + per_page

    # Stats
    stats = {
        'total': Service.objects.count(),
        'active': Service.objects.filter(is_active=True).count(),
        'inactive': Service.objects.filter(is_active=False).count(),
    }

    # Category choices for filter
    category_choices = Service.Category.choices

    context = {
        'services': queryset[start:end],
        'total': total,
        'page': page,
        'total_pages': (total + per_page - 1) // per_page if total > 0 else 1,
        'search': search,
        'current_category': category,
        'current_active': is_active,
        'category_choices': category_choices,
        'stats': stats,
        'page_title': 'Services',
    }

    return render(request, 'services/dashboard/admin/services/list.html', context)


# =====================================================================
# SERVICE CREATE
# =====================================================================

@login_required
@admin_required
def service_create(request):
    """
    Create a new service.
    Sidebar Page: Services > Add Service
    """
    from services.forms import ServiceForm

    if request.method == 'POST':
        form = ServiceForm(request.POST, request.FILES)

        if form.is_valid():
            service = form.save()
            messages.success(
                request,
                f'Service "{service.name}" created successfully!'
            )
            return redirect('services:service_detail', service_id=service.id)
        else:
            messages.error(request, 'Please correct the errors below.')

    else:
        form = ServiceForm()

    context = {
        'form': form,
        'page_title': 'Add Service',
    }

    return render(request, 'services/dashboard/admin/services/create.html', context)


# =====================================================================
# SERVICE DETAIL
# =====================================================================

@login_required
@admin_required
def service_detail(request, service_id):
    """
    Service detail page.
    Sidebar Page: Services > Service Detail
    """
    service = get_object_or_404(Service, id=service_id)

    # Get linked projects
    linked_projects = service.projects.all()[:10]

    context = {
        'service': service,
        'linked_projects': linked_projects,
        'page_title': service.name,
    }

    return render(request, 'services/dashboard/admin/services/detail.html', context)


# =====================================================================
# SERVICE EDIT
# =====================================================================

@login_required
@admin_required
def service_edit(request, service_id):
    """
    Edit an existing service.
    Sidebar Page: Services > Edit Service
    """
    from services.forms import ServiceForm

    service = get_object_or_404(Service, id=service_id)

    if request.method == 'POST':
        form = ServiceForm(request.POST, request.FILES, instance=service)

        if form.is_valid():
            form.save()
            messages.success(
                request,
                f'Service "{service.name}" updated successfully!'
            )
            return redirect('services:service_detail', service_id=service.id)
        else:
            messages.error(request, 'Please correct the errors below.')

    else:
        form = ServiceForm(instance=service)

    context = {
        'form': form,
        'service': service,
        'page_title': f'Edit {service.name}',
    }

    return render(request, 'services/dashboard/admin/services/edit.html', context)


# =====================================================================
# SERVICE DELETE
# =====================================================================

@login_required
@admin_required
@require_http_methods(['POST'])
def service_delete(request, service_id):
    """
    Delete a service.
    """
    service = get_object_or_404(Service, id=service_id)
    service_name = service.name
    service.delete()
    messages.success(request, f'Service "{service_name}" deleted successfully.')
    return redirect('services:service_list')


# =====================================================================
# CATEGORY LIST
# =====================================================================

@login_required
@admin_required
def category_list(request):
    """
    View services grouped by category.
    Sidebar Page: Services > Categories
    """
    categories = []
    for category_code, category_label in Service.Category.choices:
        services = Service.objects.filter(category=category_code, is_active=True)
        categories.append({
            'code': category_code,
            'label': category_label,
            'count': services.count(),
            'services': services.order_by('display_order', 'name')[:10],
        })

    context = {
        'categories': categories,
        'page_title': 'Service Categories',
    }

    return render(request, 'services/dashboard/admin/services/categories.html', context)