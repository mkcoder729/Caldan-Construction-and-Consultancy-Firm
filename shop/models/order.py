"""
Order model for client orders.
Caldan Construction - "Building Kenya's Future, One Project at a Time."
"""

import secrets
import string
from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta


class Order(models.Model):
    """
    Client order model with complete order lifecycle tracking.
    """

    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending Payment'
        PAID = 'PAID', 'Paid'
        PROCESSING = 'PROCESSING', 'Processing'
        SHIPPED = 'SHIPPED', 'Shipped'
        DELIVERED = 'DELIVERED', 'Delivered'
        COMPLETED = 'COMPLETED', 'Completed'
        CANCELLED = 'CANCELLED', 'Cancelled'

    # Order Identification — RANDOM, UNGUESSABLE
    order_number = models.CharField(
        max_length=20,
        unique=True,
        db_index=True,
        help_text='Unique order number (ORD-2026-A7F3K9)'
    )

    # Client Details
    client_name = models.CharField(max_length=150)
    client_email = models.EmailField(db_index=True)
    client_phone = models.CharField(max_length=15)

    # Delivery Details
    delivery_address = models.TextField()
    delivery_county = models.CharField(max_length=100)
    delivery_town = models.CharField(max_length=100)
    delivery_notes = models.TextField(blank=True, default='')

    # Financial
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    delivery_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2)

    # Status
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True
    )

    # Payment Tracking
    paystack_reference = models.CharField(
        max_length=100,
        blank=True,
        default='',
        help_text='Paystack transaction reference'
    )
    paid_at = models.DateTimeField(null=True, blank=True)

    # Delivery Tracking
    tracking_number = models.CharField(
        max_length=100,
        blank=True,
        default='',
        help_text='Shipping tracking number'
    )
    estimated_delivery = models.DateField(null=True, blank=True)

    # ============================================================
    # TRACKING VERIFICATION CODE (SECURE)
    # ============================================================
    tracking_code = models.CharField(
        max_length=6,
        blank=True,
        default='',
        help_text='6-digit verification code for tracking'
    )
    tracking_code_created_at = models.DateTimeField(null=True, blank=True)
    tracking_code_attempts = models.PositiveSmallIntegerField(default=0)

    # Notes
    notes = models.TextField(blank=True, default='')
    admin_notes = models.TextField(blank=True, default='')

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'shop_orders'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['order_number']),
            models.Index(fields=['status']),
            models.Index(fields=['client_email']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.order_number} - {self.client_name}"

    def save(self, *args, **kwargs):
        """Auto-generate random order number if not set."""
        if not self.order_number:
            self.order_number = self.generate_order_number()
        super().save(*args, **kwargs)

    def generate_order_number(self):
        """
        Generate a random, unguessable order number.
        Format: ORD-2026-A7F3K9
        """
        year = timezone.now().year
        # 6 characters from A-Z and 0-9 (unguessable)
        random_part = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(6))
        return f"ORD-{year}-{random_part}"

    def mark_paid(self, reference):
        """Mark order as paid."""
        self.status = self.Status.PAID
        self.paid_at = timezone.now()
        self.paystack_reference = reference
        self.save(update_fields=['status', 'paid_at', 'paystack_reference'])

        # Deduct stock
        from shop.services.order_service import OrderService
        OrderService.deduct_stock(self)

        return self

    def update_status(self, new_status, admin_notes=None):
        """Update order status with optional admin notes."""
        old_status = self.status
        self.status = new_status

        if admin_notes:
            timestamp = timezone.now().strftime('%Y-%m-%d %H:%M')
            self.admin_notes += f"\n\n[{timestamp}] {admin_notes}"

        self.save(update_fields=['status', 'admin_notes'])

        # Send notification if status changed
        if old_status != new_status:
            from shop.services.order_service import OrderService
            OrderService.send_status_notification(self, old_status)

        return self

    @property
    def status_class(self):
        """Get CSS class for status badge."""
        classes = {
            'PENDING': 'status-pending',
            'PAID': 'status-paid',
            'PROCESSING': 'status-processing',
            'SHIPPED': 'status-shipped',
            'DELIVERED': 'status-delivered',
            'COMPLETED': 'status-completed',
            'CANCELLED': 'status-cancelled',
        }
        return classes.get(self.status, '')

    @property
    def can_cancel(self):
        """Check if order can be cancelled."""
        return self.status in [self.Status.PENDING, self.Status.PAID]

    @property
    def can_update_status(self):
        """Check if status can be updated."""
        return self.status not in [self.Status.COMPLETED, self.Status.CANCELLED]

    def verify_email(self, email):
        """Verify that the provided email matches the order email."""
        return self.client_email.lower() == email.lower()

    # ============================================================
    # TRACKING CODE METHODS
    # ============================================================

    def generate_tracking_code(self):
        """
        Generate a 6-digit verification code for secure tracking.
        Returns the code (for sending via email).
        """
        import secrets
        code = ''.join([str(secrets.randbelow(10)) for _ in range(6)])
        self.tracking_code = code
        self.tracking_code_created_at = timezone.now()
        self.tracking_code_attempts = 0
        self.save(update_fields=['tracking_code', 'tracking_code_created_at', 'tracking_code_attempts'])
        return code

    def verify_tracking_code(self, code):
        """
        Verify the tracking code with expiry and attempts checking.
        Returns (success, message).
        """
        if not self.tracking_code:
            return False, "No verification code generated. Please request a new one."

        # Code expires after 10 minutes
        if timezone.now() > self.tracking_code_created_at + timedelta(minutes=10):
            return False, "Verification code has expired. Please request a new one."

        if self.tracking_code_attempts >= 5:
            return False, "Too many failed attempts. Please request a new code."

        if self.tracking_code == code:
            # Clear the code after successful verification (one-time use)
            self.tracking_code = ''
            self.tracking_code_created_at = None
            self.tracking_code_attempts = 0
            self.save(update_fields=['tracking_code', 'tracking_code_created_at', 'tracking_code_attempts'])
            return True, "Code verified successfully"

        self.tracking_code_attempts += 1
        self.save(update_fields=['tracking_code_attempts'])
        remaining = 5 - self.tracking_code_attempts
        return False, f"Invalid code. {remaining} attempts remaining."

    # ============================================================
    # TRACKING STEPS FOR TIMELINE
    # ============================================================

    def get_tracking_steps(self):
        """Get all tracking steps for timeline."""
        steps = []

        steps.append({
            'label': 'Order Placed',
            'date': self.created_at,
            'icon': 'fa-clock',
            'completed': True,
        })

        if self.paid_at:
            steps.append({
                'label': 'Payment Confirmed',
                'date': self.paid_at,
                'icon': 'fa-check-circle',
                'completed': True,
            })

        if self.status in ['PROCESSING', 'SHIPPED', 'DELIVERED', 'COMPLETED']:
            steps.append({
                'label': 'Processing',
                'date': self.updated_at,
                'icon': 'fa-cogs',
                'completed': True,
            })

        if self.tracking_number and self.status in ['SHIPPED', 'DELIVERED', 'COMPLETED']:
            steps.append({
                'label': 'Shipped',
                'date': self.updated_at,
                'icon': 'fa-truck',
                'completed': True,
            })

        if self.status == 'DELIVERED':
            steps.append({
                'label': 'Delivered',
                'date': self.updated_at,
                'icon': 'fa-home',
                'completed': True,
            })

        if self.status == 'COMPLETED':
            steps.append({
                'label': 'Completed',
                'date': self.updated_at,
                'icon': 'fa-flag-checkered',
                'completed': True,
            })

        if self.status == 'CANCELLED':
            steps.append({
                'label': 'Cancelled',
                'date': self.updated_at,
                'icon': 'fa-times-circle',
                'completed': True,
            })

        if self.status not in ['DELIVERED', 'COMPLETED', 'CANCELLED']:
            status_map = {
                'PENDING': {'label': 'Pending Payment', 'icon': 'fa-clock'},
                'PAID': {'label': 'Paid - Awaiting Processing', 'icon': 'fa-check-circle'},
                'PROCESSING': {'label': 'Processing Your Order', 'icon': 'fa-cogs'},
                'SHIPPED': {'label': 'In Transit', 'icon': 'fa-truck'},
            }
            current = status_map.get(self.status, {'label': self.get_status_display(), 'icon': 'fa-circle'})
            steps.append({
                'label': current['label'],
                'date': self.updated_at,
                'icon': current['icon'],
                'completed': False,
            })

        return steps

    def get_tracking_status(self):
        """Get tracking status for display."""
        status_map = {
            'PENDING': {'label': 'Order Placed', 'icon': 'fa-clock', 'completed': True},
            'PAID': {'label': 'Payment Confirmed', 'icon': 'fa-check-circle', 'completed': True},
            'PROCESSING': {'label': 'Processing', 'icon': 'fa-cogs', 'completed': True},
            'SHIPPED': {'label': 'In Transit', 'icon': 'fa-truck', 'completed': True},
            'DELIVERED': {'label': 'Delivered', 'icon': 'fa-home', 'completed': True},
            'COMPLETED': {'label': 'Completed', 'icon': 'fa-flag-checkered', 'completed': True},
            'CANCELLED': {'label': 'Cancelled', 'icon': 'fa-times-circle', 'completed': False},
        }
        return status_map.get(self.status, {'label': self.get_status_display(), 'icon': 'fa-circle', 'completed': False})