"""
Report Service - Data aggregation for all report types.
Caldan Construction - "Building Kenya's Future, One Project at a Time."
"""

import logging
from datetime import timedelta
from decimal import Decimal

from django.db.models import Count, Sum, Q, Avg
from django.utils import timezone

from projects.models import Project, Milestone
from inventory.models import Material, StockTransaction
from shop.models import Order
from finances.models import Payment, Expense, Budget
from accounts.models.user import User

logger = logging.getLogger('caldan.reports')


class ReportService:
    """
    Centralized service for generating reports from all platform modules.
    All methods are class methods for clean service-oriented architecture.
    """

    @classmethod
    def get_project_report(cls, project_id):
        """
        Generate comprehensive project report.
        Returns dict with project details, milestones, financials, and stats.
        """
        try:
            project = Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            logger.error(f"Project {project_id} not found for report")
            return None

        # Get milestones
        milestones = project.milestones.all().order_by('order', 'target_date')
        total_milestones = milestones.count()
        completed_milestones = milestones.filter(status='COMPLETED').count()
        overdue_milestones = milestones.filter(status='OVERDUE').count()

        completion_rate = round((completed_milestones / total_milestones * 100), 1) if total_milestones > 0 else 0

        # Get financials
        payments = Payment.objects.filter(project=project, status='COMPLETED')
        expenses = Expense.objects.filter(project=project)

        total_payments = payments.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        total_expenses = expenses.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        # Get budgets
        budgets = Budget.objects.filter(project=project)
        total_budget = budgets.aggregate(total=Sum('allocated'))['total'] or Decimal('0.00')
        total_spent = budgets.aggregate(total=Sum('spent'))['total'] or Decimal('0.00')

        # Get materials linked to this project
        materials = Material.objects.filter(project=project) if hasattr(Material, 'project') else []

        return {
            'project': project,
            'milestones': {
                'total': total_milestones,
                'completed': completed_milestones,
                'overdue': overdue_milestones,
                'completion_rate': completion_rate,
                'list': milestones[:10],
            },
            'financial': {
                'total_payments': float(total_payments),
                'total_expenses': float(total_expenses),
                'net_position': float(total_payments - total_expenses),
                'total_budget': float(total_budget),
                'total_spent': float(total_spent),
                'remaining_budget': float(total_budget - total_spent),
                'budget_used_percentage': round((total_spent / total_budget * 100), 1) if total_budget > 0 else 0,
                'recent_payments': payments.order_by('-payment_date')[:5],
                'recent_expenses': expenses.order_by('-expense_date')[:5],
                'budgets': budgets,
            },
            'materials': {
                'total': materials.count() if materials else 0,
                'list': materials[:10] if materials else [],
            },
            'generated_at': timezone.now(),
        }

    @classmethod
    def get_inventory_report(cls):
        """
        Generate comprehensive inventory report.
        Returns dict with material counts, low stock alerts, and category breakdowns.
        """
        materials = Material.objects.filter(is_active=True)

        total_materials = materials.count()
        low_stock_count = materials.filter(is_low_stock=True).count()
        out_of_stock_count = materials.filter(current_quantity=0).count()
        total_value = materials.aggregate(total=Sum('total_cost'))['total'] or Decimal('0.00')

        # Category breakdown
        category_breakdown = {}
        for category_code, category_label in Material.Category.choices:
            cat_materials = materials.filter(category=category_code)
            count = cat_materials.count()
            if count > 0:
                category_breakdown[category_label] = {
                    'count': count,
                    'value': float(cat_materials.aggregate(total=Sum('total_cost'))['total'] or 0),
                    'low_stock': cat_materials.filter(is_low_stock=True).count(),
                }

        # Recent transactions
        recent_transactions = StockTransaction.objects.filter(
            status='CONFIRMED'
        ).order_by('-transaction_date')[:10]

        return {
            'total_materials': total_materials,
            'low_stock_count': low_stock_count,
            'out_of_stock_count': out_of_stock_count,
            'total_value': float(total_value),
            'category_breakdown': category_breakdown,
            'low_stock_materials': materials.filter(is_low_stock=True)[:10],
            'recent_transactions': recent_transactions,
            'generated_at': timezone.now(),
        }

    @classmethod
    def get_financial_report(cls, date_from=None, date_to=None):
        """
        Generate comprehensive financial report.
        Returns dict with payments, expenses, budgets, and summaries.
        """
        if not date_from:
            date_from = timezone.now().date() - timedelta(days=30)

        if not date_to:
            date_to = timezone.now().date()

        # Payments
        payments = Payment.objects.filter(
            status='COMPLETED',
            payment_date__gte=date_from,
            payment_date__lte=date_to
        )
        total_payments = payments.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        # Expenses
        expenses = Expense.objects.filter(
            expense_date__gte=date_from,
            expense_date__lte=date_to
        )
        total_expenses = expenses.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        # Payment method breakdown
        method_breakdown = {}
        for method_code, method_label in Payment.Method.choices:
            method_payments = payments.filter(method=method_code)
            count = method_payments.count()
            if count > 0:
                method_breakdown[method_label] = {
                    'count': count,
                    'amount': float(method_payments.aggregate(total=Sum('amount'))['total'] or 0),
                }

        # Expense category breakdown
        expense_breakdown = {}
        for category_code, category_label in Expense.Category.choices:
            cat_expenses = expenses.filter(category=category_code)
            count = cat_expenses.count()
            if count > 0:
                expense_breakdown[category_label] = {
                    'count': count,
                    'amount': float(cat_expenses.aggregate(total=Sum('amount'))['total'] or 0),
                }

        # Monthly trend data (last 12 months)
        trend_data = cls._get_monthly_trend(months=12)

        # Budget summary
        budgets = Budget.objects.filter(
            project__is_archived=False
        )
        total_budget = budgets.aggregate(total=Sum('allocated'))['total'] or Decimal('0.00')
        total_spent = budgets.aggregate(total=Sum('spent'))['total'] or Decimal('0.00')

        return {
            'total_payments': float(total_payments),
            'total_expenses': float(total_expenses),
            'net_position': float(total_payments - total_expenses),
            'payment_count': payments.count(),
            'expense_count': expenses.count(),
            'method_breakdown': method_breakdown,
            'expense_breakdown': expense_breakdown,
            'trend_data': trend_data,
            'budget_summary': {
                'total_budget': float(total_budget),
                'total_spent': float(total_spent),
                'remaining': float(total_budget - total_spent),
                'used_percentage': round((total_spent / total_budget * 100), 1) if total_budget > 0 else 0,
            },
            'recent_payments': payments.order_by('-payment_date')[:10],
            'recent_expenses': expenses.order_by('-expense_date')[:10],
            'date_from': date_from,
            'date_to': date_to,
            'generated_at': timezone.now(),
        }

    @classmethod
    def _get_monthly_trend(cls, months=12):
        """Get monthly revenue and expense trend data for charts."""
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

        # Reverse to show chronological order (oldest to newest)
        return list(reversed(trend_data))

    @classmethod
    def get_dashboard_stats(cls):
        """
        Get quick stats for the reports dashboard.
        """
        # Project stats
        total_projects = Project.objects.filter(is_archived=False).count()
        active_projects = Project.objects.filter(status='ACTIVE', is_archived=False).count()
        completed_projects = Project.objects.filter(status='COMPLETED', is_archived=False).count()

        # Inventory stats
        materials = Material.objects.filter(is_active=True)
        total_materials = materials.count()
        low_stock = materials.filter(is_low_stock=True).count()

        # Order stats
        total_orders = Order.objects.count()
        pending_orders = Order.objects.filter(status='PENDING').count()

        # Financial stats
        total_revenue = Payment.objects.filter(status='COMPLETED').aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0.00')

        total_expenses = Expense.objects.aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0.00')

        # User stats
        total_admins = User.objects.filter(is_staff=True, is_active=True).count()

        return {
            'total_projects': total_projects,
            'active_projects': active_projects,
            'completed_projects': completed_projects,
            'total_materials': total_materials,
            'low_stock': low_stock,
            'total_orders': total_orders,
            'pending_orders': pending_orders,
            'total_revenue': float(total_revenue),
            'total_expenses': float(total_expenses),
            'net_position': float(total_revenue - total_expenses),
            'total_admins': total_admins,
            'generated_at': timezone.now(),
        }

    @classmethod
    def get_order_report(cls, date_from=None, date_to=None):
        """
        Generate order report for the shop.
        """
        if not date_from:
            date_from = timezone.now().date() - timedelta(days=30)

        if not date_to:
            date_to = timezone.now().date()

        orders = Order.objects.filter(
            created_at__date__gte=date_from,
            created_at__date__lte=date_to
        )

        total_orders = orders.count()
        pending = orders.filter(status='PENDING').count()
        processing = orders.filter(status='PROCESSING').count()
        shipped = orders.filter(status='SHIPPED').count()
        delivered = orders.filter(status='DELIVERED').count()
        completed = orders.filter(status='COMPLETED').count()
        cancelled = orders.filter(status='CANCELLED').count()

        total_revenue = orders.filter(
            status__in=['PAID', 'PROCESSING', 'SHIPPED', 'DELIVERED', 'COMPLETED']
        ).aggregate(total=Sum('total'))['total'] or Decimal('0.00')

        # Status distribution
        status_distribution = {
            'Pending': pending,
            'Processing': processing,
            'Shipped': shipped,
            'Delivered': delivered,
            'Completed': completed,
            'Cancelled': cancelled,
        }

        return {
            'total_orders': total_orders,
            'pending': pending,
            'processing': processing,
            'shipped': shipped,
            'delivered': delivered,
            'completed': completed,
            'cancelled': cancelled,
            'total_revenue': float(total_revenue),
            'status_distribution': status_distribution,
            'recent_orders': orders.order_by('-created_at')[:10],
            'date_from': date_from,
            'date_to': date_to,
            'generated_at': timezone.now(),
        }