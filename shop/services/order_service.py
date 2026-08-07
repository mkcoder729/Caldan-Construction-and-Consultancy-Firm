"""
Order Service - Order management and notifications.
Caldan Construction - "Building Kenya's Future, One Project at a Time."
"""

import logging
from decimal import Decimal

from django.db import transaction
from django.db.models import Sum, Count, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone

from shop.models import Order, OrderItem
from inventory.services.stock_service import StockService
from accounts.services.audit_service import AuditService
from notifications.services.email_service import EmailService

logger = logging.getLogger('caldan.shop')


class OrderService:
    """
    Service for order management operations.
    """

    @classmethod
    def get_orders(cls, filters=None, page=1, per_page=20):
        """
        Get orders with optional filters.
        """
        queryset = Order.objects.all()

        if filters:
            # Search filter
            search = filters.get('search')
            if search:
                queryset = queryset.filter(
                    Q(order_number__icontains=search) |
                    Q(client_name__icontains=search) |
                    Q(client_email__icontains=search) |
                    Q(client_phone__icontains=search)
                )

            # Status filter
            status = filters.get('status')
            if status:
                queryset = queryset.filter(status=status)

            # Date range
            date_from = filters.get('date_from')
            if date_from:
                queryset = queryset.filter(created_at__date__gte=date_from)

            date_to = filters.get('date_to')
            if date_to:
                queryset = queryset.filter(created_at__date__lte=date_to)

        queryset = queryset.order_by('-created_at')

        start = (page - 1) * per_page
        end = start + per_page
        total = queryset.count()

        return {
            'orders': queryset[start:end],
            'total': total,
            'page': page,
            'per_page': per_page,
            'total_pages': (total + per_page - 1) // per_page if total > 0 else 1,
        }

    @classmethod
    def get_order(cls, order_id):
        """Get a single order by ID."""
        return get_object_or_404(Order, id=order_id)

    @classmethod
    def get_order_by_number(cls, order_number):
        """Get a single order by order number."""
        return get_object_or_404(Order, order_number=order_number)

    @classmethod
    @transaction.atomic
    def update_order_status(cls, order_id, new_status, user=None, admin_notes=None):
        """
        Update order status with validation and notifications.
        """
        order = cls.get_order(order_id)
        old_status = order.status

        # Validate status transition
        if order.status in [Order.Status.COMPLETED, Order.Status.CANCELLED]:
            raise ValueError(f"Cannot update status from {order.status}")

        # Update status
        order.update_status(new_status, admin_notes)

        # If status is SHIPPED, DELIVERED, or COMPLETED, deduct stock if not already done
        if new_status in [Order.Status.SHIPPED, Order.Status.DELIVERED, Order.Status.COMPLETED]:
            cls.deduct_stock(order)

        # Log audit
        if user:
            AuditService.log_action(
                user=user,
                action='ORDER_STATUS_UPDATED',
                entity_type='Order',
                entity_id=str(order.id),
                details={
                    'order_number': order.order_number,
                    'old_status': old_status,
                    'new_status': new_status,
                }
            )

        logger.info(f"Order {order.order_number} status updated: {old_status} -> {new_status}")
        return order

    @classmethod
    @transaction.atomic
    def deduct_stock(cls, order):
        """
        Deduct stock for all items in an order.
        """
        for item in order.items.select_related('product'):
            product = item.product
            if product.inventory_material:
                try:
                    StockService.record_stock_out(
                        material_id=product.inventory_material.id,
                        quantity=item.quantity,
                        performed_by=None,
                        notes=f"Order {order.order_number} - {product.name}"
                    )
                    logger.info(f"Stock deducted for {product.name} from order {order.order_number}")
                except Exception as e:
                    logger.error(f"Failed to deduct stock for {product.name}: {str(e)}")
                    raise

    @classmethod
    def send_order_confirmation(cls, order):
        """
        Send order confirmation email to client.
        """
        try:
            EmailService.send_order_confirmation(order)
            logger.info(f"Order confirmation sent for {order.order_number}")
            return True
        except Exception as e:
            logger.error(f"Failed to send order confirmation: {str(e)}")
            return False

    @classmethod
    def send_status_notification(cls, order, old_status):
        """
        Send status update email to client.
        """
        try:
            EmailService.send_order_status_update(order, old_status)
            logger.info(f"Status notification sent for {order.order_number}")
            return True
        except Exception as e:
            logger.error(f"Failed to send status notification: {str(e)}")
            return False

    @classmethod
    def get_order_stats(cls):
        """
        Get order statistics for admin dashboard.
        """
        total = Order.objects.count()
        pending = Order.objects.filter(status='PENDING').count()
        processing = Order.objects.filter(status='PROCESSING').count()
        shipped = Order.objects.filter(status='SHIPPED').count()
        delivered = Order.objects.filter(status='DELIVERED').count()
        completed = Order.objects.filter(status='COMPLETED').count()
        cancelled = Order.objects.filter(status='CANCELLED').count()

        total_revenue = Order.objects.filter(
            status__in=['PAID', 'PROCESSING', 'SHIPPED', 'DELIVERED', 'COMPLETED']
        ).aggregate(total=Sum('total'))['total'] or Decimal('0.00')

        return {
            'total': total,
            'pending': pending,
            'processing': processing,
            'shipped': shipped,
            'delivered': delivered,
            'completed': completed,
            'cancelled': cancelled,
            'total_revenue': float(total_revenue),
        }

    @classmethod
    def get_order_report_data(cls, date_from=None, date_to=None):
        """
        Get detailed order report data.
        """
        if not date_from:
            date_from = timezone.now().date() - timezone.timedelta(days=30)
        if not date_to:
            date_to = timezone.now().date()

        orders = Order.objects.filter(
            created_at__date__gte=date_from,
            created_at__date__lte=date_to
        )

        # Status breakdown
        status_breakdown = {}
        status_revenue = {}
        for status_code, status_label in Order.Status.choices:
            count = orders.filter(status=status_code).count()
            if count > 0:
                revenue = orders.filter(status=status_code).aggregate(
                    total=Sum('total')
                )['total'] or Decimal('0.00')
                status_breakdown[status_label] = count
                status_revenue[status_label] = float(revenue)

        return {
            'total_orders': orders.count(),
            'total_revenue': float(orders.aggregate(total=Sum('total'))['total'] or 0),
            'date_from': date_from,
            'date_to': date_to,
            'pending': orders.filter(status='PENDING').count(),
            'processing': orders.filter(status='PROCESSING').count(),
            'shipped': orders.filter(status='SHIPPED').count(),
            'delivered': orders.filter(status='DELIVERED').count(),
            'completed': orders.filter(status='COMPLETED').count(),
            'cancelled': orders.filter(status='CANCELLED').count(),
            'status_distribution': status_breakdown,
            'status_distribution_revenue': status_revenue,
            'recent_orders': orders.order_by('-created_at')[:10],
        }