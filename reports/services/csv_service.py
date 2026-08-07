"""
CSV Service - Export data to CSV format.
Caldan Construction - "Building Kenya's Future, One Project at a Time."
"""

import csv
import logging
from datetime import datetime
from decimal import Decimal
from io import StringIO

from django.http import HttpResponse

logger = logging.getLogger('caldan.reports')


class CSVService:
    """
    Service for exporting data to CSV format.
    Uses Python's built-in csv module for reliable, fast CSV generation.
    """

    @classmethod
    def export(cls, data, fields, filename, field_headers=None):
        """
        Export data to CSV format.

        Args:
            data: List of dictionaries or objects to export
            fields: List of field names to include
            filename: Output filename (without extension)
            field_headers: Optional custom headers (defaults to field names)

        Returns:
            HttpResponse with CSV content
        """
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{filename}.csv"'

        writer = csv.writer(response)

        # Write header
        if field_headers:
            headers = field_headers
        else:
            headers = [field.replace('_', ' ').title() for field in fields]
        writer.writerow(headers)

        # Write data
        for item in data:
            row = cls._extract_row(item, fields)
            writer.writerow(row)

        logger.info(f"CSV export generated: {filename}.csv with {len(data)} rows")
        return response

    @classmethod
    def export_as_string(cls, data, fields, field_headers=None):
        """
        Export data to CSV as a string (for file storage or email).

        Args:
            data: List of dictionaries or objects to export
            fields: List of field names to include
            field_headers: Optional custom headers

        Returns:
            String containing CSV content
        """
        output = StringIO()
        writer = csv.writer(output)

        # Write header
        if field_headers:
            headers = field_headers
        else:
            headers = [field.replace('_', ' ').title() for field in fields]
        writer.writerow(headers)

        # Write data
        for item in data:
            row = cls._extract_row(item, fields)
            writer.writerow(row)

        return output.getvalue()

    @classmethod
    def _extract_row(cls, item, fields):
        """
        Extract values from a data item for a CSV row.
        Handles dictionaries, objects, and various value types.
        """
        row = []
        for field in fields:
            value = cls._get_value(item, field)
            row.append(cls._format_value(value))
        return row

    @classmethod
    def _get_value(cls, item, field):
        """
        Get a value from a data item.
        Supports dictionaries and objects with attributes.
        """
        if isinstance(item, dict):
            return item.get(field, '')
        elif hasattr(item, field):
            return getattr(item, field, '')
        else:
            return ''

    @classmethod
    def _format_value(cls, value):
        """
        Format a value for CSV output.
        Handles various types including dates, decimals, and None.
        """
        if value is None:
            return ''
        elif isinstance(value, datetime):
            return value.strftime('%Y-%m-%d %H:%M:%S')
        elif isinstance(value, (int, float, Decimal)):
            return str(value)
        elif isinstance(value, bool):
            return 'Yes' if value else 'No'
        elif isinstance(value, (list, dict)):
            # Convert complex types to JSON string
            import json
            return json.dumps(value)
        else:
            return str(value)

    @classmethod
    def export_project_report(cls, project_data, filename=None):
        """
        Export project report data to CSV.
        """
        if not filename:
            filename = f"project_report_{datetime.now().strftime('%Y%m%d')}"

        fields = [
            'name', 'project_code', 'status', 'county', 'town',
            'start_date', 'estimated_completion', 'progress',
            'budget', 'spent', 'remaining'
        ]

        headers = [
            'Project Name', 'Project Code', 'Status', 'County', 'Town',
            'Start Date', 'Estimated Completion', 'Progress (%)',
            'Budget (KES)', 'Spent (KES)', 'Remaining (KES)'
        ]

        # Prepare data
        data = []
        for project in project_data:
            data.append({
                'name': project.name,
                'project_code': project.project_code,
                'status': project.get_status_display(),
                'county': project.county,
                'town': project.town,
                'start_date': project.start_date,
                'estimated_completion': project.estimated_completion,
                'progress': float(project.progress),
                'budget': float(project.budget),
                'spent': float(project.spent),
                'remaining': float(project.budget - project.spent),
            })

        return cls.export(data, fields, filename, headers)

    @classmethod
    def export_inventory_report(cls, materials, filename=None):
        """
        Export inventory report data to CSV.
        """
        if not filename:
            filename = f"inventory_report_{datetime.now().strftime('%Y%m%d')}"

        fields = [
            'name', 'category', 'unit', 'current_quantity',
            'minimum_threshold', 'unit_cost', 'total_cost', 'status'
        ]

        headers = [
            'Material Name', 'Category', 'Unit', 'Current Quantity',
            'Minimum Threshold', 'Unit Cost (KES)', 'Total Cost (KES)', 'Status'
        ]

        data = []
        for material in materials:
            data.append({
                'name': material.name,
                'category': material.get_category_display(),
                'unit': material.get_unit_display(),
                'current_quantity': float(material.current_quantity),
                'minimum_threshold': float(material.minimum_threshold),
                'unit_cost': float(material.unit_cost),
                'total_cost': float(material.total_cost),
                'status': 'Low Stock' if material.is_low_stock else 'OK',
            })

        return cls.export(data, fields, filename, headers)

    @classmethod
    def export_financial_report(cls, payments, expenses, filename=None):
        """
        Export financial report data to CSV (separate sheets as separate files).
        Returns a tuple of (payments_csv, expenses_csv).
        """
        if not filename:
            filename = f"financial_report_{datetime.now().strftime('%Y%m%d')}"

        # Payments export
        payment_fields = ['description', 'amount', 'type', 'method', 'payment_date', 'status']
        payment_headers = ['Description', 'Amount (KES)', 'Type', 'Method', 'Date', 'Status']

        payment_data = []
        for payment in payments:
            payment_data.append({
                'description': payment.description[:50],
                'amount': float(payment.amount),
                'type': payment.get_type_display(),
                'method': payment.get_method_display(),
                'payment_date': payment.payment_date,
                'status': payment.get_status_display(),
            })

        # Expenses export
        expense_fields = ['description', 'amount', 'category', 'expense_date', 'vendor_name']
        expense_headers = ['Description', 'Amount (KES)', 'Category', 'Date', 'Vendor']

        expense_data = []
        for expense in expenses:
            expense_data.append({
                'description': expense.description[:50],
                'amount': float(expense.amount),
                'category': expense.get_category_display(),
                'expense_date': expense.expense_date,
                'vendor_name': expense.vendor_name,
            })

        return {
            'payments': cls.export(payment_data, payment_fields, f"{filename}_payments", payment_headers),
            'expenses': cls.export(expense_data, expense_fields, f"{filename}_expenses", expense_headers),
        }