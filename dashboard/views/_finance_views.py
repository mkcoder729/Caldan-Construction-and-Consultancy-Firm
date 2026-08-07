"""
Financial Management Views for Dashboard
Payments, expenses, and budget tracking.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Sum

from finances.models import Payment, Expense, Budget
from projects.models import Project
from accounts.services.audit_service import AuditService
from django.utils import timezone


@login_required
def payment_list(request):
    """
    List all payments with filters.
    """
    queryset = Payment.objects.all().order_by('-payment_date')

    # Filters
    project_id = request.GET.get('project')
    status = request.GET.get('status')
    type_filter = request.GET.get('type')
    search = request.GET.get('search')

    if project_id:
        queryset = queryset.filter(project_id=project_id)
    if status:
        queryset = queryset.filter(status=status)
    if type_filter:
        queryset = queryset.filter(type=type_filter)
    if search:
        queryset = queryset.filter(
            Q(description__icontains=search) |
            Q(paid_to__icontains=search) |
            Q(reference__icontains=search)
        )

    # Pagination
    paginator = Paginator(queryset, 20)
    page = request.GET.get('page', 1)
    payments = paginator.get_page(page)

    # Summary stats
    total_amount = queryset.aggregate(total=Sum('amount'))['total'] or 0

    context = {
        'page_title': 'Payments',
        'page_icon': 'fa-money-bill-wave',
        'payments': payments,
        'projects': Project.objects.filter(is_archived=False),
        'total_amount': float(total_amount),
        'total_count': queryset.count(),
        'current_status': status,
        'search': search,
    }
    return render(request, 'finances/dashboard/admin/finances/payments.html', context)


@login_required
def payment_create(request):
    """
    Record a new payment.
    """
    if request.method == 'POST':
        project_id = request.POST.get('project')
        amount = request.POST.get('amount')
        payment_type = request.POST.get('type')
        method = request.POST.get('method')
        description = request.POST.get('description')
        paid_to = request.POST.get('paid_to')
        payment_date = request.POST.get('payment_date')
        reference = request.POST.get('reference', '')
        status = request.POST.get('status', 'PENDING')

        project = get_object_or_404(Project, id=project_id, is_archived=False)

        payment = Payment.objects.create(
            project=project,
            amount=amount,
            type=payment_type,
            method=method,
            description=description,
            paid_to=paid_to,
            payment_date=payment_date or timezone.now().date(),
            reference=reference,
            status=status,
        )

        AuditService.log_action(
            user=request.user,
            action='PAYMENT_RECORDED',
            entity_type='payment',
            entity_id=payment.id,
            details={'amount': amount, 'project': project.name}
        )

        messages.success(request, f'Payment of KES {amount} recorded.')
        return redirect('dashboard:payment_detail', pk=payment.id)

    context = {
        'page_title': 'Record Payment',
        'page_icon': 'fa-plus-circle',
        'projects': Project.objects.filter(is_archived=False),
    }
    return render(request, 'finances/dashboard/admin/finances/payment_create.html', context)


@login_required
def payment_detail(request, pk):
    """
    View payment details.
    """
    payment = get_object_or_404(Payment, id=pk)

    context = {
        'page_title': f'Payment #{payment.id}',
        'page_icon': 'fa-info-circle',
        'payment': payment,
    }
    return render(request, 'finances/dashboard/admin/finances/payment_detail.html', context)


@login_required
def payment_edit(request, pk):
    """
    Edit payment details.
    """
    payment = get_object_or_404(Payment, id=pk)

    if request.method == 'POST':
        payment.amount = request.POST.get('amount')
        payment.type = request.POST.get('type')
        payment.method = request.POST.get('method')
        payment.description = request.POST.get('description')
        payment.paid_to = request.POST.get('paid_to')
        payment.payment_date = request.POST.get('payment_date')
        payment.reference = request.POST.get('reference', '')
        payment.status = request.POST.get('status')
        payment.save()

        AuditService.log_action(
            user=request.user,
            action='PAYMENT_UPDATED',
            entity_type='payment',
            entity_id=payment.id,
            details={'amount': payment.amount}
        )

        messages.success(request, 'Payment updated successfully.')
        return redirect('dashboard:payment_detail', pk=payment.id)

    context = {
        'page_title': f'Edit Payment #{payment.id}',
        'page_icon': 'fa-edit',
        'payment': payment,
        'projects': Project.objects.filter(is_archived=False),
    }
    return render(request, 'finances/dashboard/admin/finances/payment_edit.html', context)


@login_required
def expense_list(request):
    """
    List all expenses with filters.
    """
    queryset = Expense.objects.all().order_by('-expense_date')

    project_id = request.GET.get('project')
    category = request.GET.get('category')
    search = request.GET.get('search')

    if project_id:
        queryset = queryset.filter(project_id=project_id)
    if category:
        queryset = queryset.filter(category=category)
    if search:
        queryset = queryset.filter(
            Q(description__icontains=search) |
            Q(vendor_name__icontains=search)
        )

    paginator = Paginator(queryset, 20)
    page = request.GET.get('page', 1)
    expenses = paginator.get_page(page)

    total_amount = queryset.aggregate(total=Sum('amount'))['total'] or 0

    context = {
        'page_title': 'Expenses',
        'page_icon': 'fa-receipt',
        'expenses': expenses,
        'projects': Project.objects.filter(is_archived=False),
        'total_amount': float(total_amount),
        'total_count': queryset.count(),
        'search': search,
    }
    return render(request, 'finances/dashboard/admin/finances/expenses.html', context)


@login_required
def expense_create(request):
    """
    Record a new expense.
    """
    if request.method == 'POST':
        project_id = request.POST.get('project')
        amount = request.POST.get('amount')
        category = request.POST.get('category')
        description = request.POST.get('description')
        expense_date = request.POST.get('expense_date')
        vendor_name = request.POST.get('vendor_name', '')
        notes = request.POST.get('notes', '')

        project = get_object_or_404(Project, id=project_id, is_archived=False)

        expense = Expense.objects.create(
            project=project,
            amount=amount,
            category=category,
            description=description,
            expense_date=expense_date or timezone.now().date(),
            vendor_name=vendor_name,
            notes=notes,
            created_by=request.user,
        )

        AuditService.log_action(
            user=request.user,
            action='EXPENSE_RECORDED',
            entity_type='expense',
            entity_id=expense.id,
            details={'amount': amount, 'category': category}
        )

        messages.success(request, f'Expense of KES {amount} recorded.')
        return redirect('dashboard:expense_list')

    context = {
        'page_title': 'Record Expense',
        'page_icon': 'fa-plus-circle',
        'projects': Project.objects.filter(is_archived=False),
    }
    return render(request, 'finances/dashboard/admin/finances/expense_create.html', context)


@login_required
def budget_list(request):
    """
    View project budgets.
    """
    project_id = request.GET.get('project')
    budgets = Budget.objects.all()

    if project_id:
        budgets = budgets.filter(project_id=project_id)

    context = {
        'page_title': 'Budgets',
        'page_icon': 'fa-chart-pie',
        'budgets': budgets,
        'projects': Project.objects.filter(is_archived=False),
        'current_project': project_id,
    }
    return render(request, 'finances/dashboard/admin/finances/budgets.html', context)


@login_required
def budget_edit(request, pk):
    """
    Edit budget allocation.
    """
    budget = get_object_or_404(Budget, id=pk)

    if request.method == 'POST':
        budget.allocated = request.POST.get('allocated')
        budget.description = request.POST.get('description', '')
        budget.save()

        AuditService.log_action(
            user=request.user,
            action='BUDGET_UPDATED',
            entity_type='budget',
            entity_id=budget.id,
            details={'allocated': budget.allocated}
        )

        messages.success(request, 'Budget updated successfully.')
        return redirect('dashboard:budget_list')

    context = {
        'page_title': 'Edit Budget',
        'page_icon': 'fa-edit',
        'budget': budget,
    }
    return render(request, 'finances/dashboard/admin/finances/budget_edit.html', context)