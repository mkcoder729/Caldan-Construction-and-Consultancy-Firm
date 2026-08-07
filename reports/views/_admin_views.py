"""
Admin Views - Reports App
Caldan Construction - "Building Kenya's Future, One Project at a Time."
"""

import json
import logging
from datetime import datetime, date
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from accounts.permissions.decorators import admin_required
from projects.models import Project

logger = logging.getLogger('caldan.reports')


# =====================================================================
# Helpers — shared between export / export_download / export_history.
# Keeping the parse helpers in the view layer (rather than the service)
# because they're request-shaped; service stays a pure data transform.
# =====================================================================

def _parse_date(value):
    """Parse a YYYY-MM-DD string from request.GET into a date, or None."""
    if not value:
        return None
    try:
        return datetime.strptime(value, '%Y-%m-%d').date()
    except (TypeError, ValueError):
        return None


def _truthy(value):
    """Return True for ``1``, ``true``, ``yes`` — used by the
    ``include_archived`` flag in the URL query."""
    return str(value or '').lower() in ('1', 'true', 'yes', 'on')


def _export_filters_from_request(request):
    """Read filter kwargs from the request's GET/POST data."""
    src = request.GET if request.method == 'GET' else request.POST
    project_id = src.get('project') or None
    try:
        project_id = int(project_id) if project_id else None
    except (TypeError, ValueError):
        project_id = None
    return {
        'project_id':       project_id,
        'date_from':        _parse_date(src.get('date_from')),
        'date_to':          _parse_date(src.get('date_to')),
        'include_archived': _truthy(src.get('include_archived')),
    }


# =====================================================================
# REPORTS DASHBOARD
# =====================================================================

@login_required
@admin_required
def index(request):
    """
    Reports Dashboard with quick stats and links to all report types.
    Sidebar Page: Reports > Reports Dashboard
    """
    from reports.services.report_service import ReportService

    stats = ReportService.get_dashboard_stats()

    context = {
        'stats': stats,
        'page_title': 'Reports Dashboard',
    }

    return render(request, 'reports/dashboard/admin/reports/index.html', context)


# =====================================================================
# PROJECT REPORT
# =====================================================================

@login_required
@admin_required
def project_report(request, project_id=None):
    """
    Project Report with progress, budget, and milestone details.
    Sidebar Page: Reports > Project Report
    """
    from reports.services.report_service import ReportService

    projects = Project.objects.filter(is_archived=False).order_by('-created_at')

    selected_project = None
    report_data = None
    chart_data = None

    if project_id:
        selected_project = get_object_or_404(Project, id=project_id)
    elif projects.exists():
        selected_project = projects.first()

    if selected_project:
        report_data = ReportService.get_project_report(selected_project.id)

        if report_data and report_data.get('financial'):
            budget_data = report_data['financial']
            chart_data = {
                'labels': ['Budget', 'Spent', 'Remaining'],
                'values': [
                    budget_data['total_budget'],
                    budget_data['total_spent'],
                    budget_data['remaining_budget'],
                ],
                'colors': ['#0B66C3', '#D4AF37', '#27AE60'],
            }

    context = {
        'projects': projects,
        'selected_project': selected_project,
        'report': report_data,
        'chart_data': chart_data,
        'page_title': 'Project Report',
    }

    return render(request, 'reports/dashboard/admin/reports/project.html', context)


# =====================================================================
# INVENTORY REPORT
# =====================================================================

@login_required
@admin_required
def inventory_report(request):
    """
    Inventory Report with material counts, low stock alerts, and category breakdown.
    Sidebar Page: Reports > Inventory Report
    """
    from reports.services.report_service import ReportService

    report_data = ReportService.get_inventory_report()

    chart_data = None
    if report_data.get('category_breakdown'):
        categories = list(report_data['category_breakdown'].keys())
        values = [report_data['category_breakdown'][cat]['count'] for cat in categories]
        chart_data = {
            'labels': categories,
            'values': values,
            'colors': ['#0B66C3', '#123B73', '#D4AF37', '#27AE60', '#B9342B', '#F39C12', '#2980B9', '#8E44AD'],
        }

    context = {
        'report': report_data,
        'chart_data': chart_data,
        'page_title': 'Inventory Report',
    }

    return render(request, 'reports/dashboard/admin/reports/inventory.html', context)


# =====================================================================
# FINANCIAL REPORT
# =====================================================================

