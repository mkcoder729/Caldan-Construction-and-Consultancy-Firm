"""
Admin Views - Clients App
Caldan Construction - "Building Kenya's Future, One Project at a Time."
"""

import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_http_methods

from accounts.permissions.decorators import admin_required
from clients.forms import ClientForm
from clients.services import ClientService
from clients.models import Client

logger = logging.getLogger('caldan.clients')


# =====================================================================
# CLIENT LIST
# =====================================================================

@login_required
@admin_required
def client_list(request):
    """
    List all clients with filters and pagination.
    Sidebar Page: Clients > All Clients
    """
    # Get filters
    search = request.GET.get('search')
    status = request.GET.get('status')
    client_type = request.GET.get('type')
    source = request.GET.get('source')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    page = int(request.GET.get('page', 1))

    filters = {
        'search': search,
        'status': status,
        'type': client_type,
        'source': source,
        'date_from': date_from,
        'date_to': date_to,
        'exclude_leads': True,  # Exclude leads from client list
    }

    # Get clients
    result = ClientService.get_all_clients(
        filters=filters,
        page=page,
        per_page=20
    )

    # Get stats
    stats = ClientService.get_stats()

    # Status choices for filter
    status_choices = Client.Status.choices
    type_choices = Client.Type.choices

    context = {
        'clients': result['clients'],
        'total': result['total'],
        'page': result['page'],
        'total_pages': result['total_pages'],
        'search': search,
        'current_status': status,
        'current_type': client_type,
        'current_source': source,
        'date_from': date_from,
        'date_to': date_to,
        'status_choices': status_choices,
        'type_choices': type_choices,
        'stats': stats,
        'page_title': 'Clients',
    }

    return render(request, 'clients/dashboard/admin/clients/list.html', context)


# =====================================================================
# CLIENT CREATE
# =====================================================================

@login_required
@admin_required
def client_create(request):
    """
    Create a new client.
    Sidebar Page: Clients > Create Client
    """
    if request.method == 'POST':
        form = ClientForm(request.POST)

        if form.is_valid():
            # Create client via service
            client = ClientService.create_client(
                data=form.cleaned_data,
                user=request.user
            )

            messages.success(
                request,
                f'Client "{client.name or client.company_name}" created successfully!'
            )

            return redirect('clients:client_detail', client_id=client.id)

        else:
            messages.error(request, 'Please correct the errors below.')

    else:
        # Pre-fill type from query param
        initial = {}
        client_type = request.GET.get('type')
        if client_type:
            initial['type'] = client_type
        form = ClientForm(initial=initial)

    context = {
        'form': form,
        'page_title': 'Create Client',
    }

    return render(request, 'clients/dashboard/admin/clients/create.html', context)


# =====================================================================
# CLIENT DETAIL
# =====================================================================

@login_required
@admin_required
def client_detail(request, client_id):
    """
    Client detail page.
    Sidebar Page: Clients > Client Detail
    """
    client = ClientService.get_client(client_id)

    # Get related projects and orders
    projects = client.projects.all()[:10]
    orders = client.orders.all()[:10]

    context = {
        'client': client,
        'projects': projects,
        'orders': orders,
        'page_title': client.name or client.company_name or client.email,
    }

    return render(request, 'clients/dashboard/admin/clients/detail.html', context)


# =====================================================================
# CLIENT EDIT
# =====================================================================

@login_required
@admin_required
def client_edit(request, client_id):
    """
    Edit an existing client.
    Sidebar Page: Clients > Edit Client
    """
    client = ClientService.get_client(client_id)

    if request.method == 'POST':
        form = ClientForm(request.POST, instance=client)

        if form.is_valid():
            # Update via service
            client = ClientService.update_client(
                client_id=client.id,
                data=form.cleaned_data,
                user=request.user
            )

            messages.success(
                request,
                f'Client "{client.name or client.company_name}" updated successfully!'
            )

            return redirect('clients:client_detail', client_id=client.id)

        else:
            messages.error(request, 'Please correct the errors below.')

    else:
        form = ClientForm(instance=client)

    context = {
        'form': form,
        'client': client,
        'page_title': f'Edit {client.name or client.company_name}',
    }

    return render(request, 'clients/dashboard/admin/clients/edit.html', context)


# =====================================================================
# CLIENT DELETE
# =====================================================================

@login_required
@admin_required
@require_http_methods(['POST'])
def client_delete(request, client_id):
    """
    Delete a client.
    """
    try:
        ClientService.delete_client(client_id, request.user)
        messages.success(request, 'Client deleted successfully.')

    except Exception as e:
        logger.error(f"Client deletion failed: {str(e)}")
        messages.error(request, f'Deletion failed: {str(e)}')

    return redirect('clients:client_list')


# =====================================================================
# CLIENT CONVERT (Lead to Active)
# =====================================================================

@login_required
@admin_required
@require_http_methods(['POST'])
def client_convert(request, client_id):
    """
    Convert a lead to an active client.
    """
    try:
        client = ClientService.convert_to_active(client_id, request.user)
        messages.success(
            request,
            f'"{client.name or client.company_name}" converted from lead to active client!'
        )

    except ValueError as e:
        messages.error(request, str(e))
    except Exception as e:
        logger.error(f"Client conversion failed: {str(e)}")
        messages.error(request, f'Conversion failed: {str(e)}')

    return redirect('clients:client_detail', client_id=client_id)


# =====================================================================
# LEAD LIST
# =====================================================================

@login_required
@admin_required
def lead_list(request):
    """
    List all leads with filters and pagination.
    Sidebar Page: Clients > Leads
    """
    # Get filters
    search = request.GET.get('search')
    source = request.GET.get('source')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    page = int(request.GET.get('page', 1))

    filters = {
        'search': search,
        'source': source,
        'date_from': date_from,
        'date_to': date_to,
    }

    # Get leads
    result = ClientService.get_leads(
        filters=filters,
        page=page,
        per_page=20
    )

    # Get stats
    stats = ClientService.get_stats()

    # Source choices for filter (from existing leads)
    sources = Client.objects.filter(status='LEAD').values_list('source', flat=True).distinct()
    source_list = [s for s in sources if s]

    context = {
        'leads': result['leads'],
        'total': result['total'],
        'page': result['page'],
        'total_pages': result['total_pages'],
        'search': search,
        'current_source': source,
        'date_from': date_from,
        'date_to': date_to,
        'source_list': source_list,
        'stats': stats,
        'page_title': 'Leads',
    }

    return render(request, 'clients/dashboard/admin/clients/leads.html', context)


# =====================================================================
# LEAD CONVERT
# =====================================================================

@login_required
@admin_required
@require_http_methods(['POST'])
def lead_convert(request, lead_id):
    """
    Convert a lead to an active client from the leads page.
    """
    try:
        client = ClientService.convert_to_active(lead_id, request.user)
        messages.success(
            request,
            f'"{client.name or client.company_name}" converted from lead to active client!'
        )

    except ValueError as e:
        messages.error(request, str(e))
    except Exception as e:
        logger.error(f"Lead conversion failed: {str(e)}")
        messages.error(request, f'Conversion failed: {str(e)}')

    return redirect('clients:lead_list')