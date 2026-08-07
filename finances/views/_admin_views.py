"""
Admin Views - Finances App
Caldan Construction - "Building Kenya's Future, One Project at a Time."
"""

import json
import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from accounts.permissions.decorators import admin_required
from finances.forms import PaymentForm, ExpenseForm
from finances.services import FinancialService
from finances.models import Payment, Expense, Budget
from projects.models import Project  # <-- FIXED: Import Project from projects.models

logger = logging.getLogger('caldan.finances')


# =====================================================================
# PAYMENT LIST
# =====================================================================

@login_required
@admin_required
def payment_list(request):
    """
    List all payments with filters and pagination.
    Sidebar Page: Finances > Payments
    """
    # Get filters
    search = request.GET.get('search')
    project_id = request.GET.get('project')
    status = request.GET.get('status')
    payment_type = request.GET.get('type')
    method = request.GET.get('method')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    page = int(request.GET.get('page', 1))

    filters = {
        'search': search,
        'project': project_id,
        'status': status,
        'type': payment_type,
        'method': method,
        'date_from': date_from,
        'date_to': date_to,
    }

    # Get payments
    result = FinancialService.get_all_payments(
        filters=filters,
        page=page,
        per_page=20
    )

    # Get stats
    stats = FinancialService.get_stats()

    # Get projects for filter
    projects = Project.objects.filter(is_archived=False).order_by('name')

    # Choices for filters
    status_choices = Payment.Status.choices
    type_choices = Payment.Type.choices
    method_choices = Payment.Method.choices

    context = {
        'payments': result['payments'],
        'total': result['total'],
        'page': result['page'],
        'total_pages': result['total_pages'],
        'search': search,
        'current_project': project_id,
        'current_status': status,
        'current_type': payment_type,
        'current_method': method,
        'date_from': date_from,
        'date_to': date_to,
        'projects': projects,
        'status_choices': status_choices,
        'type_choices': type_choices,
        'method_choices': method_choices,
        'stats': stats,
        'page_title': 'Payments',
    }

    return render(request, 'finances/dashboard/admin/finances/payments.html', context)


# =====================================================================
# PAYMENT CREATE
# =====================================================================

@login_required
@admin_required
def payment_create(request):
    """
    Create a new payment.
    Sidebar Page: Finances > Create Payment
    """
    if request.method == 'POST':
        form = PaymentForm(request.POST, request.FILES)

        if form.is_valid():
            # Create payment via service
            payment = FinancialService.create_payment(
                data=form.cleaned_data,
                user=request.user
            )

            messages.success(
                request,
                f'Payment of KES {payment.amount:,.2f} created successfully!'
            )

            return redirect('finances:payment_detail', payment_id=payment.id)

        else:
            messages.error(request, 'Please correct the errors below.')

    else:
        # Pre-fill project from query param
        initial = {}
        project_id = request.GET.get('project')
        if project_id:
            initial['project'] = project_id
        form = PaymentForm(initial=initial)

    context = {
        'form': form,
        'page_title': 'Create Payment',
    }

    return render(request, 'finances/dashboard/admin/finances/payment_create.html', context)


# =====================================================================
# PAYMENT DETAIL
# =====================================================================

@login_required
@admin_required
def payment_detail(request, payment_id):
    """
    Payment detail page.
    Sidebar Page: Finances > Payment Detail
    """
    payment = FinancialService.get_payment(payment_id)

    context = {
        'payment': payment,
        'page_title': f'Payment #{payment.id}',
    }

    return render(request, 'finances/dashboard/admin/finances/payment_detail.html', context)


# =====================================================================
# PAYMENT EDIT
# =====================================================================

@login_required
@admin_required
def payment_edit(request, payment_id):
    """
    Edit an existing payment.
    Sidebar Page: Finances > Edit Payment
    """
    payment = FinancialService.get_payment(payment_id)

    if request.method == 'POST':
        form = PaymentForm(request.POST, request.FILES, instance=payment)

        if form.is_valid():
            # Update via service
            payment = FinancialService.update_payment(
                payment_id=payment.id,
                data=form.cleaned_data,
                user=request.user
            )

            messages.success(
                request,
                f'Payment #{payment.id} updated successfully!'
            )

            return redirect('finances:payment_detail', payment_id=payment.id)

        else:
            messages.error(request, 'Please correct the errors below.')

    else:
        form = PaymentForm(instance=payment)

    context = {
        'form': form,
        'payment': payment,
        'page_title': f'Edit Payment #{payment.id}',
    }

    return render(request, 'finances/dashboard/admin/finances/payment_edit.html', context)


# =====================================================================
# PAYMENT DELETE
# =====================================================================

@login_required
@admin_required
@require_http_methods(['POST'])
def payment_delete(request, payment_id):
    """
    Delete a payment.
    """
    try:
        payment = FinancialService.get_payment(payment_id)
        amount = payment.amount
        FinancialService.delete_payment(payment_id, request.user)
        messages.success(request, f'Payment of KES {amount:,.2f} deleted successfully.')

    except Exception as e:
        logger.error(f"Payment deletion failed: {str(e)}")
        messages.error(request, f'Deletion failed: {str(e)}')

    return redirect('finances:payment_list')


