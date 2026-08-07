"""
Checkout Service - Order creation and payment processing.
Caldan Construction - "Building Kenya's Future, One Project at a Time."
"""

import logging
from decimal import Decimal

from django.db import transaction
from django.conf import settings
from django.utils import timezone

from shop.models import Order, OrderItem
from shop.services.cart_service import CartService
from shop.services.order_service import OrderService
from shop.services.payment_service import PaymentService
from accounts.services.audit_service import AuditService

logger = logging.getLogger('caldan.shop')


class CheckoutService:
    """
    Service for checkout and order processing.
    Handles order creation, payment, and confirmation.
    """

    DELIVERY_FEE = Decimal('500.00')

    @classmethod
    @transaction.atomic
    def create_order(cls, session_key, checkout_data):
        """
        Create an order from cart data.
        """
        print("🔍 [CheckoutService] Creating order...")

        # Get cart data
        cart_data = CartService.get_cart_data(session_key)
        print(f"🔍 [CheckoutService] Cart data: {cart_data.get('total_items')} items, subtotal: {cart_data.get('subtotal')}")

        if cart_data['total_items'] == 0:
            raise ValueError("Cart is empty")

        # Validate stock
        is_valid, errors = CartService.validate_cart(session_key)
        if not is_valid:
            raise ValueError(f"Stock validation failed: {errors}")

        # Calculate totals
        subtotal = cart_data['subtotal']
        delivery_fee = cls.DELIVERY_FEE
        total = subtotal + delivery_fee
        print(f"🔍 [CheckoutService] Subtotal: {subtotal}, Delivery: {delivery_fee}, Total: {total}")

        # Create order
        order = Order.objects.create(
            client_name=checkout_data['name'],
            client_email=checkout_data['email'],
            client_phone=checkout_data['phone'],
            delivery_address=checkout_data['address'],
            delivery_county=checkout_data['county'],
            delivery_town=checkout_data['town'],
            delivery_notes=checkout_data.get('notes', ''),
            subtotal=subtotal,
            delivery_fee=delivery_fee,
            total=total,
            status=Order.Status.PENDING,
        )
        print(f"✅ [CheckoutService] Order created: {order.order_number} (ID: {order.id})")

        # Create order items
        for cart_item in cart_data['items']:
            OrderItem.objects.create(
                order=order,
                product=cart_item.product,
                quantity=cart_item.quantity,
                unit_price=cart_item.unit_price,
                total_price=cart_item.total_price,
            )
        print(f"✅ [CheckoutService] {cart_data['item_count']} order items created")

        # Clear the cart
        CartService.clear_cart(session_key)
        print("✅ [CheckoutService] Cart cleared")

        # Log audit
        AuditService.log_action(
            user=None,
            action='ORDER_CREATED',
            entity_type='Order',
            entity_id=str(order.id),
            details={
                'order_number': order.order_number,
                'client_name': order.client_name,
                'client_email': order.client_email,
                'total': float(order.total),
                'items_count': cart_data['item_count'],
            }
        )

        logger.info(f"Order created: {order.order_number}")
        return order

    @classmethod
    def initiate_payment(cls, order, email=None):
        """
        Initiate Paystack payment for the order.
        Returns the payment result with authorization_url.
        """
        print(f"🔍 [CheckoutService] Initiating payment for order: {order.order_number}")

        if order.status != Order.Status.PENDING:
            raise ValueError(f"Order is not in pending state. Current status: {order.status}")

        # Use order email if not provided
        if not email:
            email = order.client_email
        print(f"🔍 [CheckoutService] Email: {email}")

        # Build full callback URL
        callback_path = f"/shop/payment/verify/?order_id={order.id}"

        # Get base URL from settings or hardcode for debug
        base_url = getattr(settings, 'BASE_URL', 'http://localhost:8000')
        full_callback = f"{base_url}{callback_path}"
        print(f"🔍 [CheckoutService] Callback URL: {full_callback}")

        # Initiate payment
        print("🔍 [CheckoutService] Calling PaymentService.initiate_payment...")
        result = PaymentService.initiate_payment(
            order=order,
            email=email,
            callback_url=full_callback
        )
        print(f"🔍 [CheckoutService] Payment result: {result}")

        if result['success']:
            # Update order with reference
            order.paystack_reference = result['reference']
            order.save(update_fields=['paystack_reference'])
            print(f"✅ [CheckoutService] Payment initiated. Reference: {result['reference']}")
            logger.info(f"Payment initiated for order {order.order_number}")
        else:
            print(f"❌ [CheckoutService] Payment initiation failed: {result.get('error')}")

        return result

    @classmethod
    def verify_payment(cls, reference, order_id=None):
        """
        Verify a payment and update order status.
        """
        print(f"🔍 [CheckoutService] Verifying payment. Reference: {reference}, Order ID: {order_id}")

        result = PaymentService.verify_payment(reference)
        print(f"🔍 [CheckoutService] PaymentService.verify_payment result: {result}")

        if result.get('success') and result.get('status') == 'success':
            print(f"✅ [CheckoutService] Payment verification successful!")

            # Find the order
            if order_id:
                try:
                    order = Order.objects.get(id=order_id)
                    print(f"🔍 [CheckoutService] Found order: {order.order_number}")

                    if order.paystack_reference == reference:
                        print(f"✅ [CheckoutService] Reference matches! Marking order as paid...")
                        order.mark_paid(reference)

                        # Send confirmation email
                        OrderService.send_order_confirmation(order)

                        return {
                            'success': True,
                            'order': order,
                            'message': 'Payment verified successfully!'
                        }
                    else:
                        print(f"⚠️ [CheckoutService] Reference mismatch. Order: {order.paystack_reference}, Provided: {reference}")
                except Order.DoesNotExist:
                    print(f"❌ [CheckoutService] Order {order_id} not found")
            else:
                print(f"⚠️ [CheckoutService] No order_id provided for verification")
        else:
            print(f"❌ [CheckoutService] Payment verification failed: {result.get('error')}")

        return result