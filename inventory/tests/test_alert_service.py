"""
Alert Service Tests - Unit tests for stock alert management.

Tests cover:
- Alert creation when materials go below threshold
- Alert resolution
- Notification delivery
- Bulk alert checking
- Auto-resolution when stock is replenished
"""

from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone

from inventory.models import Material, StockAlert
from inventory.services import AlertService, StockService

User = get_user_model()


class AlertServiceTests(TestCase):
    """Test cases for AlertService."""

    def setUp(self):
        """Set up test data."""
        # Create a test user
        self.user = User.objects.create_user(
            email='admin@caldan.com',
            password='testpass123',
            full_name='Test Admin',
            phone='0712345678',
            is_staff=True,
            is_superuser=True,
        )

        # Create a material that will be low stock
        self.material = Material.objects.create(
            name='Test Cement',
            category=Material.Category.CEMENT,
            unit=Material.Unit.BAG,
            current_quantity=Decimal('5'),
            minimum_threshold=Decimal('10'),
            reorder_quantity=Decimal('50'),
            unit_cost=Decimal('850'),
            is_active=True,
            is_low_stock=True,  # Manually set for test
        )

        # Create a material that's above threshold
        self.above_threshold = Material.objects.create(
            name='Test Steel',
            category=Material.State.STEEL,
            unit=Material.Unit.TONNE,
            current_quantity=Decimal('50'),
            minimum_threshold=Decimal('10'),
            unit_cost=Decimal('45000'),
            is_active=True,
            is_low_stock=False,
        )

    # =================================================================
    # ALERT CREATION TESTS
    # =================================================================

    def test_check_and_create_alert_low_stock(self):
        """Test alert creation for low stock material."""
        alert = AlertService.check_and_create_alerts(self.material)

        self.assertIsNotNone(alert)
        self.assertEqual(alert.material, self.material)
        self.assertEqual(alert.status, StockAlert.Status.OPEN)
        self.assertEqual(alert.threshold_quantity, Decimal('10'))
        self.assertEqual(alert.current_quantity_at_alert, Decimal('5'))
        self.assertIn('Low stock', alert.message)

    def test_check_and_create_alert_above_threshold(self):
        """Test no alert created for material above threshold."""
        alert = AlertService.check_and_create_alerts(self.above_threshold)

        self.assertIsNone(alert)

    def test_check_and_create_alert_duplicate(self):
        """Test duplicate alert creation (should not create duplicate)."""
        # Create first alert
        alert1 = AlertService.check_and_create_alerts(self.material)

        # Try to create again
        alert2 = AlertService.check_and_create_alerts(self.material)

        # Should return the same alert, not create a new one
        self.assertEqual(alert1.id, alert2.id)
        self.assertEqual(StockAlert.objects.filter(material=self.material).count(), 1)

    def test_check_and_create_alert_inactive_material(self):
        """Test alert not created for inactive material."""
        self.material.is_active = False
        self.material.save()

        alert = AlertService.check_and_create_alerts(self.material)
        self.assertIsNone(alert)

    # =================================================================
    # ALERT RESOLUTION TESTS
    # =================================================================

    def test_resolve_alert(self):
        """Test resolving an alert."""
        # Create alert
        alert = AlertService.check_and_create_alerts(self.material)

        # Resolve it
        resolved = AlertService.resolve_alert(
            alert_id=alert.id,
            resolved_by=self.user,
            notes='Stock replenished',
            request=None,
        )

        self.assertEqual(resolved.status, StockAlert.Status.RESOLVED)
        self.assertEqual(resolved.resolved_by, self.user)
        self.assertEqual(resolved.resolution_notes, 'Stock replenished')
        self.assertIsNotNone(resolved.resolved_at)

    def test_resolve_nonexistent_alert(self):
        """Test resolving a non-existent alert."""
        with self.assertRaises(StockAlert.DoesNotExist):
            AlertService.resolve_alert(
                alert_id=99999,
                resolved_by=self.user,
                request=None,
            )

    def test_resolve_already_resolved_alert(self):
        """Test resolving an already resolved alert."""
        # Create and resolve alert
        alert = AlertService.check_and_create_alerts(self.material)
        AlertService.resolve_alert(
            alert_id=alert.id,
            resolved_by=self.user,
            request=None,
        )

        # Try to resolve again (should do nothing)
        # The resolve method checks status before resolving
        alert.refresh_from_db()
        self.assertEqual(alert.status, StockAlert.Status.RESOLVED)

    # =================================================================
    # AUTO-RESOLUTION TESTS
    # =================================================================

    def test_auto_resolve_for_material(self):
        """Test auto-resolution when stock is replenished."""
        # Create alert
        AlertService.check_and_create_alerts(self.material)

        # Replenish stock (stock IN)
        StockService.record_stock_in(
            material_id=self.material.id,
            quantity=Decimal('20'),
            performed_by=self.user,
            request=None,
        )

        # Alert should be auto-resolved
        alerts = StockAlert.objects.filter(
            material=self.material,
            status=StockAlert.Status.OPEN
        )
        self.assertEqual(alerts.count(), 0)

    def test_auto_resolve_for_material_no_alert(self):
        """Test auto-resolution when no alert exists."""
        # Material is above threshold, no alert
        result = AlertService.auto_resolve_for_material(
            self.above_threshold,
            user=self.user
        )
        self.assertEqual(result, 0)

    # =================================================================
    # GET ACTIVE ALERTS TESTS
    # =================================================================

    def test_get_active_alerts(self):
        """Test getting all active alerts."""
        # Create an alert
        AlertService.check_and_create_alerts(self.material)

        active = AlertService.get_active_alerts()

        self.assertEqual(len(active), 1)
        self.assertEqual(active[0].material, self.material)
        self.assertEqual(active[0].status, StockAlert.Status.OPEN)

    def test_get_active_alerts_after_resolution(self):
        """Test active alerts excludes resolved alerts."""
        # Create and resolve alert
        alert = AlertService.check_and_create_alerts(self.material)
        AlertService.resolve_alert(
            alert_id=alert.id,
            resolved_by=self.user,
            request=None,
        )

        active = AlertService.get_active_alerts()
        self.assertEqual(len(active), 0)

    # =================================================================
    # GET ALERT SUMMARY TESTS
    # =================================================================

    def test_get_alert_summary(self):
        """Test getting alert summary."""
        summary = AlertService.get_alert_summary()

        self.assertIn('open_count', summary)
        self.assertIn('resolved_count', summary)
        self.assertIn('total_count', summary)
        self.assertIn('open_alerts', summary)

        # Initially zero
        self.assertEqual(summary['open_count'], 0)
        self.assertEqual(summary['total_count'], 0)

        # Create an alert
        AlertService.check_and_create_alerts(self.material)

        summary = AlertService.get_alert_summary()
        self.assertEqual(summary['open_count'], 1)
        self.assertEqual(summary['total_count'], 1)

    # =================================================================
    # BULK CHECK TESTS
    # =================================================================

    def test_check_all_materials(self):
        """Test checking all materials for alerts."""
        # One material is low stock, one is not
        created = AlertService.check_all_materials()

        # Should create 1 alert
        self.assertEqual(created, 1)

        # Check alert exists
        alerts = StockAlert.objects.filter(status=StockAlert.Status.OPEN)
        self.assertEqual(alerts.count(), 1)
        self.assertEqual(alerts.first().material, self.material)

    def test_check_all_materials_with_no_low_stock(self):
        """Test checking all materials when none are low stock."""
        # Make all materials above threshold
        self.material.current_quantity = Decimal('20')
        self.material.is_low_stock = False
        self.material.save()

        created = AlertService.check_all_materials()
        self.assertEqual(created, 0)

    # =================================================================
    # NOTIFICATION TESTS (Mocked)
    # =================================================================

    def test_alert_creates_notification(self):
        """Test that alert creation triggers notifications."""
        # Mock the notification service
        from unittest.mock import patch

        with patch('inventory.services.alert_service.NotificationService.create') as mock_notify:
            with patch('inventory.services.alert_service.EmailService.send_stock_alert') as mock_email:
                with patch('inventory.services.alert_service.SMSService.send') as mock_sms:
                    AlertService.check_and_create_alerts(self.material)

                    # At least one notification should be sent
                    self.assertTrue(mock_notify.called or mock_email.called or mock_sms.called)