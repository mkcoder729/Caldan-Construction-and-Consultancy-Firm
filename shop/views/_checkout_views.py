"""
Checkout Views - Shop App
Caldan Construction - "Building Kenya's Future, One Project at a Time."
"""

import json
import logging
import hmac
import hashlib

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from django.conf import settings

from shop.forms import CheckoutForm
from shop.services import CheckoutService, CartService, OrderService
from shop.models import Order
from shop.views._public_views import get_shop_sidebar_context

logger = logging.getLogger('caldan.shop')


def checkout_view(request):
    """
    Display the checkout page.
    """
    session_key = request.session.session_key

    if not session_key:
        request.session.create()
        session_key = request.session.session_key

    # Get cart data
    cart_data = CartService.get_cart_data(session_key)

    if cart_data['total_items'] == 0:
        messages.warning(request, 'Your cart is empty. Please add items before checking out.')
        return redirect('shop:shop_home')

    # Validate stock
    is_valid, errors = CartService.validate_cart(session_key)
    if not is_valid:
        for error in errors:
            messages.error(
                request,
                f'"{error["product"]}" has only {error["available"]} available. '
                f'You requested {error["requested"]}.'
            )
        return redirect('shop:cart_view')

    if request.method == 'POST':
        form = CheckoutForm(request.POST)

        if form.is_valid():
            try:
                # 1. Create order
                order = CheckoutService.create_order(
                    session_key=session_key,
                    checkout_data=form.cleaned_data
                )
                print(f"✅ Order created: {order.order_number} (ID: {order.id})")

                # 2. Initiate payment
                payment_result = CheckoutService.initiate_payment(order)
                print(f"✅ Payment result: {payment_result}")

                if payment_result['success']:
                    # Store order ID in session for verification
                    request.session['pending_order_id'] = order.id

                    # ✅ ACTUALLY REDIRECT TO PAYSTACK
                    print(f"✅ Redirecting to: {payment_result['authorization_url']}")
                    return redirect(payment_result['authorization_url'])

                else:
                    print(f"❌ Payment initiation failed: {payment_result.get('error')}")
                    messages.error(request, payment_result.get('error', 'Payment initiation failed. Please try again.'))

            except ValueError as e:
                print(f"❌ ValueError: {str(e)}")
                messages.error(request, str(e))
            except Exception as e:
                print(f"❌ Exception: {str(e)}")
                logger.error(f"Checkout failed: {str(e)}")
                messages.error(request, 'An error occurred during checkout. Please try again.')

        else:
            print("❌ Form is invalid")
            print(form.errors)
            messages.error(request, 'Please correct the errors below.')

    else:
        form = CheckoutForm()

    # Calculate totals
    delivery_fee = CheckoutService.DELIVERY_FEE
    subtotal = cart_data['subtotal']
    total = subtotal + delivery_fee

    # ✅ IMPORTANT: Get cart items for the template
    cart_items = list(cart_data.get("items", []))

    context = {
        **get_shop_sidebar_context(request),
        'form': form,
        'cart': {
            'items': cart_items,
            'total_items': cart_data['total_items'],
            'item_count': cart_data['item_count'],
        },
        'subtotal': subtotal,
        'delivery_fee': delivery_fee,
        'total': total,
        'page_title': 'Checkout - Caldan Construction',
    }

    return render(request, 'shop/checkout.html', context)


