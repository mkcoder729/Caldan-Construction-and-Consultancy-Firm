"""
Export Service - CSV, Excel, and PDF generation.
Caldan Construction - "Building Kenya's Future, One Project at a Time."
"""

import csv
import io
import logging
import os
import zipfile
from datetime import datetime
from decimal import Decimal

from django.conf import settings
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils import timezone

from reports.services.report_service import ReportService

logger = logging.getLogger('caldan.reports')


class ExportService:
    """
    Service for exporting data in various formats.
    Supports CSV, Excel (via openpyxl), and PDF (via Playwright).
    """

    @classmethod
    def export_to_csv(cls, data, fields, filename):
        """
        Export data to CSV format using Python's csv module.
        """
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{filename}.csv"'

        writer = csv.writer(response)

        # Write header
        headers = [field.replace('_', ' ').title() for field in fields]
        writer.writerow(headers)

        # Write data
        for item in data:
            row = []
            for field in fields:
                value = item.get(field, '')
                if isinstance(value, (int, float, Decimal)):
                    row.append(str(value))
                elif isinstance(value, datetime):
                    row.append(value.strftime('%Y-%m-%d %H:%M'))
                elif value is None:
                    row.append('')
                else:
                    row.append(str(value))
            writer.writerow(row)

        return response

    @classmethod
    def export_to_excel(cls, data, fields, filename):
        """
        Export data to Excel format using openpyxl.
        """
        try:
            import openpyxl
            from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        except ImportError:
            logger.error("openpyxl not installed. Cannot export to Excel.")
            raise ImportError("openpyxl is required for Excel export. Run: pip install openpyxl")

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Export"

        # Header style
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="0B66C3", end_color="0B66C3", fill_type="solid")
        header_alignment = Alignment(horizontal="center", vertical="center")

        # Write header
        headers = [field.replace('_', ' ').title() for field in fields]
        for col_idx, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col_idx, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_alignment

        # Write data
        for row_idx, item in enumerate(data, 2):
            for col_idx, field in enumerate(fields, 1):
                value = item.get(field, '')
                if isinstance(value, (int, float, Decimal)):
                    value = float(value)
                elif isinstance(value, datetime):
                    value = value.strftime('%Y-%m-%d %H:%M')
                elif value is None:
                    value = ''
                ws.cell(row=row_idx, column=col_idx, value=value)

        # Auto-column width
        for column in ws.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if cell.value and len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except Exception:
                    pass
            adjusted_width = min(max_length + 2, 50)
            ws.column_dimensions[column_letter].width = adjusted_width

        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}.xlsx"'
        wb.save(response)
        return response

    @classmethod
    def export_to_pdf(cls, template_name, context, filename):
        """
        Export data to PDF using Playwright with headless Chromium.
        """
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            logger.error("playwright not installed. Cannot export to PDF.")
            raise ImportError("playwright is required for PDF export. Run: pip install playwright && playwright install")

        # Render HTML. PDF templates may use `|intcomma` for thousands
        # separators — load `humanize` so that filter is available.
        from django.template.loader import render_to_string as _rts
        from django.template.loader import get_template
        template = get_template(template_name)
        html_string = template.render(context)

        # Generate PDF
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_content(html_string, wait_until="networkidle")

            pdf_bytes = page.pdf(
                format="A4",
                print_background=True,
                margin={
                    'top': '1.5cm',
                    'bottom': '1.5cm',
                    'left': '1.5cm',
                    'right': '1.5cm',
                }
            )
            browser.close()

        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}.pdf"'
        return response

    @classmethod
    def export_project_report(cls, project_id, format='pdf'):
        """
        Export a comprehensive project report in the specified format.
        """
        report_data = ReportService.get_project_report(project_id)
        if not report_data:
            return None

        project = report_data['project']
        filename = f"project_report_{project.project_code}_{timezone.now().strftime('%Y%m%d')}"

        fields = [
            'name', 'project_code', 'status', 'county', 'town',
            'start_date', 'estimated_completion', 'progress',
            'budget', 'spent', 'remaining'
        ]

        # Prepare data for export
        export_data = [{
            'name': project.name,
            'project_code': project.project_code,
            'status': project.get_status_display(),
            'county': project.county,
            'town': project.town,
            'start_date': project.start_date,
            'estimated_completion': project.estimated_completion,
            'progress': f"{project.progress}%",
            'budget': float(project.budget),
            'spent': float(project.spent),
            'remaining': float(project.budget - project.spent),
        }]

        if format == 'csv':
            return cls.export_to_csv(export_data, fields, filename)
        elif format == 'excel':
            return cls.export_to_excel(export_data, fields, filename)
        else:
            # PDF - use template
            context = {
                'project': project,
                'report_data': report_data,
                'brand_name': 'Caldan Construction',
                'tagline': 'Building Kenya\'s Future, One Project at a Time.',
                'generated_at': timezone.now(),
            }
            return cls.export_to_pdf('pdf/project_report.html', context, filename)

    @classmethod
    def export_single_project(cls, export_format='pdf', project_id=None, **kwargs):
        """Wrapper for ``export_project_report`` so the new form choice
        ``type=project`` can dispatch through the same code path as the
        per-section exports.

        Signature: ``func(export_format, **filters)`` — matches the
        other per-section exports.  ``project_id`` comes through as a
        keyword so we don't swap positional order with format.
        """
        if not project_id:
            raise ValueError("export_single_project requires a project_id")
        return cls.export_project_report(project_id, format=export_format)

    @classmethod
    def export_inventory_report(cls, format='pdf'):
        """
        Export inventory report in the specified format.
        """
        report_data = ReportService.get_inventory_report()
        filename = f"inventory_report_{timezone.now().strftime('%Y%m%d')}"

        if format == 'csv':
            fields = ['name', 'category', 'unit', 'current_quantity', 'minimum_threshold', 'unit_cost', 'total_cost']
            materials = report_data.get('low_stock_materials', [])
            export_data = []
            for material in materials:
                export_data.append({
                    'name': material.name,
                    'category': material.get_category_display(),
                    'unit': material.get_unit_display(),
                    'current_quantity': float(material.current_quantity),
                    'minimum_threshold': float(material.minimum_threshold),
                    'unit_cost': float(material.unit_cost),
                    'total_cost': float(material.total_cost),
                })
            return cls.export_to_csv(export_data, fields, filename)

        elif format == 'excel':
            fields = ['name', 'category', 'unit', 'current_quantity', 'minimum_threshold', 'unit_cost', 'total_cost']
            materials = report_data.get('low_stock_materials', [])
            export_data = []
            for material in materials:
                export_data.append({
                    'name': material.name,
                    'category': material.get_category_display(),
                    'unit': material.get_unit_display(),
                    'current_quantity': float(material.current_quantity),
                    'minimum_threshold': float(material.minimum_threshold),
                    'unit_cost': float(material.unit_cost),
                    'total_cost': float(material.total_cost),
                })
            return cls.export_to_excel(export_data, fields, filename)

        else:
            # PDF
            context = {
                'report': report_data,
                'brand_name': 'Caldan Construction',
                'tagline': 'Building Kenya\'s Future, One Project at a Time.',
                'generated_at': timezone.now(),
            }
            return cls.export_to_pdf('pdf/inventory_report.html', context, filename)

    @classmethod
    def export_financial_report(cls, format='pdf', date_from=None, date_to=None):
        """
        Export financial report in the specified format.
        """
        report_data = ReportService.get_financial_report(date_from, date_to)
        filename = f"financial_report_{timezone.now().strftime('%Y%m%d')}"

        if format == 'csv':
            fields = ['description', 'amount', 'type', 'method', 'payment_date', 'status']
            payments = report_data.get('recent_payments', [])
            export_data = []
            for payment in payments:
                export_data.append({
                    'description': payment.description[:50],
                    'amount': float(payment.amount),
                    'type': payment.get_type_display(),
                    'method': payment.get_method_display(),
                    'payment_date': payment.payment_date,
                    'status': payment.get_status_display(),
                })
            return cls.export_to_csv(export_data, fields, filename)

        elif format == 'excel':
            fields = ['description', 'amount', 'type', 'method', 'payment_date', 'status']
            payments = report_data.get('recent_payments', [])
            export_data = []
            for payment in payments:
                export_data.append({
                    'description': payment.description[:50],
                    'amount': float(payment.amount),
                    'type': payment.get_type_display(),
                    'method': payment.get_method_display(),
                    'payment_date': payment.payment_date,
                    'status': payment.get_status_display(),
                })
            return cls.export_to_excel(export_data, fields, filename)

        else:
            # PDF
            context = {
                'report': report_data,
                'brand_name': 'Caldan Construction',
                'tagline': 'Building Kenya\'s Future, One Project at a Time.',
                'generated_at': timezone.now(),
            }
            return cls.export_to_pdf('pdf/financial_report.html', context, filename)

    # =================================================================
    # PER-SECTION EXPORTS — CSV / Excel / PDF
    # Each section pulls ALL records (not paginated, not filtered)
    # so the export is a complete backup of that slice.
    # =================================================================

    @classmethod
    def export_projects(cls, export_format='csv', date_from=None, date_to=None,
                        include_archived=False, **kwargs):
        """Export projects.  Honors date range + include_archived."""
        from projects.models import Project
        filename = f"projects_{timezone.now().strftime('%Y%m%d_%H%M%S')}"
        fields = [
            'project_code', 'name', 'status', 'county', 'town',
            'start_date', 'estimated_completion',
            'budget', 'spent', 'progress', 'is_archived', 'created_at',
        ]
        qs = Project.objects.all()
        if not include_archived:
            qs = qs.filter(is_archived=False)
        if date_from:
            qs = qs.filter(created_at__date__gte=date_from)
        if date_to:
            qs = qs.filter(created_at__date__lte=date_to)
        qs = qs.order_by('-created_at')
        rows = [{
            'project_code': p.project_code,
            'name': p.name,
            'status': p.get_status_display(),
            'county': p.county or '',
            'town': p.town or '',
            'start_date': p.start_date or '',
            'estimated_completion': p.estimated_completion or '',
            'budget': float(p.budget),
            'spent': float(p.spent),
            'progress': f"{p.progress}%",
            'is_archived': 'Yes' if p.is_archived else 'No',
            'created_at': p.created_at,
        } for p in qs]

        if export_format == 'csv':
            return cls.export_to_csv(rows, fields, filename)
        if export_format == 'excel':
            return cls.export_to_excel(rows, fields, filename)
        # PDF
        return cls.export_to_pdf('pdf/projects_full_report.html', {
            'report_title': 'Projects Report',
            'report_subtitle': 'Complete list of all projects',
            'projects': qs,
            'total_records': qs.count(),
            'generated_at': timezone.now(),
        }, filename)

    @classmethod
    def export_clients(cls, export_format='csv', date_from=None, date_to=None, **kwargs):
        """Export clients.  Honors date range."""
        from clients.models import Client
        filename = f"clients_{timezone.now().strftime('%Y%m%d_%H%M%S')}"
        fields = ['name', 'company_name', 'email', 'phone', 'type', 'status', 'county', 'town', 'created_at']
        qs = Client.objects.all()
        if date_from:
            qs = qs.filter(created_at__date__gte=date_from)
        if date_to:
            qs = qs.filter(created_at__date__lte=date_to)
        qs = qs.order_by('-created_at')
        rows = [{
            'name': c.name,
            'company_name': c.company_name or '',
            'email': c.email or '',
            'phone': c.phone or '',
            'type': c.get_type_display() if hasattr(c, 'get_type_display') else (c.type or ''),
            'status': c.get_status_display() if hasattr(c, 'get_status_display') else (c.status or ''),
            'county': c.county or '',
            'town': c.town or '',
            'created_at': c.created_at,
        } for c in qs]

        if export_format == 'csv':
            return cls.export_to_csv(rows, fields, filename)
        if export_format == 'excel':
            return cls.export_to_excel(rows, fields, filename)
        return cls.export_to_pdf('pdf/clients_report.html', {
            'report_title': 'Clients Report',
            'report_subtitle': 'Complete client directory',
            'clients': qs,
            'total_records': qs.count(),
            'generated_at': timezone.now(),
        }, filename)

    @classmethod
    def export_services(cls, export_format='csv', date_from=None, date_to=None, **kwargs):
        """Export services.  Honors date range."""
        from services.models import Service
        filename = f"services_{timezone.now().strftime('%Y%m%d_%H%M%S')}"
        fields = ['name', 'category', 'description', 'is_active', 'display_order', 'created_at']
        qs = Service.objects.all()
        if date_from:
            qs = qs.filter(created_at__date__gte=date_from)
        if date_to:
            qs = qs.filter(created_at__date__lte=date_to)
        qs = qs.order_by('display_order', 'name')
        rows = [{
            'name': s.name,
            'category': s.get_category_display() if hasattr(s, 'get_category_display') else (s.category or ''),
            'description': (s.description or '')[:120],
            'is_active': 'Yes' if s.is_active else 'No',
            'display_order': s.display_order,
            'created_at': s.created_at,
        } for s in qs]

        if export_format == 'csv':
            return cls.export_to_csv(rows, fields, filename)
        if export_format == 'excel':
            return cls.export_to_excel(rows, fields, filename)
        return cls.export_to_pdf('pdf/services_report.html', {
            'report_title': 'Services Report',
            'report_subtitle': 'Complete services catalog',
            'services': qs,
            'total_records': qs.count(),
            'generated_at': timezone.now(),
        }, filename)

    @classmethod
    def export_team(cls, export_format='csv', date_from=None, date_to=None, **kwargs):
        """Export team members.  No standard date column; kwargs accepted for parity."""
        from team.models import TeamMember
        filename = f"team_{timezone.now().strftime('%Y%m%d_%H%M%S')}"
        fields = ['name', 'role', 'title', 'email', 'phone', 'is_active', 'is_featured', 'display_order']
        qs = TeamMember.objects.all().order_by('display_order', 'name')
        rows = [{
            'name': t.name,
            'role': t.get_role_display() if hasattr(t, 'get_role_display') else (t.role or ''),
            'title': t.title or '',
            'email': t.email or '',
            'phone': t.phone or '',
            'is_active': 'Yes' if t.is_active else 'No',
            'is_featured': 'Yes' if t.is_featured else 'No',
            'display_order': t.display_order,
        } for t in qs]

        if export_format == 'csv':
            return cls.export_to_csv(rows, fields, filename)
        if export_format == 'excel':
            return cls.export_to_excel(rows, fields, filename)
        return cls.export_to_pdf('pdf/team_report.html', {
            'report_title': 'Team Report',
            'report_subtitle': 'Complete team directory',
            'team': qs,
            'total_records': qs.count(),
            'generated_at': timezone.now(),
        }, filename)

    @classmethod
    def export_blog(cls, export_format='csv', date_from=None, date_to=None, **kwargs):
        """Export blog posts.  Honors date range."""
        from blog.models import BlogPost
        filename = f"blog_{timezone.now().strftime('%Y%m%d_%H%M%S')}"
        fields = ['title', 'slug', 'is_published', 'published_at', 'created_at']
        qs = BlogPost.objects.all()
        if date_from:
            qs = qs.filter(created_at__date__gte=date_from)
        if date_to:
            qs = qs.filter(created_at__date__lte=date_to)
        qs = qs.order_by('-created_at')
        rows = [{
            'title': p.title,
            'slug': p.slug,
            'is_published': 'Published' if p.is_published else 'Draft',
            'published_at': p.published_at or '',
            'created_at': p.created_at,
        } for p in qs]

        if export_format == 'csv':
            return cls.export_to_csv(rows, fields, filename)
        if export_format == 'excel':
            return cls.export_to_excel(rows, fields, filename)
        return cls.export_to_pdf('pdf/blog_report.html', {
            'report_title': 'Blog Posts Report',
            'report_subtitle': 'All articles, published and drafts',
            'posts': qs,
            'total_records': qs.count(),
            'generated_at': timezone.now(),
        }, filename)

    @classmethod
    def export_orders(cls, export_format='csv', date_from=None, date_to=None, **kwargs):
        """Export shop orders.  Honors date range."""
        from shop.models import Order
        filename = f"orders_{timezone.now().strftime('%Y%m%d_%H%M%S')}"
        fields = [
            'order_number', 'client_name', 'client_email', 'client_phone',
            'subtotal', 'delivery_fee', 'total', 'status',
            'paid_at', 'created_at',
        ]
        qs = Order.objects.all()
        if date_from:
            qs = qs.filter(created_at__date__gte=date_from)
        if date_to:
            qs = qs.filter(created_at__date__lte=date_to)
        qs = qs.order_by('-created_at')
        rows = [{
            'order_number': o.order_number,
            'client_name': o.client_name,
            'client_email': o.client_email or '',
            'client_phone': o.client_phone or '',
            'subtotal': float(o.subtotal),
            'delivery_fee': float(o.delivery_fee),
            'total': float(o.total),
            'status': o.get_status_display() if hasattr(o, 'get_status_display') else (o.status or ''),
            'paid_at': o.paid_at or '',
            'created_at': o.created_at,
        } for o in qs]

        if export_format == 'csv':
            return cls.export_to_csv(rows, fields, filename)
        if export_format == 'excel':
            return cls.export_to_excel(rows, fields, filename)
        return cls.export_to_pdf('pdf/orders_report.html', {
            'report_title': 'Orders Report',
            'report_subtitle': 'Complete order history',
            'orders': qs,
            'total_records': qs.count(),
            'generated_at': timezone.now(),
        }, filename)

    @classmethod
    def export_payments(cls, export_format='csv', date_from=None, date_to=None, **kwargs):
        """Export payments.  Honors date range."""
        from finances.models import Payment
        filename = f"payments_{timezone.now().strftime('%Y%m%d_%H%M%S')}"
        fields = [
            'reference', 'description', 'project_name', 'amount',
            'type', 'method', 'paid_to', 'status', 'payment_date', 'created_at',
        ]
        qs = Payment.objects.all().select_related('project')
        if date_from:
            qs = qs.filter(payment_date__gte=date_from)
        if date_to:
            qs = qs.filter(payment_date__lte=date_to)
        qs = qs.order_by('-created_at')
        rows = [{
            'reference': p.reference,
            'description': (p.description or '')[:80],
            'project_name': p.project.name if p.project else '',
            'amount': float(p.amount),
            'type': p.get_type_display() if hasattr(p, 'get_type_display') else (p.type or ''),
            'method': p.get_method_display() if hasattr(p, 'get_method_display') else (p.method or ''),
            'paid_to': p.paid_to or '',
            'status': p.get_status_display() if hasattr(p, 'get_status_display') else (p.status or ''),
            'payment_date': p.payment_date or '',
            'created_at': p.created_at,
        } for p in qs]

        if export_format == 'csv':
            return cls.export_to_csv(rows, fields, filename)
        if export_format == 'excel':
            return cls.export_to_excel(rows, fields, filename)
        return cls.export_to_pdf('pdf/payments_report.html', {
            'report_title': 'Payments Report',
            'report_subtitle': 'All recorded payments',
            'payments': qs,
            'total_records': qs.count(),
            'generated_at': timezone.now(),
        }, filename)

    @classmethod
    def export_expenses(cls, export_format='csv', date_from=None, date_to=None, **kwargs):
        """Export expenses.  Honors date range."""
        from finances.models import Expense
        filename = f"expenses_{timezone.now().strftime('%Y%m%d_%H%M%S')}"
        fields = [
            'description', 'category', 'project_name', 'amount',
            'vendor_name', 'expense_date', 'created_at',
        ]
        qs = Expense.objects.all().select_related('project')
        if date_from:
            qs = qs.filter(expense_date__gte=date_from)
        if date_to:
            qs = qs.filter(expense_date__lte=date_to)
        qs = qs.order_by('-expense_date')
        rows = [{
            'description': (e.description or '')[:80],
            'category': e.get_category_display() if hasattr(e, 'get_category_display') else (e.category or ''),
            'project_name': e.project.name if e.project else '',
            'amount': float(e.amount),
            'vendor_name': e.vendor_name or '',
            'expense_date': e.expense_date or '',
            'created_at': e.created_at,
        } for e in qs]

        if export_format == 'csv':
            return cls.export_to_csv(rows, fields, filename)
        if export_format == 'excel':
            return cls.export_to_excel(rows, fields, filename)
        return cls.export_to_pdf('pdf/expenses_report.html', {
            'report_title': 'Expenses Report',
            'report_subtitle': 'All recorded expenses',
            'expenses': qs,
            'total_records': qs.count(),
            'generated_at': timezone.now(),
        }, filename)

    @classmethod
    def export_inventory_full(cls, export_format='csv', date_from=None, date_to=None, **kwargs):
        """Export inventory.  No date column on materials/suppliers; kwargs accepted for parity."""
        from inventory.models import Material, Supplier, StockTransaction
        filename = f"inventory_full_{timezone.now().strftime('%Y%m%d_%H%M%S')}"

        materials = Material.objects.all().select_related('supplier').order_by('name')
        suppliers = Supplier.objects.all().order_by('name')
        transactions = StockTransaction.objects.all().select_related('material').order_by('-created_at')[:500]

        if export_format == 'csv':
            # Materials CSV
            mat_fields = ['name', 'sku', 'category', 'unit', 'current_quantity',
                          'minimum_threshold', 'unit_cost', 'total_cost', 'supplier']
            mat_rows = [{
                'name': m.name,
                'sku': m.sku or '',
                'category': m.get_category_display(),
                'unit': m.get_unit_display(),
                'current_quantity': float(m.current_quantity),
                'minimum_threshold': float(m.minimum_threshold),
                'unit_cost': float(m.unit_cost),
                'total_cost': float(m.total_cost) if hasattr(m, 'total_cost') else 0,
                'supplier': m.supplier.name if m.supplier else '',
            } for m in materials]
            return cls.export_to_csv(mat_rows, mat_fields, filename + '_materials')

        if export_format == 'excel':
            mat_fields = ['name', 'sku', 'category', 'unit', 'current_quantity',
                          'minimum_threshold', 'unit_cost', 'total_cost', 'supplier']
            mat_rows = [{
                'name': m.name,
                'sku': m.sku or '',
                'category': m.get_category_display(),
                'unit': m.get_unit_display(),
                'current_quantity': float(m.current_quantity),
                'minimum_threshold': float(m.minimum_threshold),
                'unit_cost': float(m.unit_cost),
                'total_cost': float(m.total_cost) if hasattr(m, 'total_cost') else 0,
                'supplier': m.supplier.name if m.supplier else '',
            } for m in materials]
            return cls.export_to_excel(mat_rows, mat_fields, filename + '_materials')

        # PDF — single PDF covering materials + suppliers + recent transactions
        return cls.export_to_pdf('pdf/inventory_full_report.html', {
            'report_title': 'Inventory Report',
            'report_subtitle': 'Materials, suppliers and recent stock movements',
            'materials': materials,
            'suppliers': suppliers,
            'transactions': transactions,
            'total_records': materials.count() + suppliers.count() + transactions.count(),
            'generated_at': timezone.now(),
        }, filename)

    @classmethod
    def export_notifications(cls, export_format='csv', date_from=None, date_to=None, **kwargs):
        """Export notifications + audit log.  Honors date range."""
        from notifications.models import Notification
        from accounts.models import AuditLog
        filename = f"notifications_{timezone.now().strftime('%Y%m%d_%H%M%S')}"

        notifications = Notification.objects.all().select_related('user').order_by('-created_at')[:1000]
        audit_logs = AuditLog.objects.all().select_related('user').order_by('-created_at')[:500]

        if export_format == 'csv':
            fields = ['title', 'message', 'type', 'priority', 'user', 'is_read', 'created_at']
            rows = [{
                'title': n.title,
                'message': (n.message or '')[:120],
                'type': n.type or '',
                'priority': n.priority or '',
                'user': n.user.get_full_name() if n.user and n.user.get_full_name() else (n.user.email if n.user else ''),
                'is_read': 'Yes' if n.is_read else 'No',
                'created_at': n.created_at,
            } for n in notifications]
            return cls.export_to_csv(rows, fields, filename)

        if export_format == 'excel':
            fields = ['title', 'message', 'type', 'priority', 'user', 'is_read', 'created_at']
            rows = [{
                'title': n.title,
                'message': (n.message or '')[:120],
                'type': n.type or '',
                'priority': n.priority or '',
                'user': n.user.get_full_name() if n.user and n.user.get_full_name() else (n.user.email if n.user else ''),
                'is_read': 'Yes' if n.is_read else 'No',
                'created_at': n.created_at,
            } for n in notifications]
            return cls.export_to_excel(rows, fields, filename)

        return cls.export_to_pdf('pdf/notifications_report.html', {
            'report_title': 'Notifications & Audit Log',
            'report_subtitle': 'In-app notifications and recent administrative actions',
            'notifications': notifications,
            'audit_logs': audit_logs,
            'total_records': notifications.count() + audit_logs.count(),
            'generated_at': timezone.now(),
        }, filename)

    @classmethod
    def export_audit_logs(cls, export_format='csv', date_from=None, date_to=None, **kwargs):
        """Export audit log as CSV, Excel, or PDF. Honors date range."""
        from accounts.models import AuditLog

        qs = AuditLog.objects.select_related('user').order_by('-created_at')
        if date_from:
            qs = qs.filter(created_at__date__gte=date_from)
        if date_to:
            qs = qs.filter(created_at__date__lte=date_to)
        logs = list(qs[:5000])  # cap

        filename = f"audit_log_{timezone.now().strftime('%Y%m%d_%H%M%S')}"

        if export_format == 'csv':
            fields = ['timestamp', 'user', 'role', 'action', 'entity', 'ip_address', 'user_agent', 'hash']
            rows = [{
                'timestamp': log.created_at.isoformat() if log.created_at else '',
                'user': log.user.email if log.user_id else 'System',
                'role': log.user_role or '',
                'action': log.get_action_display() if hasattr(log, 'get_action_display') else log.action,
                'entity': f"{log.entity_type}{f'#{log.entity_id}' if log.entity_id else ''}",
                'ip_address': log.ip_address or '',
                'user_agent': (log.user_agent or '')[:200],
                'hash': log.hash_current or '',
            } for log in logs]
            return cls.export_to_csv(rows, fields, filename)

        if export_format == 'excel':
            fields = ['timestamp', 'user', 'role', 'action', 'entity', 'ip_address', 'user_agent', 'hash']
            rows = [{
                'timestamp': log.created_at.isoformat() if log.created_at else '',
                'user': log.user.email if log.user_id else 'System',
                'role': log.user_role or '',
                'action': log.get_action_display() if hasattr(log, 'get_action_display') else log.action,
                'entity': f"{log.entity_type}{f'#{log.entity_id}' if log.entity_id else ''}",
                'ip_address': log.ip_address or '',
                'user_agent': (log.user_agent or '')[:200],
                'hash': log.hash_current or '',
            } for log in logs]
            return cls.export_to_excel(rows, fields, filename)

        # PDF
        from collections import Counter
        action_counts = Counter(log.action for log in logs)
        user_ids = {log.user_id for log in logs if log.user_id}
        users_by_id = {u.id: u for u in __import__('accounts.models.user', fromlist=['User']).User.objects.filter(id__in=list(user_ids))}
        security_actions = {
            'LOGIN_SUCCESS', 'LOGIN_FAILED', 'LOGOUT', 'PASSWORD_CHANGED',
            'PASSWORD_RESET_REQUESTED', 'ACCOUNT_LOCKED', 'OTP_FAILED',
            'PERMISSION_CHANGED', 'CHIEF_ADMIN_CREATED',
        }
        security_events_list = [log for log in logs if log.action in security_actions]
        user_counts = Counter(log.user_id for log in logs if log.user_id)
        user_activity = [
            {
                'user_full_name': users_by_id.get(uid).full_name if users_by_id.get(uid) else None,
                'user_email': users_by_id.get(uid).email if users_by_id.get(uid) else 'System',
                'count': count,
            }
            for uid, count in user_counts.most_common(10)
        ]
        latest = logs[0] if logs else None
        context = {
            'total_actions': len(logs),
            'unique_users': len(user_ids),
            'security_events': len(security_events_list),
            'security_events_list': security_events_list,
            'action_breakdown': [{'action': a, 'count': c} for a, c in action_counts.most_common(20)],
            'user_activity': user_activity,
            'logs': logs,
            'previous_hash': latest.hash_previous if latest else '',
            'current_hash': latest.hash_current if latest else '',
            'period_start': logs[-1].created_at if logs else None,
            'period_end': logs[0].created_at if logs else None,
            'generated_at': timezone.now(),
            'brand_name': 'Caldan Construction',
            'tagline': "Building Kenya's Future, One Project at a Time.",
        }
        return cls.export_to_pdf('pdf/audit_report.html', context, filename)

    # =================================================================
    # ALL-IN-ONE BUNDLE — every section as its own CSV in a single zip
    # =================================================================

    @classmethod
    def export_all_data(cls, date_from=None, date_to=None, include_archived=False, **kwargs):
        """
        Bundle every section as its own CSV inside a single zip.
        Returns a HttpResponse with attachment Content-Disposition.
        """
        timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
        zip_filename = f"caldan_full_export_{timestamp}.zip"

        # Pull every section's rows
        sections = []

        try:
            sections.append(('projects', cls.export_projects))
            sections.append(('clients', cls.export_clients))
            sections.append(('services', cls.export_services))
            sections.append(('team', cls.export_team))
            sections.append(('blog', cls.export_blog))
            sections.append(('orders', cls.export_orders))
            sections.append(('payments', cls.export_payments))
            sections.append(('expenses', cls.export_expenses))
            # Inventory has its own multi-table CSV path
            sections.append(('inventory', cls.export_inventory_full))
            sections.append(('notifications', cls.export_notifications))
        except Exception as e:
            logger.error(f"Failed to assemble sections: {e}")
            raise

        # Filters passed to every per-section export so the bundle
        # respects the date range + archive toggle from the form.
        filters = {
            'date_from':        date_from,
            'date_to':          date_to,
            'include_archived': include_archived,
        }

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
            # README first so it shows at the top of the zip
            readme = (
                "Caldan Construction — Full Data Export\n"
                f"Generated: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"Timezone: {settings.TIME_ZONE}\n"
                "\n"
                "Contents:\n"
            )
            section_counts = {}
            for name, _func in sections:
                readme += f"  - {name}.csv\n"
            readme += "\nNote: This bundle contains CSV exports only.\n"
            zf.writestr('README.txt', readme)

            for name, func in sections:
                try:
                    # Render each section as CSV and capture bytes.
                    # ``**filters`` lets date/archived ranges flow into every
                    # per-section export so the bundle respects the same
                    # filters as the form.
                    response = func('csv', **filters)
                    content = b''.join(response.streaming_content) if response.streaming else response.content
                    zf.writestr(f"{name}.csv", content)
                    section_counts[name] = content.count(b'\n') - 1  # rough row count
                except Exception as e:
                    logger.error(f"Section {name} failed: {e}")
                    zf.writestr(f"{name}.ERROR.txt", f"Failed to export: {e}")

            # Final summary
            summary = "Export summary (row counts):\n"
            for name, count in section_counts.items():
                summary += f"  {name:15s} {count} rows\n"
            zf.writestr('summary.txt', summary)

        buf.seek(0)
        response = HttpResponse(buf.getvalue(), content_type='application/zip')
        response['Content-Disposition'] = f'attachment; filename="{zip_filename}"'
        return response