"""
Report Views for Dashboard
Generate and export reports for all modules.
"""

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from django.utils import timezone

from reports.services.report_service import ReportService
from reports.services.export_service import ExportService
from reports.services.pdf_service import PDFService
from accounts.services.audit_service import AuditService
from projects.models import Project


@login_required
def report_index(request):
    """
    Reports dashboard landing page.
    """
    # Get quick stats for all report types
    inventory_report = ReportService.get_inventory_report()
    order_report = ReportService.get_order_report()

    context = {
        'page_title': 'Reports Dashboard',
        'page_icon': 'fa-chart-bar',
        'inventory_report': inventory_report,
        'order_report': order_report,
        'report_types': [
            {'name': 'Project Summary', 'icon': 'fa-building', 'url': 'dashboard:report_project'},
            {'name': 'Inventory Report', 'icon': 'fa-boxes', 'url': 'dashboard:report_inventory'},
            {'name': 'Order Report', 'icon': 'fa-shopping-bag', 'url': 'dashboard:report_orders'},
            {'name': 'Financial Report', 'icon': 'fa-money-bill-wave', 'url': 'dashboard:report_financial'},
            {'name': 'Client Report', 'icon': 'fa-users', 'url': 'dashboard:report_clients'},
            {'name': 'Audit Report', 'icon': 'fa-history', 'url': 'dashboard:report_audit'},
        ],
        'generated_at': timezone.now(),
    }
    return render(request, 'reports/dashboard/admin/reports/index.html', context)


@login_required
def report_project(request):
    """
    Generate project report.
    """
    project_id = request.GET.get('project')
    projects = Project.objects.filter(is_archived=False)

    if project_id:
        project = Project.objects.get(id=project_id)
        report_data = ReportService.get_project_summary(project_id)

        # Export options
        if request.GET.get('export') == 'pdf':
            pdf_path = PDFService.generate_project_report_pdf(report_data)
            AuditService.log_action(
                user=request.user,
                action='REPORT_EXPORTED',
                details={'type': 'project_pdf', 'project': project.name}
            )
            return redirect(f'/media/{pdf_path}')

        if request.GET.get('export') == 'csv':
            # Generate CSV
            data = report_data.get('milestones', [])
            fields = ['title', 'status', 'target_date', 'completion_percentage']
            response = ExportService.export_to_csv(
                data=data,
                fields=fields,
                filename=f'project_report_{project.project_code}.csv'
            )
            AuditService.log_action(
                user=request.user,
                action='REPORT_EXPORTED',
                details={'type': 'project_csv', 'project': project.name}
            )
            return response

        context = {
            'page_title': 'Project Report',
            'page_icon': 'fa-file-alt',
            'project': project,
            'report': report_data,
            'projects': projects,
            'selected_project': project_id,
        }
        return render(request, 'reports/dashboard/admin/reports/project.html', context)

    context = {
        'page_title': 'Project Report',
        'page_icon': 'fa-file-alt',
        'projects': projects,
        'selected_project': None,
    }
    return render(request, 'reports/dashboard/admin/reports/project.html', context)


@login_required
def report_inventory(request):
    """
    Generate inventory report.
    """
    report_data = ReportService.get_inventory_report()

    # Export options
    if request.GET.get('export') == 'pdf':
        pdf_path = PDFService.generate_inventory_report_pdf(report_data)
        AuditService.log_action(
            user=request.user,
            action='REPORT_EXPORTED',
            details={'type': 'inventory_pdf'}
        )
        return redirect(f'/media/{pdf_path}')

    if request.GET.get('export') == 'csv':
        data = report_data.get('category_breakdown', [])
        fields = ['category', 'count', 'value', 'low_stock']
        response = ExportService.export_to_csv(
            data=data,
            fields=fields,
            filename='inventory_report.csv'
        )
        AuditService.log_action(
            user=request.user,
            action='REPORT_EXPORTED',
            details={'type': 'inventory_csv'}
        )
        return response

    context = {
        'page_title': 'Inventory Report',
        'page_icon': 'fa-boxes',
        'report': report_data,
        'generated_at': timezone.now(),
    }
    return render(request, 'reports/dashboard/admin/reports/inventory.html', context)


