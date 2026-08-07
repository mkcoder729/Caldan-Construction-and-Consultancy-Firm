import logging
from django.utils import timezone
from datetime import timedelta
from django.db.models import Q
from notifications.services.router_service import NotificationRouter
from notifications.services.audit_report_service import AuditReportService
from inventory.models import Material
from shop.models import Order
from accounts.models import User

logger = logging.getLogger('caldan.reminders')


class ReminderService:
    """Automated reminder engine for various events."""

    @classmethod
    def check_low_stock(cls):
        """Check and send low stock alerts."""
        low_stock_materials = Material.objects.filter(
            is_low_stock=True,
            is_active=True
        )
        alerts_sent = 0
        admin = User.objects.filter(is_superuser=True).first()

        if admin:
            for material in low_stock_materials:
                # Check if an alert for THIS material was already sent today.
                # The previous version checked globally (one alert per day for
                # the whole platform), which silently dropped alerts for any
                # material after the first.
                from notifications.models import Notification
                existing = Notification.objects.filter(
                    user=admin,
                    type='STOCK_ALERT',
                    created_at__date=timezone.now().date(),
                    metadata__material_id=material.id,
                ).exists()

                if not existing:
                    NotificationRouter.route_stock_alert(material, admin)
                    alerts_sent += 1

        logger.info(f"Low stock alerts sent: {alerts_sent}")
        return alerts_sent

    @classmethod
    def check_pending_orders(cls):
        """Check for pending orders that need attention."""
        pending_orders = Order.objects.filter(
            status='PENDING',
            created_at__lt=timezone.now() - timedelta(hours=24)
        )
        notifications_sent = 0
        admin = User.objects.filter(is_superuser=True).first()

        if admin:
            for order in pending_orders:
                # Per-order de-duplication (the previous global check
                # suppressed all but the first reminder per day).
                from notifications.models import Notification
                existing = Notification.objects.filter(
                    user=admin,
                    type='REMINDER',
                    created_at__date=timezone.now().date(),
                    metadata__order_id=order.id,
                ).exists()

                if not existing:
                    # Calculate time since created
                    time_diff = timezone.now() - order.created_at
                    hours = int(time_diff.total_seconds() // 3600)

                    NotificationRouter.route(
                        user=admin,
                        title=f"⏰ Pending Order: {order.order_number}",
                        message=f"Order {order.order_number} by {order.client_name} has been pending for {hours} hours.",
                        notification_type='REMINDER',
                        priority='MEDIUM',
                        icon='fa-clock',
                        action_url=f'/dashboard/shop/orders/{order.id}/',
                        send_email=True,
                        send_sms=False,
                        metadata={'order_id': order.id}
                    )
                    notifications_sent += 1

        logger.info(f"Pending order reminders sent: {notifications_sent}")
        return notifications_sent

    @classmethod
    def run_daily_checks(cls):
        """Run all daily reminder checks."""
        results = {
            'low_stock_alerts': cls.check_low_stock(),
            'pending_order_reminders': cls.check_pending_orders(),
            'timestamp': timezone.now().isoformat()
        }
        logger.info(f"Daily reminders completed: {results}")
        return results

    @classmethod
    def send_bi_weekly_audit(cls):
        """Generate and send bi-weekly audit report."""
        return AuditReportService.generate_and_send()