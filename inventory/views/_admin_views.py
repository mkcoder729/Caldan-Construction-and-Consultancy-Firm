"""
Admin Views for Inventory Management.

All views are lightweight - they handle request/response,
permission checks, and delegate business logic to services.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.http import JsonResponse
from django.utils import timezone
from decimal import Decimal

from accounts.permissions.decorators import admin_required
from accounts.services.audit_service import AuditService
from accounts.models import AuditLog

from inventory.models import Material, StockTransaction, StockAlert, Supplier, Delivery
from inventory.services import StockService, AlertService
from inventory.forms import (
    MaterialForm, StockInForm, StockOutForm, SupplierForm, DeliveryForm
)

import logging

logger = logging.getLogger('caldan.inventory')


# =====================================================================
# MATERIALS CRUD
# =====================================================================

@login_required
@admin_required
def materials_list(request):
    """
    List all materials with search, filter, and pagination.
    Dashboard page: /inventory/materials/
    """
    queryset = Material.objects.filter(is_active=True).select_related('supplier')

    # Search
    search = request.GET.get('search', '')
    if search:
        queryset = queryset.filter(
            Q(name__icontains=search) |
            Q(sku__icontains=search) |
            Q(description__icontains=search)
        )

    # Filter by category
    category = request.GET.get('category', '')
    if category:
        queryset = queryset.filter(category=category)

    # Filter by low stock
    low_stock = request.GET.get('low_stock', '')
    if low_stock == 'true':
        queryset = queryset.filter(is_low_stock=True)

    # Filter by shop availability
    in_shop = request.GET.get('in_shop', '')
    if in_shop == 'true':
        queryset = queryset.filter(is_available_in_shop=True)

    # Stats
    stats = StockService.get_stock_summary()

    # Pagination
    paginator = Paginator(queryset, 25)
    page = request.GET.get('page', 1)
    materials = paginator.get_page(page)

    context = {
        'materials': materials,
        'stats': stats,
        'search': search,
        'category': category,
        'low_stock': low_stock,
        'in_shop': in_shop,
        'categories': Material.Category.choices,
        'page_title': 'Materials',
    }
    return render(request, 'inventory/dashboard/admin/inventory/materials.html', context)


@login_required
@admin_required
def material_create(request):
    """
    Create a new material.
    Dashboard page: /inventory/materials/create/
    """
    if request.method == 'POST':
        form = MaterialForm(request.POST, request.FILES)
        if form.is_valid():
            material = form.save(commit=False)
            material.created_by = request.user
            material.save()

            # Log audit
            AuditService.log_action(
                user=request.user,
                action=AuditLog.Action.MATERIAL_CREATED,
                entity_type='Material',
                entity_id=material.id,
                details={
                    'name': material.name,
                    'category': material.category,
                    'unit': material.unit,
                    'unit_cost': float(material.unit_cost),
                },
                request=request
            )

            messages.success(request, f'Material "{material.name}" created successfully.')
            return redirect('inventory:material_detail', material_id=material.id)
    else:
        form = MaterialForm()

    context = {
        'form': form,
        'page_title': 'Create Material',
    }
    return render(request, 'inventory/dashboard/admin/inventory/material_create.html', context)


@login_required
@admin_required
def material_detail(request, material_id):
    """
    View material details with transaction history.
    Dashboard page: /inventory/materials/<id>/
    """
    material = get_object_or_404(Material, id=material_id)

    # Get recent transactions
    transactions = StockService.get_material_transactions(material_id, limit=20)

    # Get active alerts
    alerts = StockAlert.objects.filter(
        material=material,
        status=StockAlert.Status.OPEN
    )

    context = {
        'material': material,
        'transactions': transactions,
        'alerts': alerts,
        'page_title': f'Material: {material.name}',
    }
    return render(request, 'inventory/dashboard/admin/inventory/material_detail.html', context)


@login_required
@admin_required
def material_edit(request, material_id):
    """
    Edit an existing material.
    Dashboard page: /inventory/materials/<id>/edit/
    """
    material = get_object_or_404(Material, id=material_id)

    if request.method == 'POST':
        form = MaterialForm(request.POST, request.FILES, instance=material)
        if form.is_valid():
            old_name = material.name
            material = form.save()

            # Log audit
            AuditService.log_action(
                user=request.user,
                action=AuditLog.Action.MATERIAL_UPDATED,
                entity_type='Material',
                entity_id=material.id,
                details={
                    'name': material.name,
                    'old_name': old_name if old_name != material.name else None,
                },
                request=request
            )

            messages.success(request, f'Material "{material.name}" updated successfully.')
            return redirect('inventory:material_detail', material_id=material.id)
    else:
        form = MaterialForm(instance=material)

    context = {
        'form': form,
        'material': material,
        'page_title': f'Edit: {material.name}',
    }
    return render(request, 'inventory/dashboard/admin/inventory/material_edit.html', context)


# =====================================================================
# STOCK TRANSACTIONS
# =====================================================================

@login_required
@admin_required
def stock_in(request):
    """
    Record stock IN transaction.
    Dashboard page: /inventory/stock-in/
    """
    if request.method == 'POST':
        form = StockInForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                transaction_obj = StockService.record_stock_in(
                    material_id=form.cleaned_data['material'].id,
                    quantity=form.cleaned_data['quantity'],
                    performed_by=request.user,
                    unit_cost=form.cleaned_data.get('unit_cost'),
                    reference=form.cleaned_data.get('reference', ''),
                    notes=form.cleaned_data.get('notes', ''),
                    receipt=request.FILES.get('receipt'),
                    receipt_number=form.cleaned_data.get('receipt_number', ''),
                    request=request
                )

                messages.success(
                    request,
                    f'Stock IN recorded: {form.cleaned_data["quantity"]} '
                    f'{form.cleaned_data["material"].get_unit_display()} of '
                    f'{form.cleaned_data["material"].name}'
                )
                return redirect('inventory:material_detail', material_id=form.cleaned_data['material'].id)

            except ValueError as e:
                messages.error(request, str(e))
            except Exception as e:
                logger.error(f"Stock IN error: {str(e)}")
                messages.error(request, 'Failed to record stock IN. Please try again.')
    else:
        form = StockInForm()

    context = {
        'form': form,
        'page_title': 'Record Stock IN',
    }
    return render(request, 'inventory/dashboard/admin/inventory/stock_in.html', context)


@login_required
@admin_required
def stock_out(request):
    """
    Record stock OUT transaction.
    Dashboard page: /inventory/stock-out/
    """
    if request.method == 'POST':
        form = StockOutForm(request.POST)
        if form.is_valid():
            try:
                transaction_obj = StockService.record_stock_out(
                    material_id=form.cleaned_data['material'].id,
                    quantity=form.cleaned_data['quantity'],
                    performed_by=request.user,
                    reference=form.cleaned_data.get('reference', ''),
                    notes=form.cleaned_data.get('notes', ''),
                    request=request
                )

                messages.success(
                    request,
                    f'Stock OUT recorded: {form.cleaned_data["quantity"]} '
                    f'{form.cleaned_data["material"].get_unit_display()} of '
                    f'{form.cleaned_data["material"].name}'
                )
                return redirect('inventory:material_detail', material_id=form.cleaned_data['material'].id)

            except ValueError as e:
                messages.error(request, str(e))
            except Exception as e:
                logger.error(f"Stock OUT error: {str(e)}")
                messages.error(request, 'Failed to record stock OUT. Please try again.')
    else:
        form = StockOutForm()

    context = {
        'form': form,
        'page_title': 'Record Stock OUT',
    }
    return render(request, 'inventory/dashboard/admin/inventory/stock_out.html', context)


@login_required
@admin_required
def transactions_list(request):
    """
    List all stock transactions with filters.
    Dashboard page: /inventory/transactions/
    """
    queryset = StockTransaction.objects.filter(
        status=StockTransaction.Status.CONFIRMED
    ).select_related('material', 'performed_by', 'cancelled_by')

    # Filter by material
    material_id = request.GET.get('material', '')
    if material_id:
        queryset = queryset.filter(material_id=material_id)

    # Filter by type
    transaction_type = request.GET.get('type', '')
    if transaction_type:
        queryset = queryset.filter(type=transaction_type)

    # Filter by date range
    date_from = request.GET.get('date_from', '')
    if date_from:
        queryset = queryset.filter(transaction_date__date__gte=date_from)

    date_to = request.GET.get('date_to', '')
    if date_to:
        queryset = queryset.filter(transaction_date__date__lte=date_to)

    # Pagination
    paginator = Paginator(queryset, 50)
    page = request.GET.get('page', 1)
    transactions = paginator.get_page(page)

    # Materials for filter dropdown
    materials = Material.objects.filter(is_active=True).order_by('name')

    context = {
        'transactions': transactions,
        'materials': materials,
        'material_id': material_id,
        'transaction_type': transaction_type,
        'date_from': date_from,
        'date_to': date_to,
        'types': StockTransaction.Type.choices,
        'page_title': 'Stock Transactions',
    }
    return render(request, 'inventory/dashboard/admin/inventory/transactions.html', context)


# =====================================================================
# STOCK ALERTS
# =====================================================================

@login_required
@admin_required
def alerts_list(request):
    """
    List all stock alerts.
    Dashboard page: /inventory/alerts/
    """
    alerts = StockAlert.objects.select_related('material', 'material__supplier', 'resolved_by')

    # Filter by status
    status = request.GET.get('status', 'OPEN')
    if status:
        alerts = alerts.filter(status=status)

    # Pagination
    paginator = Paginator(alerts, 25)
    page = request.GET.get('page', 1)
    alerts = paginator.get_page(page)

    # Stats
    stats = AlertService.get_alert_summary()

    context = {
        'alerts': alerts,
        'stats': stats,
        'status': status,
        'statuses': StockAlert.Status.choices,
        'page_title': 'Stock Alerts',
    }
    return render(request, 'inventory/dashboard/admin/inventory/alerts.html', context)


@login_required
@admin_required
def alert_resolve(request, alert_id):
    """
    Resolve a stock alert via AJAX.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid method'}, status=405)

    try:
        alert = AlertService.resolve_alert(
            alert_id=alert_id,
            resolved_by=request.user,
            notes=request.POST.get('notes', ''),
            request=request
        )

        return JsonResponse({
            'success': True,
            'message': 'Alert resolved successfully',
            'alert_id': alert.id,
        })
    except StockAlert.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Alert not found'}, status=404)
    except Exception as e:
        logger.error(f"Alert resolve error: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


# =====================================================================
# SUPPLIERS CRUD
# =====================================================================

@login_required
@admin_required
def suppliers_list(request):
    """
    List all suppliers.
    Dashboard page: /inventory/suppliers/
    """
    queryset = Supplier.objects.filter(is_active=True)

    search = request.GET.get('search', '')
    if search:
        queryset = queryset.filter(
            Q(name__icontains=search) |
            Q(contact_person__icontains=search) |
            Q(phone__icontains=search) |
            Q(email__icontains=search)
        )

    paginator = Paginator(queryset, 25)
    page = request.GET.get('page', 1)
    suppliers = paginator.get_page(page)

    context = {
        'suppliers': suppliers,
        'search': search,
        'page_title': 'Suppliers',
    }
    return render(request, 'inventory/dashboard/admin/suppliers/list.html', context)


@login_required
@admin_required
def supplier_create(request):
    """
    Create a new supplier.
    Dashboard page: /inventory/suppliers/create/
    """
    if request.method == 'POST':
        form = SupplierForm(request.POST)
        if form.is_valid():
            supplier = form.save(commit=False)
            supplier.created_by = request.user
            supplier.save()

            AuditService.log_action(
                user=request.user,
                action=AuditLog.Action.SUPPLIER_CREATED,
                entity_type='Supplier',
                entity_id=supplier.id,
                details={'name': supplier.name},
                request=request
            )

            messages.success(request, f'Supplier "{supplier.name}" created successfully.')
            return redirect('inventory:supplier_detail', supplier_id=supplier.id)
    else:
        form = SupplierForm()

    context = {
        'form': form,
        'page_title': 'Create Supplier',
    }
    return render(request, 'inventory/dashboard/admin/suppliers/create.html', context)


@login_required
@admin_required
def supplier_detail(request, supplier_id):
    """
    View supplier details.
    Dashboard page: /inventory/suppliers/<id>/
    """
    supplier = get_object_or_404(Supplier, id=supplier_id)

    # Get materials from this supplier
    materials = Material.objects.filter(supplier=supplier, is_active=True)

    # Get deliveries from this supplier
    deliveries = Delivery.objects.filter(supplier=supplier).order_by('-expected_date')[:10]

    context = {
        'supplier': supplier,
        'materials': materials,
        'deliveries': deliveries,
        'page_title': f'Supplier: {supplier.name}',
    }
    return render(request, 'inventory/dashboard/admin/suppliers/detail.html', context)


@login_required
@admin_required
def supplier_edit(request, supplier_id):
    """
    Edit a supplier.
    Dashboard page: /inventory/suppliers/<id>/edit/
    """
    supplier = get_object_or_404(Supplier, id=supplier_id)

    if request.method == 'POST':
        form = SupplierForm(request.POST, instance=supplier)
        if form.is_valid():
            form.save()

            AuditService.log_action(
                user=request.user,
                action=AuditLog.Action.SUPPLIER_UPDATED,
                entity_type='Supplier',
                entity_id=supplier.id,
                details={'name': supplier.name},
                request=request
            )

            messages.success(request, f'Supplier "{supplier.name}" updated successfully.')
            return redirect('inventory:supplier_detail', supplier_id=supplier.id)
    else:
        form = SupplierForm(instance=supplier)

    context = {
        'form': form,
        'supplier': supplier,
        'page_title': f'Edit: {supplier.name}',
    }
    return render(request, 'inventory/dashboard/admin/suppliers/edit.html', context)


@login_required
@admin_required
def supplier_delete(request, supplier_id):
    """
    Soft delete a supplier.
    Dashboard page: /inventory/suppliers/<id>/delete/
    """
    supplier = get_object_or_404(Supplier, id=supplier_id)

    if request.method == 'POST':
        # Check if supplier has materials
        if Material.objects.filter(supplier=supplier, is_active=True).exists():
            messages.error(
                request,
                f'Cannot delete "{supplier.name}". It has active materials linked to it.'
            )
            return redirect('inventory:supplier_detail', supplier_id=supplier.id)

        supplier.is_active = False
        supplier.save()

        AuditService.log_action(
            user=request.user,
            action=AuditLog.Action.SUPPLIER_DELETED,
            entity_type='Supplier',
            entity_id=supplier.id,
            details={'name': supplier.name},
            request=request
        )

        messages.success(request, f'Supplier "{supplier.name}" deleted successfully.')
        return redirect('inventory:suppliers_list')

    context = {
        'supplier': supplier,
        'page_title': f'Delete: {supplier.name}',
    }
    return render(request, 'inventory/dashboard/admin/suppliers/confirm_delete.html', context)


# =====================================================================
# DELIVERIES
# =====================================================================

@login_required
@admin_required
def deliveries_list(request):
    """
    List all deliveries.
    Dashboard page: /inventory/deliveries/
    """
    queryset = Delivery.objects.select_related('supplier', 'created_by')

    # Filter by status
    status = request.GET.get('status', '')
    if status:
        queryset = queryset.filter(status=status)

    # Filter by supplier
    supplier_id = request.GET.get('supplier', '')
    if supplier_id:
        queryset = queryset.filter(supplier_id=supplier_id)

    # Search by delivery number
    search = request.GET.get('search', '')
    if search:
        queryset = queryset.filter(delivery_number__icontains=search)

    paginator = Paginator(queryset, 25)
    page = request.GET.get('page', 1)
    deliveries = paginator.get_page(page)

    # Suppliers for filter dropdown
    suppliers = Supplier.objects.filter(is_active=True)

    context = {
        'deliveries': deliveries,
        'suppliers': suppliers,
        'status': status,
        'supplier_id': supplier_id,
        'search': search,
        'statuses': Delivery.Status.choices,
        'page_title': 'Deliveries',
    }
    return render(request, 'inventory/dashboard/admin/deliveries/list.html', context)


@login_required
@admin_required
def delivery_create(request):
    """
    Create a new delivery.
    Dashboard page: /inventory/deliveries/create/
    """
    if request.method == 'POST':
        form = DeliveryForm(request.POST, request.FILES)
        if form.is_valid():
            delivery = form.save(commit=False)
            delivery.created_by = request.user
            delivery.save()

            AuditService.log_action(
                user=request.user,
                action=AuditLog.Action.DELIVERY_CREATED,
                entity_type='Delivery',
                entity_id=delivery.id,
                details={
                    'delivery_number': delivery.delivery_number,
                    'supplier': delivery.supplier.name,
                },
                request=request
            )

            messages.success(
                request,
                f'Delivery {delivery.delivery_number} created successfully.'
            )
            return redirect('inventory:delivery_detail', delivery_id=delivery.id)
    else:
        form = DeliveryForm()

    context = {
        'form': form,
        'page_title': 'Create Delivery',
    }
    return render(request, 'inventory/dashboard/admin/deliveries/create.html', context)


@login_required
@admin_required
def delivery_detail(request, delivery_id):
    """
    View delivery details.
    Dashboard page: /inventory/deliveries/<id>/
    """
    delivery = get_object_or_404(Delivery, id=delivery_id)

    context = {
        'delivery': delivery,
        'page_title': f'Delivery: {delivery.delivery_number}',
    }
    return render(request, 'inventory/dashboard/admin/deliveries/detail.html', context)


@login_required
@admin_required
def delivery_edit(request, delivery_id):
    """
    Edit a delivery.
    Dashboard page: /inventory/deliveries/<id>/edit/
    """
    delivery = get_object_or_404(Delivery, id=delivery_id)

    if request.method == 'POST':
        form = DeliveryForm(request.POST, request.FILES, instance=delivery)
        if form.is_valid():
            form.save()

            AuditService.log_action(
                user=request.user,
                action=AuditLog.Action.DELIVERY_UPDATED,
                entity_type='Delivery',
                entity_id=delivery.id,
                details={'delivery_number': delivery.delivery_number},
                request=request
            )

            messages.success(request, f'Delivery {delivery.delivery_number} updated successfully.')
            return redirect('inventory:delivery_detail', delivery_id=delivery.id)
    else:
        form = DeliveryForm(instance=delivery)

    context = {
        'form': form,
        'delivery': delivery,
        'page_title': f'Edit: {delivery.delivery_number}',
    }
    return render(request, 'inventory/dashboard/admin/deliveries/edit.html', context)


@login_required
@admin_required
def delivery_receive(request, delivery_id):
    """
    Mark delivery as received (creates stock IN transactions for items).
    Dashboard page: /inventory/deliveries/<id>/receive/
    """
    delivery = get_object_or_404(Delivery, id=delivery_id)

    if delivery.status == Delivery.Status.DELIVERED:
        messages.warning(request, 'This delivery has already been marked as delivered.')
        return redirect('inventory:delivery_detail', delivery_id=delivery.id)

    if request.method == 'POST':
        try:
            # Process each delivery item
            for item in delivery.items.all():
                # Record stock IN for each item
                StockService.record_stock_in(
                    material_id=item.material.id,
                    quantity=item.quantity,
                    performed_by=request.user,
                    unit_cost=item.unit_cost,
                    reference=delivery.delivery_number,
                    notes=f"Delivery {delivery.delivery_number} - {delivery.supplier.name}",
                    request=request
                )

            # Mark delivery as delivered
            delivery.mark_as_delivered()

            AuditService.log_action(
                user=request.user,
                action=AuditLog.Action.DELIVERY_COMPLETED,
                entity_type='Delivery',
                entity_id=delivery.id,
                details={'delivery_number': delivery.delivery_number},
                request=request
            )

            messages.success(
                request,
                f'Delivery {delivery.delivery_number} received and stock updated successfully.'
            )
            return redirect('inventory:delivery_detail', delivery_id=delivery.id)

        except ValueError as e:
            messages.error(request, str(e))
        except Exception as e:
            logger.error(f"Delivery receive error: {str(e)}")
            messages.error(request, 'Failed to process delivery. Please try again.')

    context = {
        'delivery': delivery,
        'page_title': f'Receive: {delivery.delivery_number}',
    }
    return render(request, 'inventory/dashboard/admin/deliveries/receive.html', context)