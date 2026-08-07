"""
Alert Service - Manages low stock alerts and notifications.

Handles alert creation, resolution, notification delivery via
Email, SMS, and In-App channels.
"""

import logging
from typing import List, Optional, Dict, Any
from django.utils import timezone
from django.conf import settings

from inventory.models import Material, StockAlert
from accounts.models import User, AuditLog
from accounts.services.audit_service import AuditService

logger = logging.getLogger('caldan.inventory')


class AlertService:
    """
    Service for managing stock alerts.

    Features:
    - Automatic alert creation when materials go below threshold
    - Alert resolution when stock is replenished
    - Multi-channel notifications (Email, SMS, In-App)
    - Bulk alert checking
    """

    @classmethod
    def check_and_create_alerts(cls, material: Material) -> Optional[StockAlert]:
        """
        Check if a material needs an alert and create one if needed.

        Args:
            material: Material to check

        Returns:
            StockAlert: Created alert or None if not needed
        """
        if not material.is_active:
            return None

        if not material.is_low_stock:
            return None

        # Check if alert already exists
        existing_alert = StockAlert.objects.filter(
            material=material,
            status=StockAlert.Status.OPEN
        ).first()

        if existing_alert:
            return existing_alert

        # Create new alert
        alert = StockAlert.objects.create(
            material=material,
            message=f"Low stock: {material.name} ({material.current_quantity} {material.get_unit_display()})",
            threshold_quantity=material.minimum_threshold,
            current_quantity_at_alert=material.current_quantity,
            status=StockAlert.Status.OPEN,
        )

        # Send notifications
        cls._send_alert_notifications(material, alert)

        logger.info(f"Stock alert created for {material.name}: {alert.id}")

        return alert

    @classmethod
    def _send_alert_notifications(cls, material: Material, alert: StockAlert):
        """
        Send multi-channel notifications for a stock alert.

        Args:
            material: Material that triggered the alert
            alert: The alert object
        """
        # Get all admin users
        admins = User.objects.filter(
            is_active=True,
            is_staff=True
        )

        if not admins.exists():
            logger.warning(f"No admins found to send stock alert for {material.name}")
            return

        # Subject and message
        subject = f"[WARNING] LOW STOCK ALERT: {material.name}"
        message = (
            f"ALERT: Low stock alert for {material.name}.\n"
            f"Current quantity: {material.current_quantity} {material.get_unit_display()}\n"
            f"Minimum threshold: {material.minimum_threshold} {material.get_unit_display()}\n"
            f"Please reorder immediately."
        )

        # Send email notifications
        try:
            from notifications.services.email_service import EmailService
            for admin in admins[:3]:  # Limit to first 3 admins to avoid spam
                EmailService.send_stock_alert(material)
        except Exception as e:
            logger.error(f"Failed to send stock alert email: {str(e)}")

        # Send SMS notifications (only to admins with phone numbers)
        try:
            from notifications.services.sms_service import SMSService
            for admin in admins[:3]:
                if admin.phone:
                    sms_message = (
                        f"LOW STOCK: {material.name} at {material.current_quantity} "
                        f"{material.get_unit_display()}. Threshold: {material.minimum_threshold}. "
                        f"Please reorder."
                    )
                    SMSService.send(
                        phone_number=admin.phone,
                        message=sms_message[:160],  # SMS length limit
                        user=admin,
                        notification_type='STOCK_ALERT'
                    )
        except Exception as e:
            logger.error(f"Failed to send stock alert SMS: {str(e)}")

        # Send in-app notifications
        try:
            from notifications.services.notification_service import NotificationService
            for admin in admins:
                NotificationService.create(
                    user=admin,
                    title=f"Low Stock: {material.name}",
                    message=(
                        f"{material.name} is below minimum threshold. "
                        f"Current: {material.current_quantity} {material.get_unit_display()}. "
                        f"Threshold: {material.minimum_threshold} {material.get_unit_display()}."
                    ),
                    notification_type=NotificationService.Type.STOCK_ALERT,
                    priority=NotificationService.Priority.URGENT,
                    icon="fa-exclamation-triangle",
                    action_url="/dashboard/inventory/alerts/",
                    metadata={
                        'material_id': material.id,
                        'alert_id': alert.id,
                        'current_quantity': float(material.current_quantity),
                        'threshold': float(material.minimum_threshold),
                    }
                )
        except Exception as e:
            logger.error(f"Failed to send in-app stock alert: {str(e)}")

    @classmethod
    def resolve_alert(
        cls,
        alert_id: int,
        resolved_by,
        notes: str = '',
        request=None
    ) -> StockAlert:
        """
        Resolve a stock alert.

        Args:
            alert_id: ID of the alert to resolve
            resolved_by: User resolving the alert
            notes: Resolution notes
            request: Django request for audit

        Returns:
            StockAlert: The resolved alert
        """
        alert = StockAlert.objects.get(id=alert_id, status=StockAlert.Status.OPEN)

        alert.resolve(resolved_by, notes)

        # Log audit
        AuditService.log_action(
            user=resolved_by,
            action=AuditLog.Action.STOCK_ALERT_RESOLVED,
            entity_type='StockAlert',
            entity_id=alert.id,
            details={
                'material': alert.material.name,
                'notes': notes,
            },
            request=request
        )

        logger.info(f"Stock alert {alert.id} resolved by {resolved_by.email if resolved_by else 'SYSTEM'}")

        return alert

    @classmethod
    def get_active_alerts(cls) -> List[StockAlert]:
        """
        Get all active (open) stock alerts.

        Returns:
            List of active StockAlert objects
        """
        return list(StockAlert.objects.filter(
            status=StockAlert.Status.OPEN
        ).select_related('material', 'material__supplier').order_by('-created_at'))

    @classmethod
    def get_alert_summary(cls) -> Dict[str, Any]:
        """
        Get summary of stock alerts.

        Returns:
            dict: Alert summary statistics
        """
        open_alerts = StockAlert.objects.filter(status=StockAlert.Status.OPEN)
        resolved_alerts = StockAlert.objects.filter(status=StockAlert.Status.RESOLVED)

        return {
            'open_count': open_alerts.count(),
            'resolved_count': resolved_alerts.count(),
            'total_count': StockAlert.objects.count(),
            'open_alerts': open_alerts.select_related('material')[:10],
            'recent_resolved': resolved_alerts.select_related('material', 'resolved_by').order_by('-resolved_at')[:5],
        }

    @classmethod
    def check_all_materials(cls) -> int:
        """
        Check all materials and create alerts where needed.

        Returns:
            int: Number of alerts created
        """
        materials = Material.objects.filter(
            is_active=True,
            is_low_stock=True
        )

        created_count = 0
        for material in materials:
            alert = cls.check_and_create_alerts(material)
            if alert:
                created_count += 1

        if created_count > 0:
            logger.info(f"Bulk alert check: created {created_count} alerts")

        return created_count

    @classmethod
    def auto_resolve_for_material(cls, material: Material, user=None):
        """
        Automatically resolve all open alerts for a material if stock is above threshold.

        Args:
            material: Material to check
            user: Optional user to attribute resolution to

        Returns:
            int: Number of alerts resolved
        """
        if material.is_low_stock or material.current_quantity > material.minimum_threshold:
            updated = material.resolve_low_stock_alert()
            if updated > 0 and user:
                logger.info(f"Auto-resolved {updated} alerts for {material.name} by {user.email if user else 'SYSTEM'}")
            return updated
        return 0