"""
Dashboard Overview Views
The main dashboard landing page with stats, charts, and activity feed.
"""

import json

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils import timezone

from dashboard.services.stats_service import StatsService
from dashboard.services.activity_service import ActivityService


@login_required
def dashboard_home(request):
    """
    Main dashboard overview page.
    Displays stats cards, charts, quick actions, and activity feed.
    """
    # ---- Core stats -----------------------------------------------------
    stats = StatsService.get_overview_stats(request.user)

    # ---- Time-series chart (revenue / orders / projects per month) ------
    chart_data = StatsService.get_chart_data(months=12)
    revenue_months = [item['month'] for item in chart_data]
    revenue_data = [item['revenue'] for item in chart_data]
    chart_orders = [item['orders'] for item in chart_data]
    chart_projects = [item['projects'] for item in chart_data]

    # ---- Growth chart (clients + team per month) -----------------------
    growth = StatsService.get_growth_data(months=12)

    # ---- Pie / doughnut charts -----------------------------------------
    order_chart = StatsService.get_order_status_chart()
    project_chart = StatsService.get_project_status_chart()
    inventory_chart = StatsService.get_inventory_by_category()
    revenue_breakdown = StatsService.get_revenue_breakdown()

    # ---- Recent activity + recent payments -----------------------------
    activity = ActivityService.get_recent_activity(limit=10, user=request.user)
    recent_payments = StatsService.get_recent_payments(limit=5)
    milestone_overview = StatsService.get_milestone_overview(limit=5)

    context = {
        'page_title': 'Dashboard Overview',
        'page_icon': 'fa-tachometer-alt',
        'stats': stats,

        # Revenue / growth line + bar
        'revenue_months': json.dumps(revenue_months),
        'revenue_data':   json.dumps(revenue_data),
        'chart_orders':   json.dumps(chart_orders),
        'chart_projects': json.dumps(chart_projects),
        'growth_months':  json.dumps(growth['months']),
        'growth_clients': json.dumps(growth['clients']),
        'growth_team':    json.dumps(growth['team']),

        # Order status pie
        'order_status_labels': json.dumps(order_chart['labels']),
        'order_status_data':   json.dumps(order_chart['counts']),
        'order_status_colors': json.dumps(order_chart['colors']),

        # Project status pie
        'project_status_labels': json.dumps(project_chart['labels']),
        'project_status_data':   json.dumps(project_chart['counts']),
        'project_status_colors': json.dumps(project_chart['colors']),

        # Inventory bar
        'inventory_category_labels': json.dumps(inventory_chart['labels']),
        'inventory_category_data':   json.dumps(inventory_chart['data']),

        # Revenue breakdown doughnut
        'revenue_breakdown_labels': json.dumps(revenue_breakdown['labels']),
        'revenue_breakdown_data':   json.dumps(revenue_breakdown['data']),
        'revenue_breakdown_colors': json.dumps(revenue_breakdown['colors']),

        # Recent activity + recent payments
        'activities': activity['items'],
        'recent_payments': recent_payments,
        'milestone_overview': milestone_overview,

        # Misc
        'current_date': timezone.now(),
        'user_name': request.user.full_name or request.user.email,
    }

    return render(request, 'dashboard/dashboard/admin/overview/index.html', context)