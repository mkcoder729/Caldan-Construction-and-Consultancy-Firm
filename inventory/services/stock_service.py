"""
Stock Service - Core business logic for inventory management.

Handles all stock operations including IN/OUT transactions,
material updates, quantity validation, and audit logging.
"""

import logging
from decimal import Decimal
from typing import Optional, Dict, Any, Tuple, List
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from django.shortcuts import get_object_or_404

from inventory.models import Material, StockTransaction, StockAlert
from accounts.models import AuditLog
from accounts.services.audit_service import AuditService

logger = logging.getLogger('caldan.inventory')


class StockService:
    """
    Service for all stock management operations.

    Features:
    - Record stock IN/OUT with transaction atomicity
    - Automatic material quantity updates
    - Low stock alert creation
    - Comprehensive audit logging
    - Transaction reversal on cancellation
    """

    @classmethod
    @transaction.atomic
    def record_stock_in(
        cls,
        material_id: int,
        quantity: Decimal,
        performed_by,
        unit_cost: Optional[Decimal] = None,
        reference: str = '',
        notes: str = '',
        receipt=None,
        receipt_number: str = '',
        request=None
    ) -> StockTransaction:
        """
        Record a stock IN transaction.

        Args:
            material_id: ID of the material
            quantity: Quantity being added
            performed_by: User performing the transaction
            unit_cost: Optional unit cost (uses material's unit_cost if not provided)
            reference: External reference
            notes: Additional notes
            receipt: Receipt image file
            receipt_number: Receipt number
            request: Django request for audit

        Returns:
            StockTransaction: The created transaction

        Raises:
            ValueError: If quantity is invalid
        """
        # Validate input
        if quantity <= 0:
            raise ValueError("Quantity must be positive")

        # Get material
        material = get_object_or_404(Material, id=material_id)

        # Use material's unit_cost if not provided
        if unit_cost is None:
            unit_cost = material.unit_cost

        # Record quantity before
        quantity_before = material.current_quantity

        # Create transaction
        transaction_obj = StockTransaction.objects.create(
            material=material,
            type=StockTransaction.Type.IN,
            quantity=quantity,
            unit_cost=unit_cost,
            performed_by=performed_by,
            reference=reference,
            notes=notes,
            receipt=receipt,
            receipt_number=receipt_number,
            quantity_before=quantity_before,
            status=StockTransaction.Status.CONFIRMED,
        )

        # Apply transaction (updates material quantity)
        transaction_obj._apply_transaction()

        # Log audit
        AuditService.log_action(
            user=performed_by,
            action=AuditLog.Action.STOCK_IN,
            entity_type='Material',
            entity_id=material.id,
            details={
                'material': material.name,
                'quantity': float(quantity),
                'unit_cost': float(unit_cost),
                'total_cost': float(transaction_obj.total_cost),
                'quantity_before': float(quantity_before),
                'quantity_after': float(material.current_quantity),
                'reference': reference,
                'receipt_number': receipt_number,
            },
            request=request
        )

        logger.info(
            f"Stock IN: {quantity} {material.get_unit_display()} of {material.name} "
            f"by {performed_by.email if performed_by else 'SYSTEM'}"
        )

        return transaction_obj

    @classmethod
    @transaction.atomic
    def record_stock_out(
        cls,
        material_id: int,
        quantity: Decimal,
        performed_by,
        reference: str = '',
        notes: str = '',
        request=None
    ) -> StockTransaction:
        """
        Record a stock OUT transaction.

        Args:
            material_id: ID of the material
            quantity: Quantity being removed
            performed_by: User performing the transaction
            reference: External reference
            notes: Additional notes
            request: Django request for audit

        Returns:
            StockTransaction: The created transaction

        Raises:
            ValueError: If quantity is invalid or insufficient stock
        """
        # Validate input
        if quantity <= 0:
            raise ValueError("Quantity must be positive")

        # Get material
        material = get_object_or_404(Material, id=material_id)

        # Check sufficient stock
        if quantity > material.current_quantity:
            raise ValueError(
                f"Insufficient stock. Available: {material.current_quantity} "
                f"{material.get_unit_display()}, Requested: {quantity}"
            )

        # Record quantity before
        quantity_before = material.current_quantity

        # Create transaction
        transaction_obj = StockTransaction.objects.create(
            material=material,
            type=StockTransaction.Type.OUT,
            quantity=quantity,
            unit_cost=material.unit_cost,
            performed_by=performed_by,
            reference=reference,
            notes=notes,
            quantity_before=quantity_before,
            status=StockTransaction.Status.CONFIRMED,
        )

        # Apply transaction (updates material quantity)
        transaction_obj._apply_transaction()

        # Create alert if low stock
        if material.is_low_stock:
            StockAlert.objects.get_or_create(
                material=material,
                status=StockAlert.Status.OPEN,
                defaults={
                    'message': f"Low stock: {material.name} "
                               f"({material.current_quantity} {material.get_unit_display()})",
                    'threshold_quantity': material.minimum_threshold,
                    'current_quantity_at_alert': material.current_quantity,
                }
            )

            # Trigger notification via signal or direct call
            from inventory.signals import send_stock_alert_notifications
            send_stock_alert_notifications(material)

        # Log audit
        AuditService.log_action(
            user=performed_by,
            action=AuditLog.Action.STOCK_OUT,
            entity_type='Material',
            entity_id=material.id,
            details={
                'material': material.name,
                'quantity': float(quantity),
                'unit_cost': float(material.unit_cost),
                'total_cost': float(transaction_obj.total_cost),
                'quantity_before': float(quantity_before),
                'quantity_after': float(material.current_quantity),
                'reference': reference,
            },
            request=request
        )

        logger.info(
            f"Stock OUT: {quantity} {material.get_unit_display()} of {material.name} "
            f"by {performed_by.email if performed_by else 'SYSTEM'}"
        )

        return transaction_obj

    @classmethod
    @transaction.atomic
    def cancel_transaction(
        cls,
        transaction_id: int,
        cancelled_by,
        reason: str = '',
        request=None
    ) -> StockTransaction:
        """
        Cancel a stock transaction and reverse its effects.

        Args:
            transaction_id: ID of the transaction to cancel
            cancelled_by: User cancelling the transaction
            reason: Reason for cancellation
            request: Django request for audit

        Returns:
            StockTransaction: The cancelled transaction

        Raises:
            ValueError: If transaction cannot be cancelled
        """
        transaction_obj = get_object_or_404(StockTransaction, id=transaction_id)

        if transaction_obj.status == StockTransaction.Status.CANCELLED:
            raise ValueError("Transaction is already cancelled")

        if transaction_obj.status != StockTransaction.Status.CONFIRMED:
            raise ValueError("Only confirmed transactions can be cancelled")

        # Store data for audit
        material_name = transaction_obj.material.name
        quantity = transaction_obj.quantity
        transaction_type = transaction_obj.type

        # Cancel the transaction (reverses effects)
        transaction_obj.cancel(cancelled_by, reason)

        # Log audit
        AuditService.log_action(
            user=cancelled_by,
            action=AuditLog.Action.STOCK_ADJUSTED,
            entity_type='StockTransaction',
            entity_id=transaction_obj.id,
            details={
                'cancelled_transaction': transaction_obj.id,
                'material': material_name,
                'original_type': transaction_type,
                'quantity': float(quantity),
                'reason': reason,
                'quantity_after_cancel': float(transaction_obj.material.current_quantity),
            },
            request=request
        )

        logger.info(
            f"Transaction {transaction_obj.id} cancelled by {cancelled_by.email if cancelled_by else 'SYSTEM'}: {reason}"
        )

        return transaction_obj

    @classmethod
    def get_material_transactions(
        cls,
        material_id: int,
        limit: int = 50
    ) -> List[StockTransaction]:
        """
        Get recent transactions for a material.

        Args:
            material_id: ID of the material
            limit: Maximum number of transactions

        Returns:
            List of StockTransaction objects
        """
        return StockTransaction.objects.filter(
            material_id=material_id
        ).select_related('performed_by', 'cancelled_by').order_by('-transaction_date')[:limit]

    @classmethod
    def get_stock_summary(cls) -> Dict[str, Any]:
        """
        Get overall stock summary for dashboard.

        Returns:
            dict: Stock summary statistics
        """
        materials = Material.objects.filter(is_active=True)

        total_materials = materials.count()
        low_stock_count = materials.filter(is_low_stock=True).count()
        out_of_stock_count = materials.filter(current_quantity=0).count()
        total_value = materials.aggregate(total=Sum('total_cost'))['total'] or Decimal('0')

        # Recent transactions
        recent_transactions = StockTransaction.objects.filter(
            status=StockTransaction.Status.CONFIRMED
        ).select_related('material', 'performed_by').order_by('-transaction_date')[:10]

        # Low stock materials
        low_stock_materials = materials.filter(is_low_stock=True).select_related('supplier')[:10]

        # Category breakdown
        category_breakdown = {}
        for category in Material.Category.choices:
            cat_materials = materials.filter(category=category[0])
            count = cat_materials.count()
            if count > 0:
                category_breakdown[category[1]] = {
                    'count': count,
                    'value': float(cat_materials.aggregate(total=Sum('total_cost'))['total'] or Decimal('0')),
                    'low_stock': cat_materials.filter(is_low_stock=True).count(),
                    'out_of_stock': cat_materials.filter(current_quantity=0).count(),
                }

        return {
            'total_materials': total_materials,
            'low_stock_count': low_stock_count,
            'out_of_stock_count': out_of_stock_count,
            'total_value': float(total_value),
            'recent_transactions': recent_transactions,
            'low_stock_materials': low_stock_materials,
            'category_breakdown': category_breakdown,
        }

    @classmethod
    def get_transaction_stats(cls) -> Dict[str, Any]:
        """
        Get transaction statistics.

        Returns:
            dict: Transaction statistics
        """
        today = timezone.now().date()
        start_of_month = today.replace(day=1)

        return {
            'total_transactions': StockTransaction.objects.count(),
            'today_transactions': StockTransaction.objects.filter(
                transaction_date__date=today
            ).count(),
            'month_transactions': StockTransaction.objects.filter(
                transaction_date__date__gte=start_of_month
            ).count(),
            'pending_transactions': StockTransaction.objects.filter(
                status=StockTransaction.Status.PENDING
            ).count(),
        }