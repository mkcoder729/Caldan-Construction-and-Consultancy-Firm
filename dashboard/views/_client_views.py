"""
Client Management Views for Dashboard
Full CRUD operations for clients and leads.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q

from clients.models import Client
from accounts.services.audit_service import AuditService


@login_required
def client_list(request):
    """
    List all clients with filters.
    """
    queryset = Client.objects.all()

    # Filters
    status = request.GET.get('status')
    type_filter = request.GET.get('type')
    search = request.GET.get('search')

    if status:
        queryset = queryset.filter(status=status)
    if type_filter:
        queryset = queryset.filter(type=type_filter)
    if search:
        queryset = queryset.filter(
            Q(name__icontains=search) |
            Q(email__icontains=search) |
            Q(phone__icontains=search) |
            Q(company_name__icontains=search)
        )

    # Pagination
    paginator = Paginator(queryset.order_by('-created_at'), 20)
    page = request.GET.get('page', 1)
    clients = paginator.get_page(page)

    # Status counts
    status_counts = {
        'total': Client.objects.count(),
        'lead': Client.objects.filter(status='LEAD').count(),
        'active': Client.objects.filter(status='ACTIVE').count(),
        'inactive': Client.objects.filter(status='INACTIVE').count(),
        'converted': Client.objects.filter(status='CONVERTED').count(),
    }

    context = {
        'page_title': 'Clients',
        'page_icon': 'fa-users',
        'clients': clients,
        'status_counts': status_counts,
        'current_status': status,
        'search': search,
    }
    return render(request, 'clients/dashboard/admin/clients/list.html', context)


@login_required
def client_create(request):
    """
    Create a new client.
    """
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        type = request.POST.get('type', 'INDIVIDUAL')
        company_name = request.POST.get('company_name', '')
        address = request.POST.get('address', '')
        county = request.POST.get('county', '')
        town = request.POST.get('town', '')
        notes = request.POST.get('notes', '')
        status = request.POST.get('status', 'LEAD')

        client = Client.objects.create(
            name=name,
            email=email,
            phone=phone,
            type=type,
            company_name=company_name,
            address=address,
            county=county,
            town=town,
            notes=notes,
            status=status,
        )

        AuditService.log_action(
            user=request.user,
            action='CLIENT_CREATED',
            entity_type='client',
            entity_id=client.id,
            details={'name': client.name, 'email': client.email}
        )

        messages.success(request, f'Client "{name}" created successfully.')
        return redirect('dashboard:client_detail', pk=client.id)

    context = {
        'page_title': 'Create Client',
        'page_icon': 'fa-user-plus',
    }
    return render(request, 'clients/dashboard/admin/clients/create.html', context)


@login_required
def client_detail(request, pk):
    """
    View client details.
    """
    client = get_object_or_404(Client, id=pk)

    context = {
        'page_title': client.name,
        'page_icon': 'fa-info-circle',
        'client': client,
        'projects': client.projects.all(),
        'orders': client.orders.all(),
    }
    return render(request, 'clients/dashboard/admin/clients/detail.html', context)


@login_required
def client_edit(request, pk):
    """
    Edit client details.
    """
    client = get_object_or_404(Client, id=pk)

    if request.method == 'POST':
        client.name = request.POST.get('name')
        client.email = request.POST.get('email')
        client.phone = request.POST.get('phone')
        client.type = request.POST.get('type')
        client.company_name = request.POST.get('company_name', '')
        client.address = request.POST.get('address', '')
        client.county = request.POST.get('county', '')
        client.town = request.POST.get('town', '')
        client.notes = request.POST.get('notes', '')
        client.status = request.POST.get('status')
        client.save()

        AuditService.log_action(
            user=request.user,
            action='CLIENT_UPDATED',
            entity_type='client',
            entity_id=client.id,
            details={'name': client.name}
        )

        messages.success(request, f'Client "{client.name}" updated.')
        return redirect('dashboard:client_detail', pk=client.id)

    context = {
        'page_title': f'Edit {client.name}',
        'page_icon': 'fa-edit',
        'client': client,
    }
    return render(request, 'clients/dashboard/admin/clients/edit.html', context)


@login_required
def client_delete(request, pk):
    """
    Delete a client.
    """
    client = get_object_or_404(Client, id=pk)

    if request.method == 'POST':
        client_name = client.name
        client.delete()

        AuditService.log_action(
            user=request.user,
            action='CLIENT_DELETED',
            entity_type='client',
            entity_id=client.id,
            details={'name': client_name}
        )

        messages.success(request, f'Client "{client_name}" deleted.')
        return redirect('dashboard:client_list')

    context = {
        'page_title': f'Delete {client.name}',
        'page_icon': 'fa-trash',
        'client': client,
    }
    return render(request, 'clients/dashboard/admin/clients/delete.html', context)


@login_required
def client_leads(request):
    """
    View all leads (clients with LEAD status).
    """
    leads = Client.objects.filter(status='LEAD').order_by('-created_at')

    # Convert lead to active
    if request.method == 'POST':
        client_id = request.POST.get('client_id')
        client = get_object_or_404(Client, id=client_id)
        client.convert_to_active()

        AuditService.log_action(
            user=request.user,
            action='LEAD_CONVERTED',
            entity_type='client',
            entity_id=client.id,
            details={'name': client.name}
        )

        messages.success(request, f'Lead "{client.name}" converted to active client.')
        return redirect('dashboard:client_leads')

    context = {
        'page_title': 'Leads',
        'page_icon': 'fa-user-tag',
        'leads': leads,
        'count': leads.count(),
    }
    return render(request, 'clients/dashboard/admin/clients/leads.html', context)