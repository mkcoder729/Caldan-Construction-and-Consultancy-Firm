"""
Analytics Dashboard Views
Detailed analytics with charts, reports, and data insights.
"""

import json

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils import timezone

from dashboard.services.stats_service import StatsService
from dashboard.services.activity_service import ActivityService


@login_required
def analytics_dashboard(request):
    """
    Analytics dashboard with detailed charts and insights.
    """
    # Get extended stats
    stats = StatsService.get_overview_stats(request.user)

    # Get 12-month chart data
    chart_data = StatsService.get_chart_data(months=12)

    # Prepare chart data
    months = [item['month'] for item in chart_data]
    revenue = [item['revenue'] for item in chart_data]
    orders = [item['orders'] for item in chart_data]
    projects = [item['projects'] for item in chart_data]

    # Order status distribution
    order_chart = StatsService.get_order_status_chart()

    # Activity summary
    activity_summary = ActivityService.get_activity_summary()

    context = {
        'page_title': 'Analytics',
        'page_icon': 'fa-chart-line',
        'stats': stats,

        # JSON-encoded so the template can drop them straight into
        # data-* attributes and Chart.js can JSON.parse them safely.
        # Without json.dumps, Django renders Python list repr (e.g.
        # ['Jan', 'Feb']) which happens to look like JSON today but
        # breaks the moment a value is True/False/None.
        'months':        json.dumps(months),
        'revenue_data':  json.dumps(revenue),
        'orders_data':   json.dumps(orders),
        'projects_data': json.dumps(projects),

        'order_chart': order_chart,
        'activity_summary': activity_summary,
        'current_date': timezone.now(),
    }

    return render(request, 'dashboard/dashboard/admin/analytics/index.html', context)