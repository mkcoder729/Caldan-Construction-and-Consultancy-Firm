"""
PDF Service - Generate PDF documents using Playwright.
Caldan Construction - "Building Kenya's Future, One Project at a Time."
"""

import logging
import os
from datetime import datetime

from django.conf import settings
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils import timezone

logger = logging.getLogger('caldan.reports')


class PDFService:
    """
    Service for generating PDF documents using Playwright with headless Chromium.
    Supports A4 and A5 formats with custom margins and styling.
    """

    @classmethod
    def generate_pdf(cls, template_name, context, filename, format='A4'):
        """
        Generate a PDF from an HTML template using Playwright.

        Args:
            template_name: Path to the HTML template
            context: Template context dict
            filename: Output filename (without extension)
            format: Paper format ('A4' or 'A5')

        Returns:
            HttpResponse with PDF content
        """
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            logger.error("playwright not installed. Cannot generate PDF.")
            raise ImportError(
                "playwright is required for PDF generation. "
                "Run: pip install playwright && playwright install"
            )

        # Render HTML
        html_string = render_to_string(template_name, context)

        # Generate PDF
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.set_content(html_string, wait_until="networkidle")

                margins = {
                    'top': '1.5cm',
                    'bottom': '1.5cm',
                    'left': '1.5cm',
                    'right': '1.5cm',
                }

                if format == 'A5':
                    pdf_options = {
                        'format': 'A5',
                        'print_background': True,
                        'margin': margins,
                    }
                else:
                    pdf_options = {
                        'format': 'A4',
                        'print_background': True,
                        'margin': margins,
                    }

                pdf_bytes = page.pdf(**pdf_options)
                browser.close()

            response = HttpResponse(pdf_bytes, content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="{filename}.pdf"'
            response['Content-Length'] = len(pdf_bytes)
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
            response['X-Content-Type-Options'] = 'nosniff'

            logger.info(f"PDF generated: {filename}.pdf ({len(pdf_bytes)} bytes)")
            return response

        except Exception as e:
            logger.error(f"PDF generation failed: {str(e)}")
            import traceback
            traceback.print_exc()
            raise

    @classmethod
    def generate_pdf_to_file(cls, template_name, context, filename, output_dir=None, format='A4'):
        """
        Generate a PDF and save it to a file (for archiving).

        Args:
            template_name: Path to the HTML template
            context: Template context dict
            filename: Output filename (without extension)
            output_dir: Directory to save the file (default: media/reports/)
            format: Paper format ('A4' or 'A5')

        Returns:
            Path to the generated PDF file
        """
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            logger.error("playwright not installed. Cannot generate PDF.")
            raise ImportError("playwright is required for PDF generation.")

        if not output_dir:
            output_dir = os.path.join(settings.MEDIA_ROOT, 'reports')

        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"{filename}.pdf")

        html_string = render_to_string(template_name, context)

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_content(html_string, wait_until="networkidle")

            margins = {
                'top': '1.5cm',
                'bottom': '1.5cm',
                'left': '1.5cm',
                'right': '1.5cm',
            }

            if format == 'A5':
                pdf_options = {'format': 'A5', 'print_background': True, 'margin': margins}
            else:
                pdf_options = {'format': 'A4', 'print_background': True, 'margin': margins}

            page.pdf(path=output_path, **pdf_options)
            browser.close()

        logger.info(f"PDF saved to: {output_path}")
        return output_path

    @classmethod
    def generate_project_report_pdf(cls, project, report_data):
        filename = f"project_report_{project.project_code}_{timezone.now().strftime('%Y%m%d')}"
        context = {
            'project': project,
            'report_data': report_data,
            'brand_name': 'Caldan Construction',
            'tagline': 'Building Kenya\'s Future, One Project at a Time.',
            'generated_at': timezone.now(),
        }
        return cls.generate_pdf('pdf/project_report.html', context, filename)

    @classmethod
    def generate_inventory_report_pdf(cls, report_data):
        filename = f"inventory_report_{timezone.now().strftime('%Y%m%d')}"
        context = {
            'report': report_data,
            'brand_name': 'Caldan Construction',
            'tagline': 'Building Kenya\'s Future, One Project at a Time.',
            'generated_at': timezone.now(),
        }
        return cls.generate_pdf('pdf/inventory_report.html', context, filename)

    @classmethod
    def generate_financial_report_pdf(cls, report_data):
        filename = f"financial_report_{timezone.now().strftime('%Y%m%d')}"
        context = {
            'report': report_data,
            'brand_name': 'Caldan Construction',
            'tagline': 'Building Kenya\'s Future, One Project at a Time.',
            'generated_at': timezone.now(),
        }
        return cls.generate_pdf('pdf/financial_report.html', context, filename)

    @classmethod
    def generate_audit_report_pdf(cls, audit_data):
        filename = f"audit_report_{timezone.now().strftime('%Y%m%d')}"
        # Spread audit_data into the context so the template can read keys
        # directly (e.g. `{{ total_actions }}`, `{{ logs }}`) without a wrapper.
        context = {
            **audit_data,
            'brand_name': 'Caldan Construction',
            'tagline': 'Building Kenya\'s Future, One Project at a Time.',
            'generated_at': timezone.now(),
        }
        return cls.generate_pdf('pdf/audit_report.html', context, filename)

    @classmethod
    def generate_receipt_pdf(cls, payment, receipt_number):
        filename = f"receipt_{receipt_number}_{timezone.now().strftime('%Y%m%d')}"
        context = {
            'payment': payment,
            'receipt_number': receipt_number,
            'brand_name': 'Caldan Construction',
            'tagline': 'Building Kenya\'s Future, One Project at a Time.',
            'generated_at': timezone.now(),
        }
        return cls.generate_pdf('pdf/receipt.html', context, filename, format='A5')

    @classmethod
    def generate_order_invoice(cls, order):
        """
        Generate an order invoice PDF.

        Args:
            order: Order object

        Returns:
            HttpResponse with PDF content
        """
        filename = f"Caldan_Receipt_{order.order_number}"

        context = {
            'order': order,
            'items': order.items.all(),
            'brand_name': 'Caldan Construction',
            'tagline': 'Building Kenya\'s Future, One Project at a Time.',
            'generated_at': timezone.now(),
        }

        try:
            return cls.generate_pdf('pdf/order_invoice.html', context, filename, format='A4')
        except Exception as e:
            logger.error(f"Order invoice generation failed for {order.order_number}: {str(e)}")
            raise