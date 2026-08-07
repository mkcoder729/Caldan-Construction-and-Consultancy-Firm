"""
Inventory Management Views for Dashboard
Full CRUD operations for materials, stock, and alerts.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q

from inventory.models import Material, StockTransaction, StockAlert, Supplier
from inventory.services.stock_service import StockService
from accounts.services.audit_service import AuditService


@login_required
def material_list(request):
    """
    List all materials with filters.
    """
    queryset = Material.objects.filter(is_active=True)

    # Filters
    category = request.GET.get('category')
    search = request.GET.get('search')
    low_stock = request.GET.get('low_stock')

    if category:
        queryset = queryset.filter(category=category)
    if search:
        queryset = queryset.filter(
            Q(name__icontains=search) |
            Q(sku__icontains=search)
        )
    if low_stock:
        queryset = queryset.filter(is_low_stock=True)

    # Pagination
    paginator = Paginator(queryset.order_by('name'), 20)
    page = request.GET.get('page', 1)
    materials = paginator.get_page(page)

    # Summary stats
    summary = StockService.get_stock_summary()

    context = {
        'page_title': 'Materials',
        'page_icon': 'fa-boxes',
        'materials': materials,
        'summary': summary,
        'current_category': category,
        'search': search,
    }
    return render(request, 'inventory/dashboard/admin/inventory/materials.html', context)


@login_required
def material_create(request):
    """
    Create a new material.
    """
    if request.method == 'POST':
        name = request.POST.get('name')
        category = request.POST.get('category')
        unit = request.POST.get('unit')
        current_quantity = request.POST.get('current_quantity', 0)
        minimum_threshold = request.POST.get('minimum_threshold', 0)
        unit_cost = request.POST.get('unit_cost', 0)

        material = Material.objects.create(
            name=name,
            category=category,
            unit=unit,
            current_quantity=current_quantity,
            minimum_threshold=minimum_threshold,
            unit_cost=unit_cost,
            total_cost=float(current_quantity or 0) * float(unit_cost or 0),
            is_active=True,
        )

        AuditService.log_action(
            user=request.user,
            action='MATERIAL_CREATED',
            entity_type='material',
            entity_id=material.id,
            details={'name': material.name, 'category': material.category}
        )

        messages.success(request, f'Material "{name}" created successfully.')
        return redirect('dashboard:material_list')

    context = {
        'page_title': 'Create Material',
        'page_icon': 'fa-plus-circle',
    }
    return render(request, 'inventory/dashboard/admin/inventory/material_create.html', context)


@login_required
def material_detail(request, pk):
    """
    View material details.
    """
    material = get_object_or_404(Material, id=pk, is_active=True)

    # Get recent transactions
    transactions = material.transactions.filter(status='CONFIRMED').order_by('-transaction_date')[:20]

    context = {
        'page_title': material.name,
        'page_icon': 'fa-info-circle',
        'material': material,
        'transactions': transactions,
    }
    return render(request, 'inventory/dashboard/admin/inventory/material_detail.html', context)


@login_required
def material_edit(request, pk):
    """
    Edit material details.
    """
    material = get_object_or_404(Material, id=pk, is_active=True)

    if request.method == 'POST':
        material.name = request.POST.get('name')
        material.category = request.POST.get('category')
        material.unit = request.POST.get('unit')
        material.minimum_threshold = request.POST.get('minimum_threshold', 0)
        material.unit_cost = request.POST.get('unit_cost', 0)
        material.total_cost = material.current_quantity * material.unit_cost
        material.is_low_stock = material.current_quantity <= material.minimum_threshold
        material.save()

        AuditService.log_action(
            user=request.user,
            action='MATERIAL_UPDATED',
            entity_type='material',
            entity_id=material.id,
            details={'name': material.name}
        )

        messages.success(request, f'Material "{material.name}" updated.')
        return redirect('dashboard:material_detail', pk=material.id)

    context = {
        'page_title': f'Edit {material.name}',
        'page_icon': 'fa-edit',
        'material': material,
    }
    return render(request, 'inventory/dashboard/admin/inventory/material_edit.html', context)


@login_required
def stock_in(request):
    """
    Record stock incoming.
    """
    if request.method == 'POST':
        material_id = request.POST.get('material')
        quantity = request.POST.get('quantity')
        unit_cost = request.POST.get('unit_cost')
        notes = request.POST.get('notes', '')

        try:
            transaction = StockService.record_stock_in(
                material_id=material_id,
                quantity=float(quantity),
                performed_by=request.user,
                unit_cost=float(unit_cost) if unit_cost else None,
                notes=notes,
            )

            AuditService.log_action(
                user=request.user,
                action='STOCK_IN',
                entity_type='stock_transaction',
                entity_id=transaction.id,
                details={'material': transaction.material.name, 'quantity': quantity}
            )

            messages.success(request, f'Stock IN recorded: {quantity} units.')
            return redirect('dashboard:stock_transactions')

        except ValueError as e:
            messages.error(request, str(e))

    materials = Material.objects.filter(is_active=True)
    context = {
        'page_title': 'Stock In',
        'page_icon': 'fa-arrow-down',
        'materials': materials,
    }
    return render(request, 'inventory/dashboard/admin/inventory/stock_in.html', context)


@login_required
def stock_out(request):
    """
    Record stock outgoing.
    """
    if request.method == 'POST':
        material_id = request.POST.get('material')
        quantity = request.POST.get('quantity')
        notes = request.POST.get('notes', '')

        try:
            transaction = StockService.record_stock_out(
                material_id=material_id,
                quantity=float(quantity),
                performed_by=request.user,
                notes=notes,
            )

            AuditService.log_action(
                user=request.user,
                action='STOCK_OUT',
                entity_type='stock_transaction',
                entity_id=transaction.id,
                details={'material': transaction.material.name, 'quantity': quantity}
            )

            messages.success(request, f'Stock OUT recorded: {quantity} units.')
            return redirect('dashboard:stock_transactions')

        except ValueError as e:
            messages.error(request, str(e))

    materials = Material.objects.filter(is_active=True)
    context = {
        'page_title': 'Stock Out',
        'page_icon': 'fa-arrow-up',
        'materials': materials,
    }
    return render(request, 'inventory/dashboard/admin/inventory/stock_out.html', context)


@login_required
def stock_transactions(request):
    """
    View all stock transactions.
    """
    queryset = StockTransaction.objects.filter(status='CONFIRMED').order_by('-transaction_date')

    # Filters
    material_id = request.GET.get('material')
    transaction_type = request.GET.get('type')

    if material_id:
        queryset = queryset.filter(material_id=material_id)
    if transaction_type:
        queryset = queryset.filter(type=transaction_type)

    paginator = Paginator(queryset, 30)
    page = request.GET.get('page', 1)
    transactions = paginator.get_page(page)

    context = {
        'page_title': 'Stock Transactions',
        'page_icon': 'fa-exchange-alt',
        'transactions': transactions,
        'materials': Material.objects.filter(is_active=True),
    }
    return render(request, 'inventory/dashboard/admin/inventory/transactions.html', context)


@login_required
def stock_alerts(request):
    """
    View stock alerts.
    """
    alerts = StockAlert.objects.filter(status='OPEN').order_by('-created_at')

    # Resolve alert
    if request.method == 'POST':
        alert_id = request.POST.get('alert_id')
        alert = get_object_or_404(StockAlert, id=alert_id)
        alert.status = 'RESOLVED'
        alert.resolved_at = timezone.now()
        alert.save()

        messages.success(request, 'Alert resolved.')
        return redirect('dashboard:stock_alerts')

    context = {
        'page_title': 'Stock Alerts',
        'page_icon': 'fa-exclamation-triangle',
        'alerts': alerts,
        'count': alerts.count(),
    }
    return render(request, 'inventory/dashboard/admin/inventory/alerts.html', context)