# =====================================================================
# PAYMENT APPROVE
# =====================================================================

@login_required
@admin_required
@require_http_methods(['POST'])
def payment_approve(request, payment_id):
    """
    Approve a payment.
    """
    try:
        payment = FinancialService.approve_payment(payment_id, request.user)
        messages.success(
            request,
            f'Payment #{payment.id} approved successfully!'
        )

    except ValueError as e:
        messages.error(request, str(e))
    except Exception as e:
        logger.error(f"Payment approval failed: {str(e)}")
        messages.error(request, f'Approval failed: {str(e)}')

    return redirect('finances:payment_detail', payment_id=payment_id)


# =====================================================================
# PAYMENT COMPLETE
# =====================================================================

@login_required
@admin_required
@require_http_methods(['POST'])
def payment_complete(request, payment_id):
    """
    Complete a payment.
    """
    try:
        payment = FinancialService.complete_payment(payment_id, request.user)
        messages.success(
            request,
            f'Payment #{payment.id} marked as completed!'
        )

    except ValueError as e:
        messages.error(request, str(e))
    except Exception as e:
        logger.error(f"Payment completion failed: {str(e)}")
        messages.error(request, f'Completion failed: {str(e)}')

    return redirect('finances:payment_detail', payment_id=payment_id)


# =====================================================================
# PAYMENT CANCEL
# =====================================================================

@login_required
@admin_required
@require_http_methods(['POST'])
def payment_cancel(request, payment_id):
    """
    Cancel a payment.
    """
    try:
        reason = request.POST.get('reason', '')
        payment = FinancialService.cancel_payment(payment_id, request.user, reason)
        messages.success(
            request,
            f'Payment #{payment.id} cancelled successfully!'
        )

    except ValueError as e:
        messages.error(request, str(e))
    except Exception as e:
        logger.error(f"Payment cancellation failed: {str(e)}")
        messages.error(request, f'Cancellation failed: {str(e)}')

    return redirect('finances:payment_detail', payment_id=payment_id)


# =====================================================================
# EXPENSE LIST
# =====================================================================

@login_required
@admin_required
def expense_list(request):
    """
    List all expenses with filters and pagination.
    Sidebar Page: Finances > Expenses
    """
    # Get filters
    search = request.GET.get('search')
    project_id = request.GET.get('project')
    category = request.GET.get('category')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    page = int(request.GET.get('page', 1))

    filters = {
        'search': search,
        'project': project_id,
        'category': category,
        'date_from': date_from,
        'date_to': date_to,
    }

    # Get expenses
    result = FinancialService.get_all_expenses(
        filters=filters,
        page=page,
        per_page=20
    )

    # Get stats
    stats = FinancialService.get_stats()

    # Get projects for filter
    projects = Project.objects.filter(is_archived=False).order_by('name')

    # Choices for filters
    category_choices = Expense.Category.choices

    context = {
        'expenses': result['expenses'],
        'total': result['total'],
        'page': result['page'],
        'total_pages': result['total_pages'],
        'search': search,
        'current_project': project_id,
        'current_category': category,
        'date_from': date_from,
        'date_to': date_to,
        'projects': projects,
        'category_choices': category_choices,
        'stats': stats,
        'page_title': 'Expenses',
    }

    return render(request, 'finances/dashboard/admin/finances/expenses.html', context)


# =====================================================================
# EXPENSE CREATE
# =====================================================================

@login_required
@admin_required
def expense_create(request):
    """
    Create a new expense.
    Sidebar Page: Finances > Create Expense
    """
    if request.method == 'POST':
        form = ExpenseForm(request.POST, request.FILES)

        if form.is_valid():
            # Create expense via service
            expense = FinancialService.create_expense(
                data=form.cleaned_data,
                user=request.user
            )

            messages.success(
                request,
                f'Expense of KES {expense.amount:,.2f} created successfully!'
            )

            return redirect('finances:expense_list')

        else:
            messages.error(request, 'Please correct the errors below.')

    else:
        # Pre-fill project from query param
        initial = {}
        project_id = request.GET.get('project')
        if project_id:
            initial['project'] = project_id
        form = ExpenseForm(initial=initial)

    context = {
        'form': form,
        'page_title': 'Create Expense',
    }

    return render(request, 'finances/dashboard/admin/finances/expense_create.html', context)


# =====================================================================
# EXPENSE EDIT
# =====================================================================

@login_required
@admin_required
def expense_edit(request, expense_id):
    """
    Edit an existing expense.
    """
    expense = FinancialService.get_expense(expense_id)

    if request.method == 'POST':
        form = ExpenseForm(request.POST, request.FILES, instance=expense)

        if form.is_valid():
            expense = FinancialService.update_expense(
                expense_id=expense.id,
                data=form.cleaned_data,
                user=request.user
            )

            messages.success(
                request,
                f'Expense #{expense.id} updated successfully!'
            )

            return redirect('finances:expense_list')

        else:
            messages.error(request, 'Please correct the errors below.')

    else:
        form = ExpenseForm(instance=expense)

    context = {
        'form': form,
        'expense': expense,
        'page_title': f'Edit Expense #{expense.id}',
    }

    return render(request, 'finances/dashboard/admin/finances/expense_create.html', context)