@login_required
@admin_required
def financial_report(request):
    """
    Financial Report with payments, expenses, and budget tracking.
    Sidebar Page: Reports > Financial Report
    """
    from reports.services.report_service import ReportService

    report_data = ReportService.get_financial_report()

    trend_data = report_data.get('trend_data', [])
    chart_data = {
        'labels': [item['month'] for item in trend_data],
        'revenue': [item['revenue'] for item in trend_data],
        'expenses': [item['expenses'] for item in trend_data],
    }

    context = {
        'report': report_data,
        'chart_data': chart_data,
        'page_title': 'Financial Report',
    }

    return render(request, 'reports/dashboard/admin/reports/financial.html', context)


# =====================================================================
# EXPORT CENTER
# =====================================================================

@login_required
@admin_required
def export_center(request):
    """
    Export Center for downloading reports in various formats.
    Sidebar Page: Reports > Export Center
    """
    from reports.forms.export_form import ExportForm
    from reports.models import ExportRecord

    form = ExportForm(request.GET or None)

    # Recent exports so the History table on this page shows real rows.
    # We cap at 8 — the dedicated history page lists everything else.
    recent_exports = (
        ExportRecord.objects
        .select_related('created_by', 'project')
        .order_by('-created_at')[:8]
    )

    # Types exposed in the Quick Downloads panel.
    quick_types = ['projects', 'clients', 'orders', 'payments', 'expenses',
                   'inventory', 'team', 'blog', 'notifications', 'audit']

    # Build a list of (value, label, icon, desc) tuples so the template
    # doesn't need to look up REPORT_META — no custom filter required.
    quick_meta = [
        (t, ExportForm.get_label_for(t), ExportForm.REPORT_META[t]['icon'],
         ExportForm.REPORT_META[t]['desc'])
        for t in quick_types
    ]

    context = {
        'form':              form,
        'recent_exports':    recent_exports,
        'quick_types':       quick_types,
        'quick_meta':        quick_meta,
        'report_meta':       ExportForm.REPORT_META,
        # JSON-serialize so JS can read them as arrays.  Without
        # json.dumps, Django renders Python repr (single quotes) which
        # JSON.parse rejects silently.
        'requires_project_js':  json.dumps(sorted(ExportForm.REQUIRES_PROJECT)),
        'supports_archived_js': json.dumps(sorted(ExportForm.SUPPORTS_ARCHIVED)),
        'page_title':        'Export Center',
    }

    return render(request, 'reports/dashboard/admin/reports/export.html', context)


# =====================================================================
# EXPORT DOWNLOAD  (POST shim — validates the form, then redirects to the
# unified GET endpoint so history writes happen in one place.)
# =====================================================================

@login_required
@admin_required
@require_http_methods(['POST'])
def export_download(request):
    """
    Process export request and return the file download.
    """
    from reports.forms.export_form import ExportForm

    form = ExportForm(request.POST)

    if not form.is_valid():
        for field_name, errs in form.errors.items():
            label = field_name if field_name == '__all__' else form.fields[field_name].label
            for err in errs:
                messages.error(request, f"{label}: {err}" if label else err)
        return redirect('reports:export_center')

    cd = form.cleaned_data
    params = {
        'type':   cd['report_type'],
        'format': cd['format'],
    }
    if cd.get('project'):
        params['project'] = cd['project'].id
    if cd.get('date_from'):
        params['date_from'] = cd['date_from'].isoformat()
    if cd.get('date_to'):
        params['date_to'] = cd['date_to'].isoformat()
    if cd.get('include_archived'):
        params['include_archived'] = '1'

    # Round-trip through the GET handler so all history + validation
    # logic lives in one place.  Using urlencode avoids manual & joining.
    return redirect(f"{reverse('reports:export')}?{urlencode(params)}")


# =====================================================================
# EXPORT  (the single source of truth for actually generating a file)
# =====================================================================

