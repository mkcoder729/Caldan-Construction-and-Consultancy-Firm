"""
Financial Service - Complete payment, expense, and budget management.
Caldan Construction - "Building Kenya's Future, One Project at a Time."
"""

import logging
import json
from decimal import Decimal
from datetime import timedelta
from urllib.parse import urlencode

import requests
from django.conf import settings
from django.db import transaction
from django.db.models import Sum, Count, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone

from accounts.services.audit_service import AuditService
from finances.models import Payment, Expense, Budget
from projects.models import Project

logger = logging.getLogger('caldan.finances')


class FinancialService:
    """
    Service for financial management operations.
    All methods are class methods following the service-oriented architecture.
    Supports Paystack payment integration with M-Pesa STK Push.
    """

    # Paystack API endpoints
    PAYSTACK_BASE_URL = 'https://api.paystack.co'
    PAYSTACK_SECRET_KEY = settings.PAYSTACK_SECRET_KEY
    PAYSTACK_PUBLIC_KEY = settings.PAYSTACK_PUBLIC_KEY
    PAYSTACK_LIVE = settings.PAYSTACK_LIVE

    # =====================================================================
    # PAYMENT CRUD OPERATIONS
    # =====================================================================

    @classmethod
    def get_all_payments(cls, filters=None, page=1, per_page=20):
        """
        Get all payments with optional filters.
        """
        queryset = Payment.objects.all()

        if filters:
            # Search filter
            search = filters.get('search')
            if search:
                queryset = queryset.filter(
                    Q(description__icontains=search) |
                    Q(paid_to__icontains=search) |
                    Q(reference__icontains=search) |
                    Q(invoice_number__icontains=search)
                )

            # Project filter
            project = filters.get('project')
            if project:
                queryset = queryset.filter(project_id=project)

            # Status filter
            status = filters.get('status')
            if status:
                queryset = queryset.filter(status=status)

            # Type filter
            payment_type = filters.get('type')
            if payment_type:
                queryset = queryset.filter(type=payment_type)

            # Method filter
            method = filters.get('method')
            if method:
                queryset = queryset.filter(method=method)

            # Date range filter
            date_from = filters.get('date_from')
            if date_from:
                queryset = queryset.filter(payment_date__gte=date_from)

            date_to = filters.get('date_to')
            if date_to:
                queryset = queryset.filter(payment_date__lte=date_to)

        queryset = queryset.order_by('-payment_date')

        # Pagination
        start = (page - 1) * per_page
        end = start + per_page
        total = queryset.count()

        return {
            'payments': queryset[start:end],
            'total': total,
            'page': page,
            'per_page': per_page,
            'total_pages': (total + per_page - 1) // per_page if total > 0 else 1,
        }

    @classmethod
    def get_payment(cls, payment_id):
        """Get a single payment by ID."""
        return get_object_or_404(Payment, id=payment_id)

    @classmethod
    @transaction.atomic
    def create_payment(cls, data, user):
        """Create a new payment."""
        payment = Payment.objects.create(**data)

        # Update project spent amount
        if payment.project and payment.status == 'COMPLETED':
            cls._update_project_spent(payment.project)

        # Log audit
        AuditService.log_action(
            user=user,
            action='PAYMENT_CREATED',
            entity_type='Payment',
            entity_id=str(payment.id),
            details={
                'project': payment.project.name if payment.project else None,
                'amount': float(payment.amount),
                'type': payment.type,
                'method': payment.method,
                'status': payment.status,
            }
        )

        logger.info(f"Payment created: KES {payment.amount} by {user.email}")
        return payment

    @classmethod
    @transaction.atomic
    def update_payment(cls, payment_id, data, user):
        """Update an existing payment."""
        payment = cls.get_payment(payment_id)

        # Store old values for audit
        old_status = payment.status
        old_amount = float(payment.amount)

        # Update fields
        for key, value in data.items():
            setattr(payment, key, value)
        payment.save()

        # Update project spent if status changed to COMPLETED
        if payment.project and payment.status == 'COMPLETED' and old_status != 'COMPLETED':
            cls._update_project_spent(payment.project)

        # Log audit
        AuditService.log_action(
            user=user,
            action='PAYMENT_UPDATED',
            entity_type='Payment',
            entity_id=str(payment.id),
            details={
                'project': payment.project.name if payment.project else None,
                'old_amount': old_amount,
                'new_amount': float(payment.amount),
                'old_status': old_status,
                'new_status': payment.status,
            }
        )

        logger.info(f"Payment updated: KES {payment.amount} by {user.email}")
        return payment

    @classmethod
    @transaction.atomic
    def delete_payment(cls, payment_id, user):
        """Delete a payment."""
        payment = cls.get_payment(payment_id)

        # Log audit before deletion
        AuditService.log_action(
            user=user,
            action='PAYMENT_DELETED',
            entity_type='Payment',
            entity_id=str(payment.id),
            details={
                'project': payment.project.name if payment.project else None,
                'amount': float(payment.amount),
                'type': payment.type,
            }
        )

        payment.delete()

        # Update project spent
        if payment.project:
            cls._update_project_spent(payment.project)

        logger.info(f"Payment deleted by {user.email}")
        return True

    @classmethod
    @transaction.atomic
    def approve_payment(cls, payment_id, user):
        """Approve a payment (change status from PENDING to APPROVED)."""
        payment = cls.get_payment(payment_id)

        if payment.status != 'PENDING':
            raise ValueError('Only pending payments can be approved.')

        old_status = payment.status
        payment.status = 'APPROVED'
        payment.save(update_fields=['status', 'updated_at'])

        AuditService.log_action(
            user=user,
            action='PAYMENT_APPROVED',
            entity_type='Payment',
            entity_id=str(payment.id),
            details={
                'project': payment.project.name if payment.project else None,
                'amount': float(payment.amount),
                'old_status': old_status,
                'new_status': payment.status,
            }
        )

        logger.info(f"Payment {payment.id} approved by {user.email}")
        return payment

    @classmethod
    @transaction.atomic
    def complete_payment(cls, payment_id, user):
        """Complete a payment (change status to COMPLETED)."""
        payment = cls.get_payment(payment_id)

        if payment.status not in ['PENDING', 'APPROVED']:
            raise ValueError('Only pending or approved payments can be completed.')

        old_status = payment.status
        payment.status = 'COMPLETED'
        payment.save(update_fields=['status', 'updated_at'])

        # Update project spent
        if payment.project:
            cls._update_project_spent(payment.project)

        AuditService.log_action(
            user=user,
            action='PAYMENT_COMPLETED',
            entity_type='Payment',
            entity_id=str(payment.id),
            details={
                'project': payment.project.name if payment.project else None,
                'amount': float(payment.amount),
                'old_status': old_status,
                'new_status': payment.status,
            }
        )

        logger.info(f"Payment {payment.id} completed by {user.email}")
        return payment

    @classmethod
    @transaction.atomic
    def cancel_payment(cls, payment_id, user, reason=None):
        """Cancel a payment."""
        payment = cls.get_payment(payment_id)

        if payment.status == 'COMPLETED':
            raise ValueError('Completed payments cannot be cancelled.')

        old_status = payment.status
        payment.status = 'CANCELLED'
        payment.save(update_fields=['status', 'updated_at'])

        # Update project spent if it was completed
        if payment.project:
            cls._update_project_spent(payment.project)

        AuditService.log_action(
            user=user,
            action='PAYMENT_CANCELLED',
            entity_type='Payment',
            entity_id=str(payment.id),
            details={
                'project': payment.project.name if payment.project else None,
                'amount': float(payment.amount),
                'old_status': old_status,
                'new_status': payment.status,
                'reason': reason or 'No reason provided',
            }
        )

        logger.info(f"Payment {payment.id} cancelled by {user.email}")
        return payment

    @classmethod
    def _update_project_spent(cls, project):
        """Update project spent amount from completed payments."""
        total = Payment.objects.filter(
            project=project,
            status='COMPLETED'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        project.spent = total
        project.save(update_fields=['spent', 'updated_at'])

    # =====================================================================
    # EXPENSE CRUD OPERATIONS
    # =====================================================================

    @classmethod
    def get_all_expenses(cls, filters=None, page=1, per_page=20):
        """Get all expenses with optional filters."""
        queryset = Expense.objects.all()

        if filters:
            search = filters.get('search')
            if search:
                queryset = queryset.filter(
                    Q(description__icontains=search) |
                    Q(vendor_name__icontains=search) |
                    Q(receipt_number__icontains=search)
                )

            project = filters.get('project')
            if project:
                queryset = queryset.filter(project_id=project)

            category = filters.get('category')
            if category:
                queryset = queryset.filter(category=category)

            date_from = filters.get('date_from')
            if date_from:
                queryset = queryset.filter(expense_date__gte=date_from)

            date_to = filters.get('date_to')
            if date_to:
                queryset = queryset.filter(expense_date__lte=date_to)

        queryset = queryset.order_by('-expense_date')

        start = (page - 1) * per_page
        end = start + per_page
        total = queryset.count()

        return {
            'expenses': queryset[start:end],
            'total': total,
            'page': page,
            'per_page': per_page,
            'total_pages': (total + per_page - 1) // per_page if total > 0 else 1,
        }

    @classmethod
    def get_expense(cls, expense_id):
        """Get a single expense by ID."""
        return get_object_or_404(Expense, id=expense_id)

    @classmethod
    @transaction.atomic
    def create_expense(cls, data, user):
        """Create a new expense."""
        expense = Expense.objects.create(**data)

        # Update project spent if expense is linked to project
        if expense.project:
            cls._update_project_spent_from_expenses(expense.project)

        # Log audit
        AuditService.log_action(
            user=user,
            action='EXPENSE_CREATED',
            entity_type='Expense',
            entity_id=str(expense.id),
            details={
                'project': expense.project.name if expense.project else None,
                'amount': float(expense.amount),
                'category': expense.category,
                'vendor': expense.vendor_name,
            }
        )

        logger.info(f"Expense created: KES {expense.amount} by {user.email}")
        return expense

    @classmethod
    @transaction.atomic
    def update_expense(cls, expense_id, data, user):
        """Update an existing expense."""
        expense = cls.get_expense(expense_id)

        # Update fields
        for key, value in data.items():
            setattr(expense, key, value)
        expense.save()

        # Update project spent
        if expense.project:
            cls._update_project_spent_from_expenses(expense.project)

        # Log audit
        AuditService.log_action(
            user=user,
            action='EXPENSE_UPDATED',
            entity_type='Expense',
            entity_id=str(expense.id),
            details={
                'project': expense.project.name if expense.project else None,
                'amount': float(expense.amount),
                'category': expense.category,
            }
        )

        logger.info(f"Expense updated by {user.email}")
        return expense

    @classmethod
    @transaction.atomic
    def delete_expense(cls, expense_id, user):
        """Delete an expense."""
        expense = cls.get_expense(expense_id)

        # Log audit before deletion
        AuditService.log_action(
            user=user,
            action='EXPENSE_DELETED',
            entity_type='Expense',
            entity_id=str(expense.id),
            details={
                'project': expense.project.name if expense.project else None,
                'amount': float(expense.amount),
                'category': expense.category,
            }
        )

        project = expense.project
        expense.delete()

        # Update project spent
        if project:
            cls._update_project_spent_from_expenses(project)

        logger.info(f"Expense deleted by {user.email}")
        return True

    @classmethod
    def _update_project_spent_from_expenses(cls, project):
        """Update project spent amount from expenses."""
        total = Expense.objects.filter(
            project=project
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        project.spent = total
        project.save(update_fields=['spent', 'updated_at'])

    # =====================================================================
    # BUDGET OPERATIONS
    # =====================================================================

    @classmethod
    def get_budgets(cls, project_id=None):
        """Get budgets for a project or all budgets."""
        queryset = Budget.objects.all()

        if project_id:
            queryset = queryset.filter(project_id=project_id)

        return queryset.select_related('project').order_by('project__name', 'category')

    @classmethod
    def get_budget(cls, budget_id):
        """Get a single budget by ID."""
        return get_object_or_404(Budget, id=budget_id)

    @classmethod
    @transaction.atomic
    def create_budget(cls, data, user):
        """Create a new budget."""
        # Check for duplicate category on same project
        project = data.get('project')
        category = data.get('category')
        if project and Budget.objects.filter(project=project, category=category).exists():
            raise ValueError(f'Budget already exists for {project.name} - {category}')

        budget = Budget.objects.create(**data)

        AuditService.log_action(
            user=user,
            action='BUDGET_CREATED',
            entity_type='Budget',
            entity_id=str(budget.id),
            details={
                'project': budget.project.name if budget.project else None,
                'category': budget.category,
                'allocated': float(budget.allocated),
            }
        )

        logger.info(f"Budget created for {budget.project.name} by {user.email}")
        return budget

    @classmethod
    @transaction.atomic
    def update_budget(cls, budget_id, data, user):
        """Update an existing budget."""
        budget = cls.get_budget(budget_id)

        # Store old values
        old_allocated = float(budget.allocated)

        for key, value in data.items():
            setattr(budget, key, value)
        budget.save()

        AuditService.log_action(
            user=user,
            action='BUDGET_UPDATED',
            entity_type='Budget',
            entity_id=str(budget.id),
            details={
                'project': budget.project.name if budget.project else None,
                'category': budget.category,
                'old_allocated': old_allocated,
                'new_allocated': float(budget.allocated),
            }
        )

        logger.info(f"Budget updated for {budget.project.name} by {user.email}")
        return budget

    @classmethod
    @transaction.atomic
    def delete_budget(cls, budget_id, user):
        """Delete a budget."""
        budget = cls.get_budget(budget_id)

        AuditService.log_action(
            user=user,
            action='BUDGET_DELETED',
            entity_type='Budget',
            entity_id=str(budget.id),
            details={
                'project': budget.project.name if budget.project else None,
                'category': budget.category,
                'allocated': float(budget.allocated),
            }
        )

        budget.delete()

        logger.info(f"Budget deleted by {user.email}")
        return True

    @classmethod
    def get_project_financial_summary(cls, project_id):
        """Get comprehensive financial summary for a project."""
        project = get_object_or_404(Project, id=project_id)

        # Payments
        payments = Payment.objects.filter(project=project, status='COMPLETED')
        total_payments = payments.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        # Expenses
        expenses = Expense.objects.filter(project=project)
        total_expenses = expenses.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        # Budgets
        budgets = Budget.objects.filter(project=project)
        total_budget = budgets.aggregate(total=Sum('allocated'))['total'] or Decimal('0.00')

        return {
            'project': project,
            'total_payments': float(total_payments),
            'total_expenses': float(total_expenses),
            'net_position': float(total_payments - total_expenses),
            'total_budget': float(total_budget),
            'budgets': budgets,
            'recent_payments': payments.order_by('-payment_date')[:5],
            'recent_expenses': expenses.order_by('-expense_date')[:5],
        }

    # =====================================================================
    # PAYSTACK INTEGRATION
    # =====================================================================

    @classmethod
    def initiate_payment(cls, payment_id, email=None):
        """
        Initiate a Paystack payment transaction.
        Returns payment URL for redirect.
        """
        payment = cls.get_payment(payment_id)

        if payment.status != 'PENDING':
            raise ValueError('Only pending payments can be initiated.')

        if not cls.PAYSTACK_SECRET_KEY:
            raise ValueError('Paystack secret key is not configured.')

        # Use payment email or fallback
        if not email:
            email = 'customer@example.com'

        # Prepare metadata
        metadata = {
            'payment_id': payment.id,
            'project_id': payment.project.id if payment.project else None,
            'type': payment.type,
        }

        # Prepare payload
        payload = {
            'email': email,
            'amount': int(payment.amount * 100),  # Paystack uses kobo (cents)
            'currency': 'KES',
            'reference': f'PAY-{payment.id}-{timezone.now().strftime("%Y%m%d%H%M%S")}',
            'callback_url': f"{settings.PAYSTACK_CALLBACK_URL}?payment_id={payment.id}",
            'metadata': metadata,
        }

        # Add M-Pesa as channel if enabled
        if settings.MPESA_STK_PUSH_ENABLED:
            payload['channels'] = ['card', 'bank', 'ussd', 'mobile_money']

        # Make API request
        headers = {
            'Authorization': f'Bearer {cls.PAYSTACK_SECRET_KEY}',
            'Content-Type': 'application/json',
        }

        try:
            response = requests.post(
                f'{cls.PAYSTACK_BASE_URL}/transaction/initialize',
                json=payload,
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            data = response.json()

            if data.get('status'):
                # Update payment with reference
                payment.reference = payload['reference']
                payment.save(update_fields=['reference'])

                return {
                    'success': True,
                    'authorization_url': data['data']['authorization_url'],
                    'reference': payload['reference'],
                    'access_code': data['data']['access_code'],
                }
            else:
                logger.error(f"Paystack initialization failed: {data.get('message')}")
                return {
                    'success': False,
                    'error': data.get('message', 'Payment initialization failed'),
                }

        except requests.RequestException as e:
            logger.error(f"Paystack API error: {str(e)}")
            return {
                'success': False,
                'error': 'Payment service unavailable. Please try again.',
            }

    @classmethod
    def verify_payment(cls, reference):
        """
        Verify a Paystack payment transaction.
        """
        if not cls.PAYSTACK_SECRET_KEY:
            raise ValueError('Paystack secret key is not configured.')

        headers = {
            'Authorization': f'Bearer {cls.PAYSTACK_SECRET_KEY}',
            'Content-Type': 'application/json',
        }

        try:
            response = requests.get(
                f'{cls.PAYSTACK_BASE_URL}/transaction/verify/{reference}',
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            data = response.json()

            if data.get('status'):
                transaction_data = data.get('data', {})
                payment_id = transaction_data.get('metadata', {}).get('payment_id')

                if payment_id:
                    try:
                        payment = Payment.objects.get(id=payment_id)
                        if transaction_data.get('status') == 'success':
                            payment.status = 'COMPLETED'
                            payment.save(update_fields=['status', 'updated_at'])
                            if payment.project:
                                cls._update_project_spent(payment.project)

                            logger.info(f"Payment {payment.id} verified as completed via Paystack")
                            return {
                                'success': True,
                                'payment': payment,
                                'status': 'completed',
                            }
                    except Payment.DoesNotExist:
                        logger.error(f"Payment {payment_id} not found for verification")

            return {
                'success': False,
                'error': data.get('message', 'Payment verification failed'),
            }

        except requests.RequestException as e:
            logger.error(f"Paystack verification error: {str(e)}")
            return {
                'success': False,
                'error': 'Payment verification service unavailable.',
            }

    @classmethod
    def handle_paystack_webhook(cls, payload):
        """
        Handle Paystack webhook for payment events.
        """
        try:
            event = payload.get('event')
            data = payload.get('data', {})

            if event == 'charge.success':
                reference = data.get('reference')
                payment_id = data.get('metadata', {}).get('payment_id')

                if payment_id:
                    try:
                        payment = Payment.objects.get(id=payment_id)
                        if payment.status != 'COMPLETED':
                            payment.status = 'COMPLETED'
                            payment.save(update_fields=['status', 'updated_at'])
                            if payment.project:
                                cls._update_project_spent(payment.project)
                            logger.info(f"Payment {payment.id} completed via webhook")
                            return True
                    except Payment.DoesNotExist:
                        logger.error(f"Payment {payment_id} not found for webhook")

            elif event == 'charge.failed':
                logger.warning(f"Paystack charge failed: {data.get('reference')}")

            return True

        except Exception as e:
            logger.error(f"Paystack webhook error: {str(e)}")
            return False

    # =====================================================================
    # STATISTICS
    # =====================================================================

    @classmethod
    def get_stats(cls):
        """Get financial statistics for dashboard."""
        total_payments = Payment.objects.filter(status='COMPLETED').count()
        total_amount = Payment.objects.filter(status='COMPLETED').aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0.00')

        total_expenses = Expense.objects.count()
        total_expense_amount = Expense.objects.aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0.00')

        pending_payments = Payment.objects.filter(status='PENDING').count()

        # Payment method breakdown
        method_breakdown = {}
        for method_code, method_label in Payment.Method.choices:
            count = Payment.objects.filter(method=method_code, status='COMPLETED').count()
            if count > 0:
                amount = Payment.objects.filter(method=method_code, status='COMPLETED').aggregate(
                    total=Sum('amount')
                )['total'] or Decimal('0.00')
                method_breakdown[method_label] = {
                    'count': count,
                    'amount': float(amount),
                }

        # Monthly trend (last 6 months)
        monthly_trend = cls._get_monthly_trend(months=6)

        return {
            'total_payments': total_payments,
            'total_amount': float(total_amount),
            'total_expenses': total_expenses,
            'total_expense_amount': float(total_expense_amount),
            'net_position': float(total_amount - total_expense_amount),
            'pending_payments': pending_payments,
            'method_breakdown': method_breakdown,
            'monthly_trend': monthly_trend,
        }

    @classmethod
    def _get_monthly_trend(cls, months=6):
        """Get monthly payment and expense trend data."""
        trend_data = []
        today = timezone.now().date()

        for i in range(months):
            month_end = today.replace(day=1) - timedelta(days=1)
            month_start = month_end.replace(day=1)

            revenue = Payment.objects.filter(
                status='COMPLETED',
                payment_date__gte=month_start,
                payment_date__lte=month_end
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

            expenses = Expense.objects.filter(
                expense_date__gte=month_start,
                expense_date__lte=month_end
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

            trend_data.append({
                'month': month_start.strftime('%b %Y'),
                'revenue': float(revenue),
                'expenses': float(expenses),
                'profit': float(revenue - expenses),
            })

            today = month_start - timedelta(days=1)

        return list(reversed(trend_data))