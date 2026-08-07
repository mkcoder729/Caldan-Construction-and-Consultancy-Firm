"""
Tracking flow + public PDF download tests.

Covers:
- Bad email on the tracking form → form re-renders with the values preserved
  and the sidebar (Categories / Need Help) is still present.
- Correct email → a 6-digit tracking code is generated, the email is "sent"
  (DEV backend), and the verify step renders a pre-filled summary card.
- Wrong code → the verify card re-renders with an error message.
- Correct code → the result card is shown with the receipt download link.
- Public PDF receipt download (no login) returns a valid PDF when the
  email is supplied in the query string.
"""

import io
from decimal import Decimal

from django.core import mail
from django.test import TestCase, Client, override_settings
from django.urls import reverse

from shop.models import Product, Order, OrderItem


# Force the console email backend so we can introspect what was "sent"
# without hitting a real SMTP server.
@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    SEND_REAL_EMAILS=False,
)
class TrackingFlowTests(TestCase):
    """End-to-end tests for the public order tracking page."""

    def setUp(self):
        self.client = Client()

        # A product the order can reference. Skip inventory side-effects
        # by leaving inventory_material unset.
        self.product = Product.objects.create(
            name='Portland Cement 50kg',
            slug='portland-cement-50kg',
            category=Product.Category.CEMENT,
            unit=Product.Unit.BAG,
            description='High-quality Portland cement for general construction.',
            price=Decimal('850.00'),
            stock_quantity=Decimal('100'),
            in_stock=True,
            is_active=True,
        )

        # A paid order in good standing.
        self.order = Order.objects.create(
            client_name='Jane Doe',
            client_email='jane@example.com',
            client_phone='0712345678',
            delivery_address='123 Moi Avenue',
            delivery_town='Nairobi',
            delivery_county='Nairobi',
            delivery_notes='Leave at gate',
            subtotal=Decimal('1700.00'),
            delivery_fee=Decimal('300.00'),
            total=Decimal('2000.00'),
            status=Order.Status.PAID,
            tracking_number='TRK-2026-001',
            estimated_delivery='2026-08-01',
        )
        OrderItem.objects.create(
            order=self.order,
            product=self.product,
            quantity=2,
            unit_price=Decimal('850.00'),
        )

        self.tracking_url = reverse('shop:order_tracking')

    # ------------------------------------------------------------------
    # Step 1 — initial form is reachable
    # ------------------------------------------------------------------
    def test_initial_form_renders_with_sidebar(self):
        """Visiting /shop/order/track/ shows the form and the sidebar."""
        response = self.client.get(self.tracking_url)

        self.assertEqual(response.status_code, 200)
        # Sidebar widgets are present
        self.assertContains(response, 'Categories')
        self.assertContains(response, 'All Products')
        self.assertContains(response, 'Need Help')
        self.assertContains(response, 'Contact Us')
        # Form fields are present
        self.assertContains(response, 'id_order_number')
        self.assertContains(response, 'id_email')
        self.assertContains(response, 'Send Verification Code')

    # ------------------------------------------------------------------
    # Step 1 → 2 — wrong email keeps the user on the form, but preserves
    # the typed values so they don't have to retype.
    # ------------------------------------------------------------------
    def test_wrong_email_keeps_form_with_values(self):
        response = self.client.get(
            self.tracking_url,
            {'order_number': self.order.order_number, 'email': 'wrong@example.com'},
        )

        self.assertEqual(response.status_code, 200)
        # Form is bound with the values the user typed
        self.assertContains(response, 'value="{}"'.format(self.order.order_number), html=True)
        self.assertContains(response, 'value="wrong@example.com"', html=True)
        # Sidebar still present
        self.assertContains(response, 'Categories')
        self.assertContains(response, 'Need Help')

    # ------------------------------------------------------------------
    # Step 1 → 2 — correct email generates a code, "sends" it, and shows
    # the verify step with the pre-filled summary card.
    # ------------------------------------------------------------------
    def test_correct_email_generates_code_and_renders_prefill(self):
        response = self.client.get(
            self.tracking_url,
            {'order_number': self.order.order_number, 'email': self.order.client_email},
        )

        self.assertEqual(response.status_code, 200)

        # A tracking code was generated
        self.order.refresh_from_db()
        self.assertTrue(self.order.tracking_code)
        self.assertEqual(len(self.order.tracking_code), 6)

        # Email was sent (via locmem)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(self.order.client_email, mail.outbox[0].to)
        self.assertIn('Verification Code', mail.outbox[0].subject)

        # Verify step is shown with pre-filled summary card
        self.assertContains(response, 'prefill-summary')
        self.assertContains(response, self.order.order_number)
        self.assertContains(response, self.order.client_email)
        self.assertContains(response, 'Proceed')

    # ------------------------------------------------------------------
    # Step 2 → 3 — wrong code returns to the verify step with an error
    # ------------------------------------------------------------------
    def test_wrong_code_re_renders_verify_step(self):
        # First, generate the code
        self.client.get(
            self.tracking_url,
            {'order_number': self.order.order_number, 'email': self.order.client_email},
        )
        self.order.refresh_from_db()
        real_code = self.order.tracking_code

        # Now POST a wrong code
        response = self.client.post(
            self.tracking_url,
            {
                'order_number': self.order.order_number,
                'email': self.order.client_email,
                'verification_code': '000000',
            },
        )

        self.assertEqual(response.status_code, 200)
        # Still on the verify step
        self.assertContains(response, 'prefill-summary')
        self.assertContains(response, 'Proceed')
        # Attempts counter incremented
        self.order.refresh_from_db()
        self.assertEqual(self.order.tracking_code_attempts, 1)
        # The real code is still the same
        self.assertEqual(self.order.tracking_code, real_code)

    # ------------------------------------------------------------------
    # Step 2 → 3 — correct code shows the result card and a receipt link
    # ------------------------------------------------------------------
    def test_correct_code_shows_result_and_receipt_link(self):
        # Generate the code
        self.client.get(
            self.tracking_url,
            {'order_number': self.order.order_number, 'email': self.order.client_email},
        )
        self.order.refresh_from_db()
        code = self.order.tracking_code

        # POST the correct code
        response = self.client.post(
            self.tracking_url,
            {
                'order_number': self.order.order_number,
                'email': self.order.client_email,
                'verification_code': code,
            },
        )

        self.assertEqual(response.status_code, 200)
        # Result card is shown
        self.assertContains(response, 'Order Verified!')
        self.assertContains(response, 'tracking-result-card')
        # Receipt download link is rendered
        self.assertContains(response, 'Download Receipt')
        self.assertContains(response, 'downloadReceiptBtn')
        # Code was cleared on success
        self.order.refresh_from_db()
        self.assertFalse(self.order.tracking_code)

    # ------------------------------------------------------------------
    # Public PDF receipt download — with email in the query string
    # ------------------------------------------------------------------
    def test_public_receipt_download_returns_pdf(self):
        url = reverse('shop:public_order_receipt', kwargs={'order_number': self.order.order_number})
        response = self.client.get(url, {'email': self.order.client_email})

        # 200 + PDF content type (Playwright generated bytes)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        # Force-download header
        self.assertIn('attachment', response['Content-Disposition'])
        self.assertIn('Caldan_Receipt', response['Content-Disposition'])
        # Bytes look like a real PDF
        self.assertGreater(len(response.content), 4)
        self.assertTrue(response.content.startswith(b'%PDF'))

    def test_public_receipt_rejects_wrong_email(self):
        url = reverse('shop:public_order_receipt', kwargs={'order_number': self.order.order_number})
        response = self.client.get(url, {'email': 'attacker@example.com'}, follow=True)

        # Should redirect to the tracking page (no PDF returned)
        self.assertEqual(response.status_code, 200)
        # We ended up on the tracking page
        self.assertIn('Track', response.content.decode('utf-8', errors='ignore'))

    def test_public_receipt_blocks_pending_order(self):
        self.order.status = Order.Status.PENDING
        self.order.save(update_fields=['status'])

        url = reverse('shop:public_order_receipt', kwargs={'order_number': self.order.order_number})
        response = self.client.get(url, {'email': self.order.client_email}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn('Track', response.content.decode('utf-8', errors='ignore'))