@login_required
@admin_required
def export(request):
    """
    GET-friendly export endpoint for direct download links.

    Accepts ``?type=<section>&format=<csv|excel|pdf>`` query params plus
    optional filters: ``project``, ``date_from``, ``date_to``,
    ``include_archived``.

    Every successful download is recorded in ``ExportRecord`` so the
    History panel and ``/reports/export/history/`` page have real data.

    Supported sections:
        projects, project, clients, orders, payments, expenses,
        inventory, team, blog, notifications, all
    """
    from reports.forms.export_form import ExportForm
    from reports.models import ExportRecord
    from reports.services.export_service import ExportService

    section = request.GET.get('type', '').lower().strip()
    if not section and 'export-all' in request.path:
        section = 'all'
    export_format = request.GET.get('format', 'csv').lower().strip()

    filters = _export_filters_from_request(request)

    if not section:
        messages.error(request, 'Missing export type. Use ?type=<section>&format=<format>.')
        return redirect('reports:export_center')

    if export_format not in ('csv', 'excel', 'pdf'):
        messages.error(request, f'Unsupported export format: {export_format}')
        return redirect('reports:export_center')

    # Per-section dispatch.  ``project`` (singular) is the "single project
    # report" choice and requires ``project_id``; everything else is a
    # bulk export.
    section_map = {
        'projects':      ExportService.export_projects,
        'project':       ExportService.export_single_project,
        'clients':       ExportService.export_clients,
        'services':      ExportService.export_services,
        'team':          ExportService.export_team,
        'blog':          ExportService.export_blog,
        'orders':        ExportService.export_orders,
        'payments':      ExportService.export_payments,
        'expenses':      ExportService.export_expenses,
        'inventory':     ExportService.export_inventory_full,
        'materials':     ExportService.export_inventory_full,
        'notifications': ExportService.export_notifications,
        'audit':         ExportService.export_audit_logs,
    }

    # Resolve report_label for the history record
    label = next(
        (lbl for val, lbl in ExportForm.REPORT_TYPES if val == section),
        section.title(),
    )

    def _record(**overrides):
        """Helper: write an ExportRecord with consistent defaults."""
        defaults = dict(
            report_type=section,
            report_label=label,
            format=export_format,
            status=ExportRecord.Status.SUCCESS,
            project_id=filters['project_id'] or None,
            date_from=filters['date_from'],
            date_to=filters['date_to'],
            include_archived=filters['include_archived'],
            created_by=request.user if request.user.is_authenticated else None,
        )
        defaults.update(overrides)
        return ExportRecord.objects.create(**defaults)

    # Special-case "all" — single zip bundle
    if section == 'all':
        try:
            response = ExportService.export_all_data(**filters)
            size = len(response.content) if hasattr(response, 'content') else 0
            _record(format=ExportRecord.Format.ZIP, file_size=size)
            return response
        except Exception as e:
            logger.error(f"Full export bundle failed: {e}")
            _record(format=ExportRecord.Format.ZIP, status=ExportRecord.Status.FAILED, error=str(e))
            messages.error(request, f'Export bundle failed: {e}')
            return redirect('reports:export_center')

    func = section_map.get(section)
    if not func:
        messages.error(request, f'Unsupported export type: {section}')
        return redirect('reports:export_center')

    # Single-project report needs the project_id arg; everything else
    # accepts it via **filters and ignores it.
    call_kwargs = dict(filters)
    if section == 'project':
        if not filters['project_id']:
            messages.error(request, 'Pick a specific project for a Single Project Report.')
            return redirect('reports:export_center')
        call_kwargs = {'project_id': filters['project_id']}

    try:
        response = func(export_format, **call_kwargs)
        if response is None:
            _record(status=ExportRecord.Status.FAILED, error='No data available')
            messages.error(request, f'No data available to export for "{section}".')
            return redirect('reports:export_center')

        size = len(response.content) if hasattr(response, 'content') else 0
        _record(file_size=size)
        return response
    except Exception as e:
        logger.error(f"Export failed for {section} ({export_format}): {e}")
        _record(status=ExportRecord.Status.FAILED, error=str(e))
        messages.error(request, f'Export failed: {e}')
        return redirect('reports:export_center')


# =====================================================================
# EXPORT HISTORY  (full list page with filters + pagination)
# =====================================================================

@login_required
@admin_required
def export_history(request):
    """Full export history with type + date-range filters."""
    from reports.forms.export_form import ExportForm
    from reports.models import ExportRecord

    qs = ExportRecord.objects.select_related('created_by', 'project')

    # Filters (GET params).
    type_filter = request.GET.get('type', '').strip()
    date_from = _parse_date(request.GET.get('date_from'))
    date_to = _parse_date(request.GET.get('date_to'))

    if type_filter:
        qs = qs.filter(report_type=type_filter)
    if date_from:
        qs = qs.filter(created_at__date__gte=date_from)
    if date_to:
        qs = qs.filter(created_at__date__lte=date_to)

    qs = qs.order_by('-created_at')

    # Simple offset pagination (50/page) — keeps URL bookmarks stable.
    try:
        page = max(1, int(request.GET.get('page', '1')))
    except ValueError:
        page = 1
    per_page = 50
    total = qs.count()
    start = (page - 1) * per_page
    end = start + per_page
    records = qs[start:end]

    context = {
        'records':       records,
        'report_types':  ExportForm.REPORT_TYPES,
        'current_type':  type_filter,
        'date_from':     date_from,
        'date_to':       date_to,
        'page':          page,
        'per_page':      per_page,
        'total':         total,
        'has_prev':      page > 1,
        'has_next':      end < total,
        'page_title':    'Export History',
    }

    return render(request, 'reports/dashboard/admin/reports/export_history.html', context)