def place_order(request):
    """
    Place an order from the cart (non-Paystack flow).
    """
    if request.method != 'POST':
        return redirect('shop:checkout_view')

    session_key = request.session.session_key

    if not session_key:
        request.session.create()
        session_key = request.session.session_key

    # Get cart data
    cart_data = CartService.get_cart_data(session_key)

    if cart_data['total_items'] == 0:
        messages.warning(request, 'Your cart is empty.')
        return redirect('shop:shop_home')

    form = CheckoutForm(request.POST)

    if form.is_valid():
        try:
            order = CheckoutService.create_order(
                session_key=session_key,
                checkout_data=form.cleaned_data
            )

            # Send the customer a confirmation email immediately. The
            # admin-side notification + email is handled by the
            # post_save signal on shop.Order (see notifications.signals).
            try:
                OrderService.send_order_confirmation(order)
            except Exception:
                logger.exception("place_order: send_order_confirmation failed")

            messages.success(
                request,
                f'Order #{order.order_number} placed successfully! We\'ll send you a confirmation email.'
            )

            return redirect('shop:order_confirmation', order_number=order.order_number)

        except ValueError as e:
            messages.error(request, str(e))
        except Exception as e:
            logger.error(f"Place order failed: {str(e)}")
            messages.error(request, 'An error occurred. Please try again.')

    else:
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(request, f'{field}: {error}')

    return redirect('shop:checkout_view')


def payment_verify(request):
    """
    Verify payment after Paystack redirect.
    """
    reference = request.GET.get('reference')
    order_id = request.GET.get('order_id')

    print(f"🔍 Payment verify - Reference: {reference}, Order ID: {order_id}")

    if not reference:
        messages.error(request, 'Invalid payment reference.')
        return redirect('shop:shop_home')

    # Get order ID from session if not provided
    if not order_id:
        order_id = request.session.get('pending_order_id')
        print(f"🔍 Got order_id from session: {order_id}")

    try:
        result = CheckoutService.verify_payment(reference, order_id)
        print(f"🔍 Verification result: {result}")

        if result['success']:
            order = result.get('order')
            if order:
                messages.success(
                    request,
                    f'Payment confirmed! Order #{order.order_number} has been placed successfully.'
                )

                # Clear pending order from session
                if 'pending_order_id' in request.session:
                    del request.session['pending_order_id']

                return redirect('shop:order_confirmation', order_number=order.order_number)
            else:
                messages.success(request, 'Payment verified successfully!')
                return redirect('shop:shop_home')
        else:
            messages.error(request, result.get('error', 'Payment verification failed. Please contact support.'))

    except Exception as e:
        print(f"❌ Payment verification error: {str(e)}")
        logger.error(f"Payment verification failed: {str(e)}")
        messages.error(request, 'Payment verification failed. Please contact support.')

    return redirect('shop:shop_home')


@csrf_exempt
@require_http_methods(['POST'])
def payment_webhook(request):
    """
    Paystack webhook handler with signature verification.
    """
    try:
        raw_body = request.body
        signature = request.headers.get('x-paystack-signature', '')
        logger.info(f"Paystack webhook received, signature present: {bool(signature)}")

        from shop.services import PaymentService

        if signature:
            is_valid = PaymentService._verify_webhook_signature(raw_body, signature)
            if not is_valid:
                logger.warning("Invalid Paystack webhook signature - rejecting")
                return JsonResponse({'status': 'invalid_signature'}, status=401)

        result = PaymentService.handle_webhook(raw_body, signature)

        if result:
            return JsonResponse({'status': 'success'}, status=200)
        else:
            return JsonResponse({'status': 'failed'}, status=400)

    except json.JSONDecodeError:
        logger.error("Invalid JSON payload received")
        return JsonResponse({'status': 'invalid'}, status=400)
    except Exception as e:
        logger.error(f"Webhook error: {str(e)}")
        return JsonResponse({'status': 'error'}, status=500)


@csrf_exempt
@require_http_methods(['POST'])
def mpesa_callback(request):
    """
    M-Pesa callback handler (via Paystack).
    """
    try:
        payload = json.loads(request.body)
        logger.info(f"M-Pesa callback received: {payload}")
        return JsonResponse({'status': 'success'}, status=200)

    except json.JSONDecodeError:
        logger.error("Invalid JSON payload received")
        return JsonResponse({'status': 'invalid'}, status=400)
    except Exception as e:
        logger.error(f"M-Pesa callback error: {str(e)}")
        return JsonResponse({'status': 'error'}, status=500)
