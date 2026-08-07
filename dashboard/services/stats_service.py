"""
Statistics service for dashboard overview.
Provides dynamic stats from all apps using service classes.
"""

from decimal import Decimal
from django.db.models import Sum, Count, Q, Value, DecimalField, IntegerField
from django.db.models.functions import Coalesce, TruncMonth
from django.utils import timezone
from datetime import timedelta

from accounts.models import User
from projects.models import Project
from projects.models.milestone import Milestone
from inventory.models import Material, StockTransaction
from shop.models import Order
from finances.models import Payment, Expense
from clients.models import Client
from team.models.team_member import TeamMember


# Brand-cohesive palette for chart slices/lines (matches dashboard CSS vars)
CHART_PALETTE = [
    '#0B66C3',  # brand-blue
    '#D4AF37',  # brand-gold
    '#27AE60',  # sem-success
    '#F39C12',  # sem-warning
    '#B9342B',  # sem-danger
    '#7C3AED',  # purple
    '#0891B2',  # teal
    '#8B5CF6',  # violet
    '#EC4899',  # pink
    '#64748B',  # slate
]


class StatsService:
    """
    Service for fetching dashboard statistics.
    All data is queried dynamically - no hardcoding.
    """

    @classmethod
    def get_overview_stats(cls, user=None):
        """
        Get all overview statistics for dashboard.
        """
        today = timezone.now().date()
        month_start = today.replace(day=1)
        week_start = today - timedelta(days=today.weekday())
        year_start = today.replace(month=1, day=1)

        # ------------------------------------------------------------------
        # Project stats
        # ------------------------------------------------------------------
        projects = Project.objects.filter(is_archived=False)
        project_stats = {
            'total': projects.count(),
            'active': projects.filter(status=Project.Status.ACTIVE).count(),
            'planning': projects.filter(status=Project.Status.PLANNING).count(),
            'completed': projects.filter(status=Project.Status.COMPLETED).count(),
            'on_hold': projects.filter(status=Project.Status.ON_HOLD).count(),
            'archived': Project.objects.filter(is_archived=True).count(),
        }

        # This month's projects
        project_stats['this_month'] = Project.objects.filter(
            created_at__date__gte=month_start
        ).count()

        # Avg progress (denormalised field on Project — always present)
        avg_progress = projects.aggregate(
            avg=Coalesce(Sum('progress'), Value(0), output_field=DecimalField())
        )['avg'] or 0
        total_projects = project_stats['total'] or 1
        project_stats['avg_progress'] = round(
            float(Decimal(str(avg_progress)) / Decimal(total_projects)), 2
        )

        # ------------------------------------------------------------------
        # Inventory stats
        # ------------------------------------------------------------------
        materials = Material.objects.filter(is_active=True)
        inventory_stats = {
            'total_materials': materials.count(),
            'low_stock': materials.filter(is_low_stock=True).count(),
            'out_of_stock': materials.filter(current_quantity__lte=0).count(),
            'total_value': float(
                materials.aggregate(
                    total=Coalesce(Sum('total_cost'), Value(0), output_field=DecimalField())
                )['total']
            ),
        }

        # Categories = distinct categories actually used by materials
        inventory_stats['categories'] = (
            materials.exclude(category__isnull=True)
            .exclude(category='')
            .values('category').distinct().count()
        )

        # Recent stock transactions
        inventory_stats['recent_transactions'] = StockTransaction.objects.filter(
            status='CONFIRMED'
        ).order_by('-transaction_date')[:5]

        # ------------------------------------------------------------------
        # Order stats
        # ------------------------------------------------------------------
        orders = Order.objects.all()
        order_stats = {
            'total': orders.count(),
            'pending': orders.filter(status=Order.Status.PENDING).count(),
            'paid': orders.filter(status=Order.Status.PAID).count(),
            'processing': orders.filter(status=Order.Status.PROCESSING).count(),
            'shipped': orders.filter(status=Order.Status.SHIPPED).count(),
            'delivered': orders.filter(status=Order.Status.DELIVERED).count(),
            'completed': orders.filter(status=Order.Status.COMPLETED).count(),
            'cancelled': orders.filter(status=Order.Status.CANCELLED).count(),
        }

        # ------------------------------------------------------------------
        # Revenue / payments
        # ------------------------------------------------------------------
        completed_payments = Payment.objects.filter(status=Payment.Status.COMPLETED)
        approved_payments = Payment.objects.filter(status=Payment.Status.APPROVED)
        all_payments = Payment.objects.all()

        revenue_stats = {
            'total_revenue': float(
                completed_payments.aggregate(
                    t=Coalesce(Sum('amount'), Value(0), output_field=DecimalField())
                )['t']
            ),
            'this_month': float(
                completed_payments.filter(payment_date__gte=month_start)
                .aggregate(t=Coalesce(Sum('amount'), Value(0), output_field=DecimalField()))['t']
            ),
            'this_week': float(
                completed_payments.filter(payment_date__gte=week_start)
                .aggregate(t=Coalesce(Sum('amount'), Value(0), output_field=DecimalField()))['t']
            ),
            'today': float(
                completed_payments.filter(payment_date=today)
                .aggregate(t=Coalesce(Sum('amount'), Value(0), output_field=DecimalField()))['t']
            ),
            'annual_revenue': float(
                completed_payments.filter(payment_date__gte=year_start)
                .aggregate(t=Coalesce(Sum('amount'), Value(0), output_field=DecimalField()))['t']
            ),
        }

        total_count = all_payments.count()
        completed_count = completed_payments.count() + approved_payments.count()
        success_rate = (
            round((completed_count / total_count) * 100, 1) if total_count else 0
        )

        payment_stats = {
            'count': total_count,
            'this_month': revenue_stats['this_month'],
            'completed': completed_payments.count(),
            'pending': all_payments.filter(status=Payment.Status.PENDING).count(),
            'cancelled': all_payments.filter(status=Payment.Status.CANCELLED).count(),
            'success_rate': success_rate,
        }

        # ------------------------------------------------------------------
        # Expenses
        # ------------------------------------------------------------------
        expense_stats = {
            'total': float(
                Expense.objects.aggregate(
                    t=Coalesce(Sum('amount'), Value(0), output_field=DecimalField())
                )['t']
            ),
            'this_month': float(
                Expense.objects.filter(expense_date__gte=month_start)
                .aggregate(t=Coalesce(Sum('amount'), Value(0), output_field=DecimalField()))['t']
            ),
        }

        # ------------------------------------------------------------------
        # Client stats
        # ------------------------------------------------------------------
        client_stats = {
            'total': Client.objects.count(),
            'active': Client.objects.filter(status=Client.Status.ACTIVE).count(),
            'leads': Client.objects.filter(status=Client.Status.LEAD).count(),
            'inactive': Client.objects.filter(status=Client.Status.INACTIVE).count(),
            'converted': Client.objects.filter(status=Client.Status.CONVERTED).count(),
            'this_month': Client.objects.filter(
                created_at__date__gte=month_start
            ).count(),
        }

        # ------------------------------------------------------------------
        # Team stats
        # ------------------------------------------------------------------
        team_qs = TeamMember.objects.all()
        team_stats = {
            'total': team_qs.count(),
            'active': team_qs.filter(is_active=True).count(),
            'inactive': team_qs.filter(is_active=False).count(),
            'featured': team_qs.filter(is_featured=True).count(),
            'new_this_month': team_qs.filter(
                created_at__date__gte=month_start
            ).count(),
        }

        # ------------------------------------------------------------------
        # User stats (admin accounts)
        # ------------------------------------------------------------------
        user_stats = {
            'total_admins': User.objects.filter(is_staff=True).count(),
            'active_users': User.objects.filter(is_active=True).count(),
            'total_users': User.objects.count(),
            'chief_admins': User.objects.filter(is_chief=True).count(),
        }

        return {
            'projects': project_stats,
            'inventory': inventory_stats,
            'orders': order_stats,
            'revenue': revenue_stats,
            'payments': payment_stats,
            'expenses': expense_stats,
            'clients': client_stats,
            'team': team_stats,
            'users': user_stats,
            'total_users': user_stats['total_users'],
            'pending_approvals': (
                payment_stats['pending']
                + order_stats['pending']
            ),
            'kyc_pending': Client.objects.filter(status=Client.Status.LEAD).count(),
            'generated_at': timezone.now(),
        }

    # =====================================================================
    # REVENUE & ORDERS TIME-SERIES (line + bar)
    # =====================================================================
    @classmethod
    def get_chart_data(cls, months=12):
        """
        Get month-by-month revenue, orders, and projects for charts.
        """
        today = timezone.now().date()
        chart_data = []

        # Build a list of (start, end, label) for the last N months
        cursor = today.replace(day=1)
        for _ in range(months):
            chart_data.append({
                'month_start': cursor,
                'month_end': cls._month_end(cursor),
                'label': cursor.strftime('%b %Y'),
            })
            # move to previous month
            prev_end = cursor - timedelta(days=1)
            cursor = prev_end.replace(day=1)

        # Reverse so oldest is first (chronological)
        chart_data.reverse()

        for entry in chart_data:
            revenue = Payment.objects.filter(
                status=Payment.Status.COMPLETED,
                payment_date__gte=entry['month_start'],
                payment_date__lte=entry['month_end'],
            ).aggregate(
                t=Coalesce(Sum('amount'), Value(0), output_field=DecimalField())
            )['t']

            order_count = Order.objects.filter(
                created_at__date__gte=entry['month_start'],
                created_at__date__lte=entry['month_end'],
            ).count()

            project_count = Project.objects.filter(
                created_at__date__gte=entry['month_start'],
                created_at__date__lte=entry['month_end'],
            ).count()

            entry['revenue'] = float(revenue)
            entry['orders'] = order_count
            entry['projects'] = project_count
            entry['month'] = entry['label']
            del entry['month_start']
            del entry['month_end']

        return chart_data

    # =====================================================================
    # GROWTH (clients + team members per month)
    # =====================================================================
    @classmethod
    def get_growth_data(cls, months=12):
        """
        Return per-month new-client and new-team-member counts for the
        User Growth bar chart.
        """
        today = timezone.now().date()
        labels, clients, team = [], [], []

        cursor = today.replace(day=1)
        for _ in range(months):
            end = cls._month_end(cursor)
            labels.append(cursor.strftime('%b %Y'))
            clients.append(
                Client.objects.filter(
                    created_at__date__gte=cursor,
                    created_at__date__lte=end,
                ).count()
            )
            team.append(
                TeamMember.objects.filter(
                    created_at__date__gte=cursor,
                    created_at__date__lte=end,
                ).count()
            )
            prev_end = cursor - timedelta(days=1)
            cursor = prev_end.replace(day=1)

        # Reverse so oldest is first
        return {
            'months': labels[::-1],
            'clients': clients[::-1],
            'team': team[::-1],
        }

    # =====================================================================
    # ORDER STATUS (pie / doughnut)
    # =====================================================================
    @classmethod
    def get_order_status_chart(cls):
        """
        Get order status distribution for the pie chart. Returns
        labels, counts, and colors in matching order.
        """
        # Define a preferred order for the slices
        status_order = [
            (Order.Status.PENDING,    'Pending',    '#F39C12'),
            (Order.Status.PAID,        'Paid',       '#0EA5E9'),
            (Order.Status.PROCESSING,  'Processing', '#2980B9'),
            (Order.Status.SHIPPED,     'Shipped',    '#3498DB'),
            (Order.Status.DELIVERED,   'Delivered',  '#27AE60'),
            (Order.Status.COMPLETED,   'Completed',  '#2ECC71'),
            (Order.Status.CANCELLED,   'Cancelled',  '#B9342B'),
        ]

        labels, counts, colors = [], [], []
        for value, label, color in status_order:
            count = Order.objects.filter(status=value).count()
            if count > 0:
                labels.append(label)
                counts.append(count)
                colors.append(color)

        return {
            'labels': labels,
            'counts': counts,
            'colors': colors,
        }

    # =====================================================================
    # PROJECT STATUS (pie / doughnut)
    # =====================================================================
    @classmethod
    def get_project_status_chart(cls):
        """
        Get project status distribution for the pie chart.
        """
        status_order = [
            (Project.Status.PLANNING,  'Planning',  '#F39C12'),
            (Project.Status.ACTIVE,    'Active',    '#27AE60'),
            (Project.Status.ON_HOLD,   'On Hold',   '#2980B9'),
            (Project.Status.COMPLETED, 'Completed', '#0B66C3'),
            (Project.Status.ARCHIVED,  'Archived',  '#64748B'),
        ]

        labels, counts, colors = [], [], []
        for value, label, color in status_order:
            count = Project.objects.filter(status=value).count()
            if count > 0:
                labels.append(label)
                counts.append(count)
                colors.append(color)

        return {
            'labels': labels,
            'counts': counts,
            'colors': colors,
        }

    # =====================================================================
    # INVENTORY BY CATEGORY (bar)
    # =====================================================================
    @classmethod
    def get_inventory_by_category(cls):
        """
        Return label/value pairs for the inventory-by-category bar chart.
        Sums current_quantity per material category so the chart reflects
        real stock counts (not material line count).
        """
        rows = (
            Material.objects.filter(is_active=True)
            .values('category')
            .annotate(total=Coalesce(Sum('current_quantity'), Value(0), output_field=DecimalField()))
            .order_by('-total')
        )

        labels, data = [], []
        for row in rows:
            cat = row['category']
            if not cat:
                continue
            labels.append(Material.Category(cat).label if cat in Material.Category.values else cat)
            data.append(float(row['total'] or 0))

        return {'labels': labels, 'data': data}

    # =====================================================================
    # REVENUE BREAKDOWN (doughnut) — by Payment.type
    # =====================================================================
    @classmethod
    def get_revenue_breakdown(cls):
        """
        Return revenue broken down by payment type for the doughnut chart.
        Only completed payments are summed.
        """
        rows = (
            Payment.objects.filter(status=Payment.Status.COMPLETED)
            .values('type')
            .annotate(total=Coalesce(Sum('amount'), Value(0), output_field=DecimalField()))
            .order_by('-total')
        )

        labels, data, colors = [], [], []
        for i, row in enumerate(rows):
            t = row['type']
            total = float(row['total'] or 0)
            if total <= 0:
                continue
            label = Payment.Type(t).label if t in Payment.Type.values else t
            labels.append(label)
            data.append(total)
            colors.append(CHART_PALETTE[i % len(CHART_PALETTE)])

        return {
            'labels': labels,
            'data': data,
            'colors': colors,
        }

    # =====================================================================
    # RECENT PAYMENTS (table on overview)
    # =====================================================================
    @classmethod
    def get_recent_payments(cls, limit=5):
        """
        Return the most recent payments, with derived client_name /
        project_name / status_display so the template can render without
        hardcoded fields.
        """
        payments = list(
            Payment.objects
            .select_related('project')
            .order_by('-payment_date', '-created_at')[:limit]
        )

        # Build a {project_id: first_client_name} map.
        # Client.projects is the M2M (defined on Client), so we query
        # through the Client side via the ClientProjectLink reverse.
        project_ids = [p.project_id for p in payments if p.project_id]
        client_by_project = {}
        if project_ids:
            # Each Client row back from the through-table gives us one
            # (project_id, client_name) pair. We keep the lowest-id client
            # per project for stable display.
            for row in (
                Client.objects
                .filter(projects__id__in=project_ids)
                .values('projects__id', 'name')
                .order_by('projects__id', 'id')
            ):
                pid = row['projects__id']
                if pid not in client_by_project:
                    client_by_project[pid] = row['name']

        results = []
        for p in payments:
            project_name = ''
            client_name = ''
            if p.project_id:
                project_name = p.project.name
                client_name = client_by_project.get(p.project_id, '')
            results.append({
                'id': p.id,
                'created_at': p.created_at,
                'payment_date': p.payment_date,
                'amount': float(p.amount),
                'method': p.get_method_display() if hasattr(p, 'get_method_display') else p.method,
                'status': p.status.lower(),
                'status_display': p.get_status_display() if hasattr(p, 'get_status_display') else p.status.title(),
                'project_name': project_name,
                'client_name': client_name,
                'paid_to': p.paid_to,
            })
        return results

    # =====================================================================
    # MILESTONE PROGRESS (active projects + their milestone state)
    # =====================================================================
    @classmethod
    def get_milestone_overview(cls, limit=5):
        """
        Return per-project milestone progress for the most recently
        updated ACTIVE projects. Each entry drives a progress bar in the
        overview's "Milestones" widget.

        Returns:
            [{
                'project_id': int,
                'project_name': str,
                'project_code': str,
                'progress': float (0-100),
                'milestones_total': int,
                'milestones_completed': int,
                'milestones_in_progress': int,
                'milestones_overdue': int,
                'milestones_pending': int,
            }]
        """
        active_projects = (
            Project.objects
            .filter(is_archived=False, status=Project.Status.ACTIVE)
            .order_by('-updated_at')[:limit]
        )

        results = []
        for project in active_projects:
            milestones = project.milestones.all()
            total = milestones.count()
            completed = milestones.filter(status=Milestone.Status.COMPLETED).count()
            in_progress = milestones.filter(status=Milestone.Status.IN_PROGRESS).count()
            overdue = milestones.filter(status=Milestone.Status.OVERDUE).count()
            pending = milestones.filter(status=Milestone.Status.PENDING).count()

            # Progress: prefer stored field, fall back to computed
            progress = float(project.progress or 0)
            if total > 0:
                avg = sum(float(m.completion_percentage or 0) for m in milestones) / total
                # If stored value is 0 but milestones exist, use computed
                if progress == 0 and avg > 0:
                    progress = round(avg, 2)

            results.append({
                'project_id': project.id,
                'project_name': project.name,
                'project_code': project.project_code,
                'progress': round(progress, 2),
                'milestones_total': total,
                'milestones_completed': completed,
                'milestones_in_progress': in_progress,
                'milestones_overdue': overdue,
                'milestones_pending': pending,
            })

        return results

    # =====================================================================
    # HELPERS
    # =====================================================================
    @staticmethod
    def _month_end(start_date):
        """Return the last day of the month containing start_date."""
        if start_date.month == 12:
            return start_date.replace(day=31)
        next_month = start_date.replace(month=start_date.month + 1, day=1)
        return next_month - timedelta(days=1)