@login_required
def report_orders(request):
    """
    Generate order report.
    """
    report_data = ReportService.get_order_report()

    if request.GET.get('export') == 'pdf':
        pdf_path = PDFService.generate_order_report_pdf(report_data)
        AuditService.log_action(
            user=request.user,
            action='REPORT_EXPORTED',
            details={'type': 'order_pdf'}
        )
        return redirect(f'/media/{pdf_path}')

    if request.GET.get('export') == 'csv':
        orders = Order.objects.all()
        data = [{
            'order_number': o.order_number,
            'client_name': o.client_name,
            'total': o.total,
            'status': o.status,
            'created_at': o.created_at.date(),
        } for o in orders]
        fields = ['order_number', 'client_name', 'total', 'status', 'created_at']
        response = ExportService.export_to_csv(
            data=data,
            fields=fields,
            filename='order_report.csv'
        )
        AuditService.log_action(
            user=request.user,
            action='REPORT_EXPORTED',
            details={'type': 'order_csv'}
        )
        return response

    context = {
        'page_title': 'Order Report',
        'page_icon': 'fa-shopping-bag',
        'report': report_data,
        'generated_at': timezone.now(),
    }
    return render(request, 'reports/dashboard/admin/reports/orders.html', context)


@login_required
def report_financial(request):
    """
    Generate financial report.
    """
    from finances.services.financial_service import FinancialService
    financial_summary = FinancialService.get_overall_financial_summary()

    if request.GET.get('export') == 'pdf':
        pdf_path = PDFService.generate_financial_report_pdf(financial_summary)
        AuditService.log_action(
            user=request.user,
            action='REPORT_EXPORTED',
            details={'type': 'financial_pdf'}
        )
        return redirect(f'/media/{pdf_path}')

    context = {
        'page_title': 'Financial Report',
        'page_icon': 'fa-file-invoice',
        'report': financial_summary,
        'generated_at': timezone.now(),
    }
    return render(request, 'reports/dashboard/admin/reports/financial.html', context)


@login_required
def report_clients(request):
    """
    Generate client report.
    """
    from clients.models import Client
    from django.db.models import Count, Sum

    clients = Client.objects.all()
    total = clients.count()
    active = clients.filter(status='ACTIVE').count()
    leads = clients.filter(status='LEAD').count()

    # Get client with most orders/projects
    top_clients = clients.annotate(
        project_count=Count('projects'),
        order_count=Count('orders')
    ).order_by('-project_count')[:10]

    context = {
        'page_title': 'Client Report',
        'page_icon': 'fa-users',
        'total': total,
        'active': active,
        'leads': leads,
        'top_clients': top_clients,
        'generated_at': timezone.now(),
    }
    return render(request, 'reports/dashboard/admin/reports/clients.html', context)


@login_required
def report_audit(request):
    """
    Generate audit report.
    """
    from accounts.models import AuditLog
    from django.db.models import Count

    # Get audit summary
    total_actions = AuditLog.objects.count()
    today_actions = AuditLog.objects.filter(created_at__date=timezone.now().date()).count()

    # Most common actions
    common_actions = AuditLog.objects.values('action').annotate(
        count=Count('id')
    ).order_by('-count')[:10]

    # User activity
    user_activity = AuditLog.objects.values('user__email').annotate(
        count=Count('id')
    ).order_by('-count')[:10]

    context = {
        'page_title': 'Audit Report',
        'page_icon': 'fa-history',
        'total_actions': total_actions,
        'today_actions': today_actions,
        'common_actions': common_actions,
        'user_activity': user_activity,
        'generated_at': timezone.now(),
    }
    return render(request, 'reports/dashboard/admin/reports/audit.html', context)