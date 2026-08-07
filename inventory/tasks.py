"""
Inventory Celery Tasks - Asynchronous operations.

Handles background tasks for inventory management including:
- Bulk alert checking
- Stock report generation
- Scheduled notifications
"""

import logging
from decimal import Decimal
from celery import shared_task
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.db.models import Sum

from inventory.models import Material, StockAlert, StockTransaction
from inventory.services import AlertService, StockService

logger = logging.getLogger('caldan.inventory')


@shared_task
def check_all_stock_alerts():
    """
    Check all materials for low stock alerts.

    Runs daily (scheduled via Celery Beat) to ensure all
    low stock materials have active alerts.

    Returns:
        dict: Summary of alerts created
    """
    logger.info("Running scheduled stock alert check...")

    try:
        created_count = AlertService.check_all_materials()

        # Get alert summary
        summary = AlertService.get_alert_summary()

        result = {
            'alerts_created': created_count,
            'open_alerts': summary['open_count'],
            'total_alerts': summary['total_count'],
            'timestamp': timezone.now().isoformat(),
        }

        logger.info(f"Stock alert check complete: {result}")
        return result

    except Exception as e:
        logger.error(f"Stock alert check failed: {str(e)}")
        raise


@shared_task
def send_daily_stock_summary():
    """
    Send a daily stock summary email to admins with an attached PDF report.

    Includes:
    - Total materials
    - Low stock count
    - Out of stock count
    - Total stock value
    """
    logger.info("Generating daily stock summary...")

    try:
        from accounts.models import User
        from notifications.services.email_service import EmailService
        from reports.services.pdf_service import PDFService

        # Get stock summary
        summary = StockService.get_stock_summary()

        # Build a fuller report dict so the PDF has section-level breakdown
        from inventory.models import Material
        from django.db.models import Sum
        materials = Material.objects.filter(is_active=True)
        report = {
            'generated_at': timezone.now().isoformat(),
            'total_materials': materials.count(),
            'low_stock_count': materials.filter(is_low_stock=True).count(),
            'out_of_stock_count': materials.filter(current_quantity=0).count(),
            'total_value': float(
                materials.aggregate(total=Sum('total_cost'))['total'] or Decimal('0')
            ),
            'summary': summary,
            'low_stock_items': list(
                materials.filter(is_low_stock=True).values(
                    'name', 'current_quantity', 'minimum_threshold', 'unit', 'category'
                )[:50]
            ),
        }

        # Generate the PDF attachment once (faster than per-admin)
        pdf_filename = (
            f"daily_stock_summary_{timezone.now().strftime('%Y%m%d')}.pdf"
        )
        pdf_bytes = b''
        try:
            pdf_path = PDFService.generate_pdf_to_file(
                template_name='pdf/inventory_full_report.html',
                context={
                    'report': report,
                    'brand_name': 'Caldan Construction and Consultancy Firm',
                    'tagline': "Building Kenya's Future, One Project at a Time.",
                    'generated_at': timezone.now(),
                },
                filename=pdf_filename.replace('.pdf', ''),
            )
            with open(pdf_path, 'rb') as fh:
                pdf_bytes = fh.read()
        except Exception as pdf_err:
            # Don't fail the whole email if the PDF generation is unhappy;
            # the HTML summary is still useful on its own.
            logger.warning(f"PDF generation skipped for daily stock summary: {pdf_err}")

        # Get all admins (we still iterate so we can attribute the audit
        # row to whoever was first, but the email always goes to ADMIN_EMAIL)
        admins = User.objects.filter(is_staff=True, is_active=True)

        admin_email = getattr(settings, 'ADMIN_EMAIL', '') or 'info.caldanconstruction@gmail.com'

        if not admins.exists():
            logger.warning("No admins found to send stock summary")
            return {'sent': 0}

        # Send to ADMIN_EMAIL once (per the platform rule "all admin-facing
        # email goes to ADMIN_EMAIL"). Individual admin users all appear in
        # the bell + audit log via notification signals elsewhere.
        attachments = [{'filename': pdf_filename, 'content': pdf_bytes}] if pdf_bytes else None
        sent_count = 0
        try:
            EmailService.send_template(
                to_email=admin_email,
                subject="Daily Stock Summary - Caldan Construction",
                template_name="email/daily_stock_summary.html",
                context={
                    'admin': admins.first(),
                    'summary': summary,
                    'date': timezone.now(),
                },
                user=admins.first(),
                email_type='DAILY_STOCK_SUMMARY',
                attachments=attachments,
            )
            sent_count = 1
        except Exception as e:
            logger.error(f"Failed to send stock summary to {admin_email}: {str(e)}")

        logger.info(f"Daily stock summary sent to {sent_count} admins")
        return {'sent': sent_count, 'total': admins.count()}

    except Exception as e:
        logger.error(f"Daily stock summary failed: {str(e)}")
        raise


@shared_task
def cleanup_old_stock_alerts(days=90):
    """
    Clean up resolved stock alerts older than specified days.

    Args:
        days: Number of days to keep resolved alerts

    Returns:
        int: Number of alerts deleted
    """
    cutoff = timezone.now() - timezone.timedelta(days=days)

    old_alerts = StockAlert.objects.filter(
        status=StockAlert.Status.RESOLVED,
        resolved_at__lt=cutoff
    )

    count = old_alerts.count()
    old_alerts.delete()

    logger.info(f"Cleaned up {count} old stock alerts (older than {days} days)")
    return count


@shared_task
def cleanup_stale_transactions(days=365):
    """
    Clean up old confirmed stock transactions.

    Args:
        days: Number of days to keep transactions

    Returns:
        int: Number of transactions deleted
    """
    cutoff = timezone.now() - timezone.timedelta(days=days)

    old_transactions = StockTransaction.objects.filter(
        status=StockTransaction.Status.CONFIRMED,
        transaction_date__lt=cutoff
    )

    count = old_transactions.count()
    old_transactions.delete()

    logger.info(f"Cleaned up {count} old stock transactions (older than {days} days)")
    return count


@shared_task
def generate_inventory_report():
    """
    Generate a comprehensive inventory report.

    Returns:
        dict: Report data
    """
    logger.info("Generating inventory report...")

    try:
        # Get all materials
        materials = Material.objects.filter(is_active=True)

        # Category breakdown
        category_data = {}
        for category in Material.Category.choices:
            cat_materials = materials.filter(category=category[0])
            count = cat_materials.count()
            if count > 0:
                category_data[category[1]] = {
                    'count': count,
                    'low_stock': cat_materials.filter(is_low_stock=True).count(),
                    'out_of_stock': cat_materials.filter(current_quantity=0).count(),
                    'total_value': float(cat_materials.aggregate(
                        total=Sum('total_cost')
                    )['total'] or Decimal('0')),
                }

        # Transaction summary
        transaction_summary = StockService.get_transaction_stats()

        # Alert summary
        alert_summary = AlertService.get_alert_summary()

        report = {
            'generated_at': timezone.now().isoformat(),
            'total_materials': materials.count(),
            'low_stock_count': materials.filter(is_low_stock=True).count(),
            'out_of_stock_count': materials.filter(current_quantity=0).count(),
            'total_value': float(materials.aggregate(
                total=Sum('total_cost')
            )['total'] or Decimal('0')),
            'category_breakdown': category_data,
            'transactions': transaction_summary,
            'alerts': alert_summary,
        }

        logger.info(f"Inventory report generated: {report['total_materials']} materials")
        return report

    except Exception as e:
        logger.error(f"Inventory report generation failed: {str(e)}")
        raise