"""
Payment Service - Paystack and M-Pesa integration.
Caldan Construction - "Building Kenya's Future, One Project at a Time."
"""

import json
import logging
import hmac
import hashlib
import requests
from decimal import Decimal

from django.conf import settings
from django.utils import timezone

logger = logging.getLogger('caldan.payments')


class PaymentService:
    """
    Service for payment processing with Paystack and M-Pesa.
    Supports card payments, M-Pesa STK Push, and bank transfers.
    """

    PAYSTACK_BASE_URL = 'https://api.paystack.co'

    @classmethod
    def _get_headers(cls):
        """Get Paystack API headers."""
        secret_key = getattr(settings, 'PAYSTACK_SECRET_KEY', '')
        print(f"🔍 [PaymentService] Secret key present: {bool(secret_key)}")
        print(f"🔍 [PaymentService] Secret key first 10 chars: {secret_key[:10] if secret_key else 'None'}")

        return {
            'Authorization': f'Bearer {secret_key}',
            'Content-Type': 'application/json',
        }

    @classmethod
    def _verify_webhook_signature(cls, request_body, signature_header):
        """
        Verify Paystack webhook signature using HMAC SHA256.
        """
        if not signature_header:
            logger.warning("Missing Paystack signature header")
            return False

        try:
            secret_key = getattr(settings, 'PAYSTACK_SECRET_KEY', '').encode('utf-8')
            computed = hmac.new(
                secret_key,
                request_body,
                hashlib.sha256
            ).hexdigest()

            return hmac.compare_digest(computed, signature_header)
        except Exception as e:
            logger.error(f"Webhook signature verification failed: {str(e)}")
            return False

    @classmethod
    def initiate_payment(cls, order, email=None, callback_url=None):
        """
        Initialize a Paystack payment transaction.
        """
        print("🔍 [PaymentService] initiate_payment called")
        print(f"🔍 [PaymentService] Order ID: {order.id}, Order number: {order.order_number}")

        if not getattr(settings, 'PAYSTACK_SECRET_KEY', None):
            print("❌ [PaymentService] No Paystack secret key configured!")
            raise ValueError('Paystack secret key is not configured.')

        if not email:
            email = order.client_email
        print(f"🔍 [PaymentService] Email: {email}")

        # Calculate amount in kobo (Paystack uses cents)
        amount = int(order.total * 100)
        print(f"🔍 [PaymentService] Amount: {order.total} KES = {amount} kobo")

        # Prepare metadata
        metadata = {
            'order_id': order.id,
            'order_number': order.order_number,
            'client_email': order.client_email,
        }

        if callback_url is None:
            callback_url = getattr(settings, 'PAYSTACK_CALLBACK_URL', 'http://localhost:8000/shop/payment/verify/')
        print(f"🔍 [PaymentService] Callback URL: {callback_url}")

        # Generate unique reference
        reference = f'ORD-{order.id}-{timezone.now().strftime("%Y%m%d%H%M%S")}'
        print(f"🔍 [PaymentService] Reference: {reference}")

        payload = {
            'email': email,
            'amount': amount,
            'currency': 'KES',
            'reference': reference,
            'callback_url': callback_url,
            'metadata': metadata,
        }

        # Add M-Pesa as channel if enabled
        if getattr(settings, 'MPESA_STK_PUSH_ENABLED', False):
            payload['channels'] = ['card', 'bank', 'ussd', 'mobile_money']
            print("🔍 [PaymentService] M-Pesa STK Push enabled")

        print(f"🔍 [PaymentService] Payload: {json.dumps(payload, indent=2)}")

        try:
            headers = cls._get_headers()
            print(f"🔍 [PaymentService] Headers: {headers}")

            url = f'{cls.PAYSTACK_BASE_URL}/transaction/initialize'
            print(f"🔍 [PaymentService] URL: {url}")

            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=30
            )
            print(f"🔍 [PaymentService] Response status: {response.status_code}")

            response.raise_for_status()
            data = response.json()
            print(f"🔍 [PaymentService] Response data: {json.dumps(data, indent=2)}")

            if data.get('status'):
                print(f"✅ [PaymentService] Paystack initialization successful!")
                print(f"✅ [PaymentService] Authorization URL: {data['data']['authorization_url']}")

                return {
                    'success': True,
                    'authorization_url': data['data']['authorization_url'],
                    'reference': reference,
                    'access_code': data['data']['access_code'],
                }
            else:
                error_msg = data.get('message', 'Payment initialization failed')
                print(f"❌ [PaymentService] Paystack returned error: {error_msg}")
                print(f"❌ [PaymentService] Full response: {data}")
                logger.error(f"Paystack initialization failed: {error_msg}")
                return {
                    'success': False,
                    'error': error_msg,
                }

        except requests.exceptions.Timeout:
            print("❌ [PaymentService] Request timeout - Paystack API took too long")
            logger.error("Paystack API timeout")
            return {
                'success': False,
                'error': 'Payment service timeout. Please try again.',
            }
        except requests.exceptions.ConnectionError:
            print("❌ [PaymentService] Connection error - Could not reach Paystack API")
            logger.error("Paystack API connection error")
            return {
                'success': False,
                'error': 'Payment service unavailable. Please check your internet connection.',
            }
        except requests.exceptions.HTTPError as e:
            print(f"❌ [PaymentService] HTTP error: {str(e)}")
            try:
                error_data = response.json()
                print(f"❌ [PaymentService] Error details: {error_data}")
            except:
                pass
            logger.error(f"Paystack HTTP error: {str(e)}")
            return {
                'success': False,
                'error': 'Payment service error. Please try again.',
            }
        except Exception as e:
            print(f"❌ [PaymentService] Unexpected error: {str(e)}")
            import traceback
            traceback.print_exc()
            logger.error(f"Paystack API error: {str(e)}")
            return {
                'success': False,
                'error': 'Payment service unavailable. Please try again.',
            }

    @classmethod
    def verify_payment(cls, reference):
        """
        Verify a Paystack payment transaction.
        """
        print(f"🔍 [PaymentService] verify_payment called with reference: {reference}")

        if not getattr(settings, 'PAYSTACK_SECRET_KEY', None):
            print("❌ [PaymentService] No Paystack secret key configured!")
            raise ValueError('Paystack secret key is not configured.')

        try:
            headers = cls._get_headers()
            url = f'{cls.PAYSTACK_BASE_URL}/transaction/verify/{reference}'
            print(f"🔍 [PaymentService] Verification URL: {url}")

            response = requests.get(
                url,
                headers=headers,
                timeout=30
            )
            print(f"🔍 [PaymentService] Verification response status: {response.status_code}")

            response.raise_for_status()
            data = response.json()
            print(f"🔍 [PaymentService] Verification response: {json.dumps(data, indent=2)}")

            if data.get('status'):
                transaction_data = data.get('data', {})
                status = transaction_data.get('status')
                print(f"🔍 [PaymentService] Transaction status: {status}")

                return {
                    'success': True,
                    'status': status,
                    'amount': transaction_data.get('amount', 0) / 100,
                    'currency': transaction_data.get('currency', 'KES'),
                    'reference': transaction_data.get('reference'),
                    'metadata': transaction_data.get('metadata', {}),
                    'paid_at': transaction_data.get('paid_at'),
                }
            else:
                error_msg = data.get('message', 'Payment verification failed')
                print(f"❌ [PaymentService] Verification failed: {error_msg}")
                return {
                    'success': False,
                    'error': error_msg,
                }

        except requests.exceptions.Timeout:
            print("❌ [PaymentService] Verification timeout")
            logger.error("Paystack verification timeout")
            return {
                'success': False,
                'error': 'Payment verification timeout. Please try again.',
            }
        except requests.exceptions.ConnectionError:
            print("❌ [PaymentService] Verification connection error")
            logger.error("Paystack verification connection error")
            return {
                'success': False,
                'error': 'Payment verification service unavailable.',
            }
        except Exception as e:
            print(f"❌ [PaymentService] Verification error: {str(e)}")
            import traceback
            traceback.print_exc()
            logger.error(f"Paystack verification error: {str(e)}")
            return {
                'success': False,
                'error': 'Payment verification service unavailable.',
            }

    @classmethod
    def handle_webhook(cls, payload, signature_header=None):
        """
        Handle Paystack webhook for payment events with signature verification.
        """
        print(f"🔍 [PaymentService] handle_webhook called")

        try:
            # Verify webhook signature
            if signature_header:
                print("🔍 [PaymentService] Verifying webhook signature...")
                if not cls._verify_webhook_signature(payload, signature_header):
                    print("❌ [PaymentService] Invalid webhook signature!")
                    logger.warning("Invalid Paystack webhook signature")
                    return False
                print("✅ [PaymentService] Webhook signature verified")

            # If payload is bytes (from request.body), decode it
            if isinstance(payload, bytes):
                payload = json.loads(payload.decode('utf-8'))
            elif isinstance(payload, str):
                payload = json.loads(payload)

            print(f"🔍 [PaymentService] Webhook event: {payload.get('event')}")

            event = payload.get('event')
            data = payload.get('data', {})

            if event == 'charge.success':
                reference = data.get('reference')
                metadata = data.get('metadata', {})
                order_id = metadata.get('order_id')
                print(f"🔍 [PaymentService] Webhook: charge.success - Order ID: {order_id}, Reference: {reference}")

                if order_id:
                    from shop.models import Order
                    try:
                        order = Order.objects.get(id=order_id)
                        print(f"🔍 [PaymentService] Found order: {order.order_number}, Status: {order.status}")

                        if order.status == 'PENDING':
                            order.mark_paid(reference)
                            from shop.services.order_service import OrderService
                            OrderService.send_order_confirmation(order)
                            print(f"✅ [PaymentService] Order {order.order_number} paid via webhook")
                            logger.info(f"Order {order.order_number} paid via webhook")
                            return True
                        else:
                            print(f"⚠️ [PaymentService] Order status is {order.status}, not PENDING")
                    except Order.DoesNotExist:
                        print(f"❌ [PaymentService] Order {order_id} not found for webhook")

            elif event == 'charge.failed':
                print(f"⚠️ [PaymentService] Paystack charge failed: {data.get('reference')}")
                logger.warning(f"Paystack charge failed: {data.get('reference')}")

            return True

        except json.JSONDecodeError as e:
            print(f"❌ [PaymentService] Invalid JSON payload: {str(e)}")
            logger.error(f"Invalid JSON payload in webhook: {str(e)}")
            return False
        except Exception as e:
            print(f"❌ [PaymentService] Webhook error: {str(e)}")
            import traceback
            traceback.print_exc()
            logger.error(f"Paystack webhook error: {str(e)}")
            return False

    @classmethod
    def initiate_mpesa_stk_push(cls, order, phone_number):
        """
        Initiate M-Pesa STK Push via Paystack.
        """
        print(f"🔍 [PaymentService] initiate_mpesa_stk_push called for order {order.order_number}")

        if not getattr(settings, 'MPESA_STK_PUSH_ENABLED', False):
            print("❌ [PaymentService] M-Pesa STK Push is not enabled")
            raise ValueError('M-Pesa STK Push is not enabled.')

        # Paystack handles M-Pesa via their API
        # This is a wrapper for the Paystack transaction initialization
        return cls.initiate_payment(order, email=order.client_email)