# =====================================================================
# EXPENSE DELETE
# =====================================================================

@login_required
@admin_required
@require_http_methods(['POST'])
def expense_delete(request, expense_id):
    """
    Delete an expense.
    """
    try:
        expense = FinancialService.get_expense(expense_id)
        amount = expense.amount
        FinancialService.delete_expense(expense_id, request.user)
        messages.success(request, f'Expense of KES {amount:,.2f} deleted successfully.')

    except Exception as e:
        logger.error(f"Expense deletion failed: {str(e)}")
        messages.error(request, f'Deletion failed: {str(e)}')

    return redirect('finances:expense_list')


# =====================================================================
# BUDGET LIST
# =====================================================================

@login_required
@admin_required
def budget_list(request):
    """
    List and manage budgets.
    Sidebar Page: Finances > Budgets
    """
    project_id = request.GET.get('project')
    budgets = FinancialService.get_budgets(project_id)

    # Get projects for filter
    projects = Project.objects.filter(is_archived=False).order_by('name')

    # Calculate totals
    total_allocated = sum(b.allocated for b in budgets)
    total_spent = sum(b.spent for b in budgets)

    context = {
        'budgets': budgets,
        'projects': projects,
        'selected_project': project_id,
        'total_allocated': total_allocated,
        'total_spent': total_spent,
        'remaining': total_allocated - total_spent,
        'page_title': 'Budgets',
    }

    return render(request, 'finances/dashboard/admin/finances/budgets.html', context)


# =====================================================================
# BUDGET CREATE
# =====================================================================

@login_required
@admin_required
def budget_create(request):
    """
    Create a new budget.
    """
    if request.method == 'POST':
        data = {
            'project_id': request.POST.get('project'),
            'category': request.POST.get('category'),
            'allocated': request.POST.get('allocated'),
            'description': request.POST.get('description', ''),
        }

        try:
            project = get_object_or_404(Project, id=data['project_id'])
            budget = Budget.objects.create(
                project=project,
                category=data['category'],
                allocated=data['allocated'],
                description=data['description'],
            )

            messages.success(
                request,
                f'Budget for {project.name} - {budget.get_category_display()} created successfully!'
            )

        except Exception as e:
            logger.error(f"Budget creation failed: {str(e)}")
            messages.error(request, f'Creation failed: {str(e)}')

        return redirect('finances:budget_list')

    # GET - show form
    projects = Project.objects.filter(is_archived=False).order_by('name')
    category_choices = Budget.Category.choices

    context = {
        'projects': projects,
        'category_choices': category_choices,
        'page_title': 'Create Budget',
    }

    return render(request, 'finances/dashboard/admin/finances/budgets.html', context)


# =====================================================================
# BUDGET EDIT
# =====================================================================

@login_required
@admin_required
def budget_edit(request, budget_id):
    """
    Edit an existing budget.
    """
    budget = get_object_or_404(Budget, id=budget_id)

    if request.method == 'POST':
        try:
            budget.allocated = request.POST.get('allocated')
            budget.description = request.POST.get('description', '')
            budget.save()

            messages.success(
                request,
                f'Budget updated successfully!'
            )

        except Exception as e:
            logger.error(f"Budget update failed: {str(e)}")
            messages.error(request, f'Update failed: {str(e)}')

        return redirect('finances:budget_list')

    projects = Project.objects.filter(is_archived=False).order_by('name')
    category_choices = Budget.Category.choices

    context = {
        'budget': budget,
        'projects': projects,
        'category_choices': category_choices,
        'page_title': 'Edit Budget',
    }

    return render(request, 'finances/dashboard/admin/finances/budgets.html', context)


# =====================================================================
# BUDGET DELETE
# =====================================================================

@login_required
@admin_required
@require_http_methods(['POST'])
def budget_delete(request, budget_id):
    """
    Delete a budget.
    """
    try:
        budget = get_object_or_404(Budget, id=budget_id)
        budget.delete()
        messages.success(request, 'Budget deleted successfully.')

    except Exception as e:
        logger.error(f"Budget deletion failed: {str(e)}")
        messages.error(request, f'Deletion failed: {str(e)}')

    return redirect('finances:budget_list')


# =====================================================================
# PAYSTACK WEBHOOK
# =====================================================================

@csrf_exempt
@require_http_methods(['POST'])
def paystack_webhook(request):
    """
    Paystack webhook handler for payment events.
    """
    try:
        payload = json.loads(request.body)
        logger.info(f"Paystack webhook received: {payload.get('event')}")

        result = FinancialService.handle_paystack_webhook(payload)

        if result:
            return JsonResponse({'status': 'success'}, status=200)
        else:
            return JsonResponse({'status': 'failed'}, status=400)

    except json.JSONDecodeError:
        logger.error("Invalid JSON payload received")
        return JsonResponse({'status': 'invalid'}, status=400)
    except Exception as e:
        logger.error(f"Webhook error: {str(e)}")
        return JsonResponse({'status': 'error'}, status=500)