# =====================================================================
# EXPORT HISTORY DELETE  (soft-remove a record from the history table)
# =====================================================================

@login_required
@admin_required
@require_http_methods(['POST'])
def export_history_delete(request, record_id):
    """Delete an export record.  Hard delete — the row itself is just
    bookkeeping; the actual file content is regenerated on demand."""
    from reports.models import ExportRecord

    record = get_object_or_404(ExportRecord, id=record_id)
    label = str(record)
    record.delete()
    messages.success(request, f'Removed “{label}” from export history.')
    return redirect(request.META.get('HTTP_REFERER') or 'reports:export_history')


# =====================================================================
# BACKUP MANAGER
# =====================================================================

@login_required
@admin_required
def backup_manager(request):
    """
    Backup Manager for creating, restoring, and managing project backups.
    Sidebar Page: Reports > Backup Manager
    """
    from reports.forms.backup_form import BackupForm
    from reports.services.backup_service import BackupService

    form = BackupForm()
    backups = BackupService.list_backups()

    context = {
        'form': form,
        'backups': backups[:20],
        'page_title': 'Backup Manager',
    }

    return render(request, 'reports/dashboard/admin/reports/backup.html', context)


# =====================================================================
# BACKUP HISTORY
# =====================================================================

@login_required
@admin_required
def backup_history(request):
    """
    Full backup history page. Lists every non-deleted backup with
    restore / download actions.
    """
    from reports.services.backup_service import BackupService

    backups = BackupService.list_backups()

    context = {
        'backups': backups,
        'page_title': 'Backup History',
    }

    return render(request, 'reports/dashboard/admin/reports/backup_history.html', context)


# =====================================================================
# BACKUP CREATE
# =====================================================================

@login_required
@admin_required
@require_http_methods(['POST'])
def backup_create(request):
    """
    Create a new backup for a project.
    """
    from reports.forms.backup_form import BackupForm
    from reports.services.backup_service import BackupService

    form = BackupForm(request.POST)

    if not form.is_valid():
        messages.error(request, 'Please correct the errors below.')
        return redirect('reports:backup_manager')

    project = form.cleaned_data['project']
    includes = form.get_includes()
    notes = form.cleaned_data.get('notes', '')

    try:
        backup = BackupService.create_backup(
            project_id=project.id,
            user=request.user,
            includes=includes,
            notes=notes,
        )

        messages.success(
            request,
            f'Backup created successfully for "{project.name}". '
            f'{backup.record_count} records backed up.'
        )

    except Exception as e:
        logger.error(f"Backup creation failed: {str(e)}")
        messages.error(request, f'Backup failed: {str(e)}')

    return redirect('reports:backup_manager')


# =====================================================================
# BACKUP RESTORE
# =====================================================================

@login_required
@admin_required
@require_http_methods(['POST'])
def backup_restore(request, backup_id):
    """
    Restore a project from a backup.
    """
    from reports.services.backup_service import BackupService
    from reports.models.backup_record import BackupRecord

    try:
        backup = get_object_or_404(BackupRecord, id=backup_id)

        if backup.is_deleted:
            messages.error(request, 'Cannot restore a deleted backup.')
            return redirect('reports:backup_manager')

        project = BackupService.restore_backup(backup_id, request.user)

        messages.success(
            request,
            f'Project "{project.name}" restored successfully from backup!'
        )

    except ValueError as e:
        messages.error(request, str(e))
    except Exception as e:
        logger.error(f"Backup restore failed: {str(e)}")
        messages.error(request, f'Restore failed: {str(e)}')

    return redirect('reports:backup_manager')


# =====================================================================
# BACKUP DELETE
# =====================================================================

@login_required
@admin_required
@require_http_methods(['POST'])
def backup_delete(request, backup_id):
    """
    Delete a backup (soft delete).
    """
    from reports.services.backup_service import BackupService

    try:
        BackupService.delete_backup(backup_id, request.user)
        messages.success(request, 'Backup deleted successfully.')

    except Exception as e:
        logger.error(f"Backup deletion failed: {str(e)}")
        messages.error(request, f'Deletion failed: {str(e)}')

    return redirect('reports:backup_manager')