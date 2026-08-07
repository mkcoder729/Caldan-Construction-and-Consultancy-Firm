"""
Inventory View Tests - Integration tests for dashboard views.

Tests cover:
- Materials list with filters and pagination
- Material CRUD operations
- Stock IN/OUT forms
- Alert list and resolution
- Supplier management
- Delivery management
"""

from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone

from inventory.models import Material, StockTransaction, StockAlert, Supplier, Delivery
from inventory.services import StockService

User = get_user_model()


class InventoryViewTests(TestCase):
    """Test cases for inventory dashboard views."""

    def setUp(self):
        """Set up test data and client."""
        self.client = Client()

        # Create admin user
        self.admin = User.objects.create_user(
            email='admin@caldan.com',
            password='testpass123',
            full_name='Test Admin',
            phone='0712345678',
            is_staff=True,
            is_superuser=True,
        )

        # Create regular user (non-admin)
        self.user = User.objects.create_user(
            email='user@caldan.com',
            password='testpass123',
            full_name='Test User',
            phone='0712345679',
            is_staff=False,
        )

        # Create test materials
        self.material1 = Material.objects.create(
            name='Test Cement',
            category=Material.Category.CEMENT,
            unit=Material.Unit.BAG,
            current_quantity=Decimal('50'),
            minimum_threshold=Decimal('10'),
            unit_cost=Decimal('850'),
            is_active=True,
        )

        self.material2 = Material.objects.create(
            name='Test Steel',
            category=Material.State.STEEL,
            unit=Material.Unit.TONNE,
            current_quantity=Decimal('5'),
            minimum_threshold=Decimal('10'),
            unit_cost=Decimal('45000'),
            is_active=True,
            is_low_stock=True,
        )

        # Create test supplier
        self.supplier = Supplier.objects.create(
            name='Test Supplier Ltd',
            contact_person='John Doe',
            phone='0712345670',
            email='supplier@test.com',
            address='123 Test Street, Nairobi',
            is_active=True,
        )

    # =================================================================
    # MATERIALS LIST TESTS
    # =================================================================

    def test_materials_list_authenticated_admin(self):
        """Test materials list loads for admin."""
        self.client.login(email='admin@caldan.com', password='testpass123')
        response = self.client.get(reverse('inventory:materials_list'))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'inventory/dashboard/admin/inventory/materials.html')
        self.assertIn('materials', response.context)

    def test_materials_list_authenticated_user(self):
        """Test materials list redirects for non-admin."""
        self.client.login(email='user@caldan.com', password='testpass123')
        response = self.client.get(reverse('inventory:materials_list'))

        self.assertEqual(response.status_code, 403)  # Permission denied

    def test_materials_list_unauthenticated(self):
        """Test materials list redirects for unauthenticated."""
        response = self.client.get(reverse('inventory:materials_list'))
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_materials_list_search(self):
        """Test materials list search functionality."""
        self.client.login(email='admin@caldan.com', password='testpass123')
        response = self.client.get(
            reverse('inventory:materials_list'),
            {'search': 'Cement'}
        )

        self.assertEqual(response.status_code, 200)
        materials = response.context['materials']
        self.assertEqual(materials.count(), 1)
        self.assertEqual(materials[0].name, 'Test Cement')

    def test_materials_list_filter_category(self):
        """Test materials list category filter."""
        self.client.login(email='admin@caldan.com', password='testpass123')
        response = self.client.get(
            reverse('inventory:materials_list'),
            {'category': Material.Category.CEMENT}
        )

        self.assertEqual(response.status_code, 200)
        materials = response.context['materials']
        self.assertEqual(materials.count(), 1)
        self.assertEqual(materials[0].category, Material.Category.CEMENT)

    def test_materials_list_filter_low_stock(self):
        """Test materials list low stock filter."""
        self.client.login(email='admin@caldan.com', password='testpass123')
        response = self.client.get(
            reverse('inventory:materials_list'),
            {'low_stock': 'true'}
        )

        self.assertEqual(response.status_code, 200)
        materials = response.context['materials']
        self.assertEqual(materials.count(), 1)
        self.assertTrue(materials[0].is_low_stock)

    # =================================================================
    # MATERIAL DETAIL TESTS
    # =================================================================

    def test_material_detail(self):
        """Test material detail page."""
        self.client.login(email='admin@caldan.com', password='testpass123')
        response = self.client.get(
            reverse('inventory:material_detail', args=[self.material1.id])
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'inventory/dashboard/admin/inventory/material_detail.html')
        self.assertEqual(response.context['material'].id, self.material1.id)

    def test_material_detail_not_found(self):
        """Test material detail with non-existent ID."""
        self.client.login(email='admin@caldan.com', password='testpass123')
        response = self.client.get(
            reverse('inventory:material_detail', args=[99999])
        )

        self.assertEqual(response.status_code, 404)

    # =================================================================
    # MATERIAL CREATE TESTS
    # =================================================================

    def test_material_create_get(self):
        """Test material create form GET."""
        self.client.login(email='admin@caldan.com', password='testpass123')
        response = self.client.get(reverse('inventory:material_create'))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'inventory/dashboard/admin/inventory/material_create.html')
        self.assertIn('form', response.context)

    def test_material_create_post(self):
        """Test material create POST."""
        self.client.login(email='admin@caldan.com', password='testpass123')
        data = {
            'name': 'New Material',
            'category': Material.Category.TOOLS,
            'unit': Material.Unit.PIECE,
            'current_quantity': '100',
            'minimum_threshold': '20',
            'unit_cost': '500',
            'is_active': 'on',
        }
        response = self.client.post(reverse('inventory:material_create'), data)

        self.assertEqual(response.status_code, 302)  # Redirect

        # Check material was created
        material = Material.objects.get(name='New Material')
        self.assertEqual(material.category, Material.Category.TOOLS)
        self.assertEqual(material.current_quantity, Decimal('100'))

    def test_material_create_post_invalid(self):
        """Test material create with invalid data."""
        self.client.login(email='admin@caldan.com', password='testpass123')
        data = {
            'name': '',  # Invalid - required
            'category': Material.Category.TOOLS,
            'unit': Material.Unit.PIECE,
            'current_quantity': '-5',  # Invalid - negative
        }
        response = self.client.post(reverse('inventory:material_create'), data)

        self.assertEqual(response.status_code, 200)  # Stay on page with errors
        self.assertIn('form', response.context)
        self.assertTrue(response.context['form'].errors)

    # =================================================================
    # MATERIAL EDIT TESTS
    # =================================================================

    def test_material_edit_get(self):
        """Test material edit form GET."""
        self.client.login(email='admin@caldan.com', password='testpass123')
        response = self.client.get(
            reverse('inventory:material_edit', args=[self.material1.id])
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'inventory/dashboard/admin/inventory/material_edit.html')
        self.assertEqual(response.context['material'].id, self.material1.id)

    def test_material_edit_post(self):
        """Test material edit POST."""
        self.client.login(email='admin@caldan.com', password='testpass123')
        data = {
            'name': 'Updated Material Name',
            'category': self.material1.category,
            'unit': self.material1.unit,
            'current_quantity': str(self.material1.current_quantity),
            'minimum_threshold': str(self.material1.minimum_threshold),
            'unit_cost': str(self.material1.unit_cost),
            'is_active': 'on',
        }
        response = self.client.post(
            reverse('inventory:material_edit', args=[self.material1.id]),
            data
        )

        self.assertEqual(response.status_code, 302)  # Redirect

        # Check material was updated
        self.material1.refresh_from_db()
        self.assertEqual(self.material1.name, 'Updated Material Name')

    # =================================================================
    # STOCK IN TESTS
    # =================================================================

    def test_stock_in_get(self):
        """Test stock IN form GET."""
        self.client.login(email='admin@caldan.com', password='testpass123')
        response = self.client.get(reverse('inventory:stock_in'))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'inventory/dashboard/admin/inventory/stock_in.html')
        self.assertIn('form', response.context)

    def test_stock_in_post(self):
        """Test stock IN POST."""
        self.client.login(email='admin@caldan.com', password='testpass123')
        data = {
            'material': self.material1.id,
            'quantity': '25',
            'unit_cost': '900',
            'reference': 'TEST-IN-001',
            'notes': 'Test stock IN',
        }
        response = self.client.post(reverse('inventory:stock_in'), data)

        self.assertEqual(response.status_code, 302)  # Redirect

        # Check stock was updated
        self.material1.refresh_from_db()
        self.assertEqual(self.material1.current_quantity, Decimal('75'))

        # Check transaction was created
        transaction = StockTransaction.objects.filter(
            material=self.material1,
            type=StockTransaction.Type.IN
        ).first()
        self.assertIsNotNone(transaction)
        self.assertEqual(transaction.quantity, Decimal('25'))

    # =================================================================
    # STOCK OUT TESTS
    # =================================================================

    def test_stock_out_get(self):
        """Test stock OUT form GET."""
        self.client.login(email='admin@caldan.com', password='testpass123')
        response = self.client.get(reverse('inventory:stock_out'))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'inventory/dashboard/admin/inventory/stock_out.html')
        self.assertIn('form', response.context)

    def test_stock_out_post(self):
        """Test stock OUT POST."""
        self.client.login(email='admin@caldan.com', password='testpass123')
        data = {
            'material': self.material1.id,
            'quantity': '10',
            'reference': 'PROJECT-001',
            'notes': 'Test stock OUT',
        }
        response = self.client.post(reverse('inventory:stock_out'), data)

        self.assertEqual(response.status_code, 302)  # Redirect

        # Check stock was updated
        self.material1.refresh_from_db()
        self.assertEqual(self.material1.current_quantity, Decimal('40'))

        # Check transaction was created
        transaction = StockTransaction.objects.filter(
            material=self.material1,
            type=StockTransaction.Type.OUT
        ).first()
        self.assertIsNotNone(transaction)
        self.assertEqual(transaction.quantity, Decimal('10'))

    def test_stock_out_post_insufficient(self):
        """Test stock OUT with insufficient stock."""
        self.client.login(email='admin@caldan.com', password='testpass123')
        data = {
            'material': self.material1.id,
            'quantity': '1000',  # More than available
            'reference': 'PROJECT-001',
        }
        response = self.client.post(reverse('inventory:stock_out'), data)

        self.assertEqual(response.status_code, 200)  # Stay on page with error
        self.assertIn('form', response.context)

        # Stock should NOT be updated
        self.material1.refresh_from_db()
        self.assertEqual(self.material1.current_quantity, Decimal('50'))

    # =================================================================
    # ALERTS LIST TESTS
    # =================================================================

    def test_alerts_list(self):
        """Test alerts list page."""
        # Create an alert
        AlertService.check_and_create_alerts(self.material2)

        self.client.login(email='admin@caldan.com', password='testpass123')
        response = self.client.get(reverse('inventory:alerts_list'))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'inventory/dashboard/admin/inventory/alerts.html')
        self.assertIn('alerts', response.context)

    def test_alerts_list_filter_status(self):
        """Test alerts list status filter."""
        # Create and resolve an alert
        alert = AlertService.check_and_create_alerts(self.material2)
        AlertService.resolve_alert(
            alert_id=alert.id,
            resolved_by=self.admin,
            request=None,
        )

        self.client.login(email='admin@caldan.com', password='testpass123')
        response = self.client.get(
            reverse('inventory:alerts_list'),
            {'status': StockAlert.Status.RESOLVED}
        )

        self.assertEqual(response.status_code, 200)
        alerts = response.context['alerts']
        self.assertEqual(alerts.count(), 1)
        self.assertEqual(alerts[0].status, StockAlert.Status.RESOLVED)

    # =================================================================
    # SUPPLIERS LIST TESTS
    # =================================================================

    def test_suppliers_list(self):
        """Test suppliers list page."""
        self.client.login(email='admin@caldan.com', password='testpass123')
        response = self.client.get(reverse('inventory:suppliers_list'))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'inventory/dashboard/admin/inventory/suppliers.html')
        self.assertIn('suppliers', response.context)

    def test_suppliers_list_search(self):
        """Test suppliers list search."""
        self.client.login(email='admin@caldan.com', password='testpass123')
        response = self.client.get(
            reverse('inventory:suppliers_list'),
            {'search': 'Test Supplier'}
        )

        self.assertEqual(response.status_code, 200)
        suppliers = response.context['suppliers']
        self.assertEqual(suppliers.count(), 1)
        self.assertEqual(suppliers[0].name, 'Test Supplier Ltd')

    # =================================================================
    # SUPPLIER CREATE TESTS
    # =================================================================

    def test_supplier_create_post(self):
        """Test supplier create POST."""
        self.client.login(email='admin@caldan.com', password='testpass123')
        data = {
            'name': 'New Supplier',
            'contact_person': 'Jane Doe',
            'phone': '0712345678',
            'email': 'jane@newsupplier.com',
            'address': '456 New Street, Nairobi',
            'is_active': 'on',
        }
        response = self.client.post(reverse('inventory:supplier_create'), data)

        self.assertEqual(response.status_code, 302)  # Redirect

        # Check supplier was created
        supplier = Supplier.objects.get(name='New Supplier')
        self.assertEqual(supplier.contact_person, 'Jane Doe')
        self.assertEqual(supplier.email, 'jane@newsupplier.com')

    # =================================================================
    # DELIVERIES LIST TESTS
    # =================================================================

    def test_deliveries_list(self):
        """Test deliveries list page."""
        # Create a delivery
        delivery = Delivery.objects.create(
            supplier=self.supplier,
            expected_date=timezone.now().date(),
            status=Delivery.Status.EXPECTED,
            created_by=self.admin,
        )

        self.client.login(email='admin@caldan.com', password='testpass123')
        response = self.client.get(reverse('inventory:deliveries_list'))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'inventory/dashboard/admin/inventory/deliveries.html')
        self.assertIn('deliveries', response.context)

    def test_deliveries_list_filter_status(self):
        """Test deliveries list status filter."""
        delivery = Delivery.objects.create(
            supplier=self.supplier,
            expected_date=timezone.now().date(),
            status=Delivery.Status.DELIVERED,
            created_by=self.admin,
        )

        self.client.login(email='admin@caldan.com', password='testpass123')
        response = self.client.get(
            reverse('inventory:deliveries_list'),
            {'status': Delivery.Status.DELIVERED}
        )

        self.assertEqual(response.status_code, 200)
        deliveries = response.context['deliveries']
        self.assertEqual(deliveries.count(), 1)
        self.assertEqual(deliveries[0].status, Delivery.Status.DELIVERED)