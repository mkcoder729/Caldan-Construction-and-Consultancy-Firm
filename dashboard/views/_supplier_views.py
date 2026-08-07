"""
Supplier Management Views for Dashboard
Full CRUD operations for suppliers.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q

from inventory.models import Supplier, Material
from accounts.services.audit_service import AuditService


@login_required
def supplier_list(request):
    """
    List all suppliers with filters.
    """
    queryset = Supplier.objects.filter(is_active=True)

    # Filters
    search = request.GET.get('search')
    if search:
        queryset = queryset.filter(
            Q(name__icontains=search) |
            Q(contact_person__icontains=search) |
            Q(email__icontains=search) |
            Q(phone__icontains=search)
        )

    # Pagination
    paginator = Paginator(queryset.order_by('name'), 20)
    page = request.GET.get('page', 1)
    suppliers = paginator.get_page(page)

    context = {
        'page_title': 'Suppliers',
        'page_icon': 'fa-truck',
        'suppliers': suppliers,
        'search': search,
        'total': queryset.count(),
    }
    return render(request, 'inventory/dashboard/admin/suppliers/list.html', context)


@login_required
def supplier_create(request):
    """
    Create a new supplier.
    """
    if request.method == 'POST':
        name = request.POST.get('name')
        contact_person = request.POST.get('contact_person', '')
        phone = request.POST.get('phone')
        email = request.POST.get('email', '')
        address = request.POST.get('address', '')
        notes = request.POST.get('notes', '')

        supplier = Supplier.objects.create(
            name=name,
            contact_person=contact_person,
            phone=phone,
            email=email,
            address=address,
            notes=notes,
            is_active=True,
        )

        AuditService.log_action(
            user=request.user,
            action='SUPPLIER_CREATED',
            entity_type='supplier',
            entity_id=supplier.id,
            details={'name': supplier.name}
        )

        messages.success(request, f'Supplier "{name}" created successfully.')
        return redirect('dashboard:supplier_list')

    context = {
        'page_title': 'Create Supplier',
        'page_icon': 'fa-plus-circle',
    }
    return render(request, 'inventory/dashboard/admin/suppliers/create.html', context)


@login_required
def supplier_detail(request, pk):
    """
    View supplier details.
    """
    supplier = get_object_or_404(Supplier, id=pk, is_active=True)

    # Get materials from this supplier
    materials = supplier.materials.filter(is_active=True)

    context = {
        'page_title': supplier.name,
        'page_icon': 'fa-info-circle',
        'supplier': supplier,
        'materials': materials,
    }
    return render(request, 'inventory/dashboard/admin/suppliers/detail.html', context)


@login_required
def supplier_edit(request, pk):
    """
    Edit supplier details.
    """
    supplier = get_object_or_404(Supplier, id=pk, is_active=True)

    if request.method == 'POST':
        supplier.name = request.POST.get('name')
        supplier.contact_person = request.POST.get('contact_person', '')
        supplier.phone = request.POST.get('phone')
        supplier.email = request.POST.get('email', '')
        supplier.address = request.POST.get('address', '')
        supplier.notes = request.POST.get('notes', '')
        supplier.save()

        AuditService.log_action(
            user=request.user,
            action='SUPPLIER_UPDATED',
            entity_type='supplier',
            entity_id=supplier.id,
            details={'name': supplier.name}
        )

        messages.success(request, f'Supplier "{supplier.name}" updated.')
        return redirect('dashboard:supplier_detail', pk=supplier.id)

    context = {
        'page_title': f'Edit {supplier.name}',
        'page_icon': 'fa-edit',
        'supplier': supplier,
    }
    return render(request, 'inventory/dashboard/admin/suppliers/edit.html', context)


@login_required
def supplier_delete(request, pk):
    """
    Soft delete a supplier.
    """
    supplier = get_object_or_404(Supplier, id=pk, is_active=True)

    if request.method == 'POST':
        supplier.is_active = False
        supplier.save()

        AuditService.log_action(
            user=request.user,
            action='SUPPLIER_DELETED',
            entity_type='supplier',
            entity_id=supplier.id,
            details={'name': supplier.name}
        )

        messages.success(request, f'Supplier "{supplier.name}" deleted.')
        return redirect('dashboard:supplier_list')

    context = {
        'page_title': f'Delete {supplier.name}',
        'page_icon': 'fa-trash',
        'supplier': supplier,
    }
    return render(request, 'inventory/dashboard/admin/suppliers/delete.html', context)