"""
Delivery Management Views for Dashboard
Track and manage material deliveries.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q

from inventory.models import Delivery, Supplier, Material
from accounts.services.audit_service import AuditService
from django.utils import timezone


@login_required
def delivery_list(request):
    """
    List all deliveries with filters.
    """
    queryset = Delivery.objects.all().order_by('-delivery_date')

    # Filters
    status = request.GET.get('status')
    supplier_id = request.GET.get('supplier')
    search = request.GET.get('search')

    if status:
        queryset = queryset.filter(status=status)
    if supplier_id:
        queryset = queryset.filter(supplier_id=supplier_id)
    if search:
        queryset = queryset.filter(
            Q(reference_number__icontains=search) |
            Q(notes__icontains=search)
        )

    # Pagination
    paginator = Paginator(queryset, 20)
    page = request.GET.get('page', 1)
    deliveries = paginator.get_page(page)

    context = {
        'page_title': 'Deliveries',
        'page_icon': 'fa-truck-loading',
        'deliveries': deliveries,
        'suppliers': Supplier.objects.filter(is_active=True),
        'total': queryset.count(),
        'current_status': status,
        'search': search,
    }
    return render(request, 'inventory/dashboard/admin/deliveries/list.html', context)


@login_required
def delivery_create(request):
    """
    Create a new delivery.
    """
    if request.method == 'POST':
        supplier_id = request.POST.get('supplier')
        delivery_date = request.POST.get('delivery_date')
        reference_number = request.POST.get('reference_number', '')
        notes = request.POST.get('notes', '')
        status = request.POST.get('status', 'PENDING')

        supplier = get_object_or_404(Supplier, id=supplier_id, is_active=True)

        delivery = Delivery.objects.create(
            supplier=supplier,
            delivery_date=delivery_date or timezone.now().date(),
            reference_number=reference_number,
            notes=notes,
            status=status,
        )

        AuditService.log_action(
            user=request.user,
            action='DELIVERY_CREATED',
            entity_type='delivery',
            entity_id=delivery.id,
            details={'supplier': supplier.name, 'reference': reference_number}
        )

        messages.success(request, f'Delivery created successfully.')
        return redirect('dashboard:delivery_detail', pk=delivery.id)

    context = {
        'page_title': 'Create Delivery',
        'page_icon': 'fa-plus-circle',
        'suppliers': Supplier.objects.filter(is_active=True),
    }
    return render(request, 'inventory/dashboard/admin/deliveries/create.html', context)


@login_required
def delivery_detail(request, pk):
    """
    View delivery details.
    """
    delivery = get_object_or_404(Delivery, id=pk)

    context = {
        'page_title': f'Delivery {delivery.reference_number or delivery.id}',
        'page_icon': 'fa-info-circle',
        'delivery': delivery,
    }
    return render(request, 'inventory/dashboard/admin/deliveries/detail.html', context)


@login_required
def delivery_edit(request, pk):
    """
    Edit delivery details.
    """
    delivery = get_object_or_404(Delivery, id=pk)

    if request.method == 'POST':
        supplier_id = request.POST.get('supplier')
        delivery_date = request.POST.get('delivery_date')
        reference_number = request.POST.get('reference_number', '')
        notes = request.POST.get('notes', '')
        status = request.POST.get('status')

        delivery.supplier = get_object_or_404(Supplier, id=supplier_id, is_active=True)
        delivery.delivery_date = delivery_date or delivery.delivery_date
        delivery.reference_number = reference_number
        delivery.notes = notes
        delivery.status = status
        delivery.save()

        AuditService.log_action(
            user=request.user,
            action='DELIVERY_UPDATED',
            entity_type='delivery',
            entity_id=delivery.id,
            details={'status': status}
        )

        messages.success(request, f'Delivery updated successfully.')
        return redirect('dashboard:delivery_detail', pk=delivery.id)

    context = {
        'page_title': f'Edit Delivery',
        'page_icon': 'fa-edit',
        'delivery': delivery,
        'suppliers': Supplier.objects.filter(is_active=True),
    }
    return render(request, 'inventory/dashboard/admin/deliveries/edit.html', context)


@login_required
def delivery_update_status(request, pk):
    """
    Update delivery status.
    """
    delivery = get_object_or_404(Delivery, id=pk)

    if request.method == 'POST':
        status = request.POST.get('status')
        notes = request.POST.get('notes', '')

        if status in ['PENDING', 'IN_TRANSIT', 'DELIVERED', 'CANCELLED']:
            delivery.status = status
            if notes:
                delivery.notes = f"{delivery.notes}\n\n{timezone.now()}: {notes}"
            delivery.save()

            AuditService.log_action(
                user=request.user,
                action='DELIVERY_STATUS_UPDATED',
                entity_type='delivery',
                entity_id=delivery.id,
                details={'status': status}
            )

            messages.success(request, f'Delivery status updated to {status}.')

    return redirect('dashboard:delivery_detail', pk=delivery.id)