"""
Celery tasks for Shop app.
Caldan Construction - "Building Kenya's Future, One Project at a Time."
"""

import logging

from celery import shared_task
from django.utils import timezone
from datetime import timedelta

from shop.models import Order
from shop.services import OrderService

logger = logging.getLogger('caldan.shop')


@shared_task
def send_order_confirmation_email(order_id):
    """
    Send order confirmation email asynchronously.
    """
    try:
        order = Order.objects.get(id=order_id)
        success = OrderService.send_order_confirmation(order)

        if success:
            logger.info(f"Order confirmation email sent for {order.order_number}")
        else:
            logger.error(f"Failed to send order confirmation for {order.order_number}")

        return success

    except Order.DoesNotExist:
        logger.error(f"Order {order_id} not found for email")
        return False
    except Exception as e:
        logger.error(f"Order confirmation email task failed: {str(e)}")
        return False


@shared_task
def send_status_update_email(order_id, old_status):
    """
    Send status update email asynchronously.
    """
    try:
        order = Order.objects.get(id=order_id)
        success = OrderService.send_status_notification(order, old_status)

        if success:
            logger.info(f"Status update email sent for {order.order_number}")
        else:
            logger.error(f"Failed to send status update for {order.order_number}")

        return success

    except Order.DoesNotExist:
        logger.error(f"Order {order_id} not found for status update email")
        return False
    except Exception as e:
        logger.error(f"Status update email task failed: {str(e)}")
        return False


@shared_task
def auto_cancel_pending_orders():
    """
    Automatically cancel pending orders after 7 days.
    """
    cutoff_date = timezone.now() - timedelta(days=7)
    pending_orders = Order.objects.filter(
        status='PENDING',
        created_at__lte=cutoff_date
    )

    cancelled_count = 0
    for order in pending_orders:
        try:
            order.status = 'CANCELLED'
            order.admin_notes += f"\n\n[{timezone.now().strftime('%Y-%m-%d %H:%M')}] Auto-cancelled - pending for over 7 days"
            order.save(update_fields=['status', 'admin_notes'])
            cancelled_count += 1
            logger.info(f"Auto-cancelled order {order.order_number}")
        except Exception as e:
            logger.error(f"Failed to auto-cancel order {order.order_number}: {str(e)}")

    logger.info(f"Auto-cancelled {cancelled_count} orders")
    return cancelled_count