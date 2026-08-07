"""
Stock Service Tests - Unit tests for stock management.

Tests cover:
- Stock IN recording
- Stock OUT recording
- Quantity validation
- Audit logging
- Alert creation
- Transaction cancellation
"""

from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone

from inventory.models import Material, StockTransaction, StockAlert
from inventory.services import StockService
from accounts.services.audit_service import AuditService

User = get_user_model()


class StockServiceTests(TestCase):
    """Test cases for StockService."""

    def setUp(self):
        """Set up test data."""
        # Create a test user
        self.user = User.objects.create_user(
            email='test@caldan.com',
            password='testpass123',
            full_name='Test Admin',
            phone='0712345678',
            is_staff=True,
        )

        # Create a test material
        self.material = Material.objects.create(
            name='Test Cement',
            category=Material.Category.CEMENT,
            unit=Material.Unit.BAG,
            current_quantity=Decimal('50'),
            minimum_threshold=Decimal('10'),
            reorder_quantity=Decimal('100'),
            unit_cost=Decimal('850'),
            is_active=True,
        )

        # Create another material for testing
        self.low_stock_material = Material.objects.create(
            name='Test Steel',
            category=Material.State.STEEL,
            unit=Material.Unit.TONNE,
            current_quantity=Decimal('5'),
            minimum_threshold=Decimal('10'),
            unit_cost=Decimal('45000'),
            is_active=True,
        )

    # =================================================================
    # STOCK IN TESTS
    # =================================================================

    def test_record_stock_in(self):
        """Test recording a stock IN transaction."""
        quantity = Decimal('25')

        transaction = StockService.record_stock_in(
            material_id=self.material.id,
            quantity=quantity,
            performed_by=self.user,
            unit_cost=Decimal('900'),
            reference='TEST-001',
            notes='Test stock IN',
            request=None,
        )

        # Check transaction was created
        self.assertIsNotNone(transaction)
        self.assertEqual(transaction.type, StockTransaction.Type.IN)
        self.assertEqual(transaction.quantity, quantity)
        self.assertEqual(transaction.unit_cost, Decimal('900'))
        self.assertEqual(transaction.status, StockTransaction.Status.CONFIRMED)

        # Check material was updated
        self.material.refresh_from_db()
        self.assertEqual(self.material.current_quantity, Decimal('75'))  # 50 + 25
        self.assertEqual(self.material.total_cost, Decimal('75') * Decimal('850'))

    def test_record_stock_in_without_unit_cost(self):
        """Test stock IN using material's unit cost."""
        quantity = Decimal('10')

        transaction = StockService.record_stock_in(
            material_id=self.material.id,
            quantity=quantity,
            performed_by=self.user,
            request=None,
        )

        # Should use material's unit cost
        self.assertEqual(transaction.unit_cost, Decimal('850'))
        self.material.refresh_from_db()
        self.assertEqual(self.material.current_quantity, Decimal('60'))

    def test_record_stock_in_negative_quantity(self):
        """Test stock IN with negative quantity (should fail)."""
        with self.assertRaises(ValueError) as context:
            StockService.record_stock_in(
                material_id=self.material.id,
                quantity=Decimal('-5'),
                performed_by=self.user,
                request=None,
            )

        self.assertIn('must be positive', str(context.exception))

    def test_record_stock_in_zero_quantity(self):
        """Test stock IN with zero quantity (should fail)."""
        with self.assertRaises(ValueError) as context:
            StockService.record_stock_in(
                material_id=self.material.id,
                quantity=Decimal('0'),
                performed_by=self.user,
                request=None,
            )

        self.assertIn('must be positive', str(context.exception))

    # =================================================================
    # STOCK OUT TESTS
    # =================================================================

    def test_record_stock_out(self):
        """Test recording a stock OUT transaction."""
        quantity = Decimal('15')

        transaction = StockService.record_stock_out(
            material_id=self.material.id,
            quantity=quantity,
            performed_by=self.user,
            reference='PROJECT-001',
            notes='Test stock OUT',
            request=None,
        )

        # Check transaction was created
        self.assertIsNotNone(transaction)
        self.assertEqual(transaction.type, StockTransaction.Type.OUT)
        self.assertEqual(transaction.quantity, quantity)
        self.assertEqual(transaction.status, StockTransaction.Status.CONFIRMED)

        # Check material was updated
        self.material.refresh_from_db()
        self.assertEqual(self.material.current_quantity, Decimal('35'))  # 50 - 15

    def test_record_stock_out_insufficient_stock(self):
        """Test stock OUT with insufficient stock (should fail)."""
        with self.assertRaises(ValueError) as context:
            StockService.record_stock_out(
                material_id=self.material.id,
                quantity=Decimal('100'),
                performed_by=self.user,
                request=None,
            )

        self.assertIn('Insufficient stock', str(context.exception))

    def test_record_stock_out_negative_quantity(self):
        """Test stock OUT with negative quantity (should fail)."""
        with self.assertRaises(ValueError) as context:
            StockService.record_stock_out(
                material_id=self.material.id,
                quantity=Decimal('-5'),
                performed_by=self.user,
                request=None,
            )

        self.assertIn('must be positive', str(context.exception))

    def test_record_stock_out_creates_alert(self):
        """Test stock OUT creates low stock alert."""
        quantity = Decimal('3')  # Will bring stock from 5 to 2 (below threshold 10)

        transaction = StockService.record_stock_out(
            material_id=self.low_stock_material.id,
            quantity=quantity,
            performed_by=self.user,
            request=None,
        )

        # Check alert was created
        alert = StockAlert.objects.filter(
            material=self.low_stock_material,
            status=StockAlert.Status.OPEN
        ).first()

        self.assertIsNotNone(alert)
        self.assertEqual(alert.material, self.low_stock_material)
        self.assertIn('Low stock', alert.message)

        # Material should be marked as low stock
        self.low_stock_material.refresh_from_db()
        self.assertTrue(self.low_stock_material.is_low_stock)

    # =================================================================
    # TRANSACTION CANCELLATION TESTS
    # =================================================================

    def test_cancel_transaction(self):
        """Test cancelling a transaction."""
        # Create a transaction
        original_quantity = self.material.current_quantity
        transaction = StockService.record_stock_in(
            material_id=self.material.id,
            quantity=Decimal('10'),
            performed_by=self.user,
            request=None,
        )

        # Verify material was updated
        self.material.refresh_from_db()
        self.assertEqual(self.material.current_quantity, original_quantity + Decimal('10'))

        # Cancel the transaction
        cancelled = StockService.cancel_transaction(
            transaction_id=transaction.id,
            cancelled_by=self.user,
            reason='Test cancellation',
            request=None,
        )

        # Verify transaction was cancelled
        self.assertEqual(cancelled.status, StockTransaction.Status.CANCELLED)

        # Verify material was reversed
        self.material.refresh_from_db()
        self.assertEqual(self.material.current_quantity, original_quantity)

    def test_cancel_already_cancelled_transaction(self):
        """Test cancelling an already cancelled transaction."""
        transaction = StockService.record_stock_in(
            material_id=self.material.id,
            quantity=Decimal('10'),
            performed_by=self.user,
            request=None,
        )

        # Cancel once
        StockService.cancel_transaction(
            transaction_id=transaction.id,
            cancelled_by=self.user,
            request=None,
        )

        # Cancel again (should fail)
        with self.assertRaises(ValueError) as context:
            StockService.cancel_transaction(
                transaction_id=transaction.id,
                cancelled_by=self.user,
                request=None,
            )

        self.assertIn('already cancelled', str(context.exception))

    # =================================================================
    # GET STOCK SUMMARY TESTS
    # =================================================================

    def test_get_stock_summary(self):
        """Test getting stock summary."""
        summary = StockService.get_stock_summary()

        self.assertIn('total_materials', summary)
        self.assertIn('low_stock_count', summary)
        self.assertIn('out_of_stock_count', summary)
        self.assertIn('total_value', summary)
        self.assertIn('recent_transactions', summary)

        # Our setup has 2 materials
        self.assertEqual(summary['total_materials'], 2)

        # One material is low stock (test_steel)
        self.assertEqual(summary['low_stock_count'], 1)

        # Total value should be sum of both materials
        expected_value = (Decimal('50') * Decimal('850')) + (Decimal('5') * Decimal('45000'))
        self.assertEqual(Decimal(str(summary['total_value'])), expected_value)

    # =================================================================
    # GET MATERIAL TRANSACTIONS TESTS
    # =================================================================

    def test_get_material_transactions(self):
        """Test getting transactions for a material."""
        # Create some transactions
        StockService.record_stock_in(
            material_id=self.material.id,
            quantity=Decimal('10'),
            performed_by=self.user,
            request=None,
        )
        StockService.record_stock_out(
            material_id=self.material.id,
            quantity=Decimal('5'),
            performed_by=self.user,
            request=None,
        )

        transactions = StockService.get_material_transactions(
            material_id=self.material.id,
            limit=10,
        )

        self.assertEqual(len(transactions), 2)
        self.assertEqual(transactions[0].type, StockTransaction.Type.OUT)  # Most recent first
        self.assertEqual(transactions[1].type, StockTransaction.Type.IN)

    # =================================================================
    # AUDIT LOGGING TESTS
    # =================================================================

    def test_stock_in_audit_logging(self):
        """Test stock IN creates audit log."""
        self.assertEqual(AuditService.objects.count(), 0)

        StockService.record_stock_in(
            material_id=self.material.id,
            quantity=Decimal('10'),
            performed_by=self.user,
            request=None,
        )

        # One audit log should be created
        audit_logs = AuditService.objects.filter(action='STOCK_IN')
        self.assertEqual(audit_logs.count(), 1)

        # Check log details
        log = audit_logs.first()
        self.assertEqual(log.entity_type, 'Material')
        self.assertEqual(str(log.entity_id), str(self.material.id))

    def test_stock_out_audit_logging(self):
        """Test stock OUT creates audit log."""
        StockService.record_stock_out(
            material_id=self.material.id,
            quantity=Decimal('5'),
            performed_by=self.user,
            request=None,
        )

        audit_logs = AuditService.objects.filter(action='STOCK_OUT')
        self.assertEqual(audit_logs.count(), 1)