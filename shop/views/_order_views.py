"""
Order Views - Shop App
Caldan Construction - "Building Kenya's Future, One Project at a Time."
"""

import logging
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.utils import timezone
from django.conf import settings

from shop.models import Order
from shop.forms.tracking_form import OrderTrackingForm
from shop.views._public_views import get_shop_sidebar_context
from notifications.services.email_service import EmailService

logger = logging.getLogger('caldan.shop')


def _tracking_context(request, **overrides):
    """
    Build the base context for order_tracking so the sidebar + nav
    are consistent with every other shop public page.
    """
    ctx = {
        **get_shop_sidebar_context(request),
        'form': OrderTrackingForm(),
        'show_verification': False,
        'verified': False,
        'found': None,
        'order': None,
        'order_number': None,
        'email': None,
        'tracking_steps': [],
        'page_title': 'Track Your Order - Caldan Construction',
    }
    ctx.update(overrides)
    return ctx


def order_confirmation(request, order_number):
    """
    Order confirmation page after successful order placement.
    """
    order = get_object_or_404(Order, order_number=order_number)

    context = {
        **get_shop_sidebar_context(request),
        'order': order,
        'page_title': f'Order Confirmation - {order_number}',
        'meta_description': f'Order {order_number} confirmed.',
    }

    return render(request, 'shop/order_confirmation.html', context)


def order_tracking(request, order_number=None):
    """
    Order tracking — three states:

      1. GET (no params) → show the "Find Your Order" form.
      2. GET (?order_number=…&email=…) → order exists, send code, show
         the verification card with the order_number + email pre-filled
         in a read-only summary so the user can just type the code and
         press Proceed.
      3. POST (verification_code=…) → verify the code; on success show
         the tracking result, on failure re-render the verify step
         with the code attempt state preserved.

    `order_number` may be passed via URL path (the
    /order/track/<order_number>/ shortcut) or via ?order_number=… query.
    """
    order = None
    found = False
    verified = False
    tracking_steps = []
    form = OrderTrackingForm()
    code_verified = False
    show_verification = False
    email = None

    # Read the in-flight state from either URL kwarg, GET or POST.
    # The /order/track/<order_number>/ URL passes it as a kwarg.
    order_number = order_number or request.GET.get('order_number') or request.POST.get('order_number')
    email = request.GET.get('email') or request.POST.get('email')
    verification_code = request.POST.get('verification_code')

    def _initial_form():
        """Return a form prefilled with whatever the user typed."""
        return OrderTrackingForm(initial={
            'order_number': order_number or '',
            'email': email or '',
        })

    # ============================================================
    # STEP 3: Verify the code (POST)
    # ============================================================
    if verification_code and order_number and email:
        try:
            order = Order.objects.get(order_number=order_number)
            if order.verify_email(email):
                success, message = order.verify_tracking_code(verification_code)
                if success:
                    code_verified = True
                    found = True
                    verified = True
                    tracking_steps = order.get_tracking_steps()

                    # ✅ Store verified email in session for PDF download
                    request.session['verified_order_email'] = email

                    messages.success(request, '✅ Order verified successfully!')
                    logger.info(f"Order {order_number} verified via tracking code for email {email}")
                else:
                    # Re-render the verify step with the bad code attempt
                    show_verification = True
                    found = True
                    messages.error(request, message)
                    return render(request, 'shop/order_tracking.html', _tracking_context(
                        request,
                        order=order,
                        order_number=order_number,
                        email=email,
                        found=True,
                        verified=False,
                        show_verification=True,
                        form=_initial_form(),
                        page_title='Verify Your Order - Caldan Construction',
                    ))
            else:
                messages.error(request, 'Email does not match this order.')
        except Order.DoesNotExist:
            messages.error(request, 'Order not found. Please check your order number.')
            form = _initial_form()

    # ============================================================
    # STEP 2: GET with order_number + email → send code, show verify card
    # ============================================================
    if not code_verified and request.method == 'GET' and order_number and email:
        form = OrderTrackingForm({'order_number': order_number, 'email': email})
        if form.is_valid():
            order = form.cleaned_data['order']
            found = True
            show_verification = True

            # Generate verification code
            code = order.generate_tracking_code()
            logger.info(f"Tracking code generated for {order_number}: {code}")

            # ✅ Send the email (or print to console if SEND_REAL_EMAILS=False)
            email_sent = EmailService.send_tracking_code(order, code)

            if email_sent:
                messages.info(
                    request,
                    f'📧 A verification code has been sent to {email}. '
                    f'Please check your inbox (and spam folder).'
                )
                logger.info(f"Tracking code sent to {email} for order {order_number}")
            else:
                messages.warning(
                    request,
                    '⚠️ Failed to send verification code. Please try again or contact support.'
                )
                logger.error(f"Failed to send tracking code to {email} for order {order_number}")
        else:
            # Invalid form: order not found OR email mismatch.
            # Re-render the initial form with the typed values so the user
            # does not have to retype.
            for error in form.non_field_errors():
                messages.error(request, error)
            return render(request, 'shop/order_tracking.html', _tracking_context(
                request,
                form=_initial_form(),
                page_title='Track Your Order - Caldan Construction',
            ))

    # ============================================================
    # STEP 3 (render): Code verified, show full tracking result
    # ============================================================
    if code_verified and order:
        return render(request, 'shop/order_tracking.html', _tracking_context(
            request,
            order=order,
            found=True,
            verified=True,
            order_number=order_number,
            email=email,
            tracking_steps=tracking_steps,
            form=_initial_form(),
            show_verification=False,
            page_title='Track Your Order - Caldan Construction',
        ))

    # ============================================================
    # STEP 1 (render): GET with no params → show the form
    # STEP 2 (render): GET with order_number+email → show verify step
    # ============================================================
    if show_verification:
        # Send-code path: keep the order_number/email visible in the prefill
        return render(request, 'shop/order_tracking.html', _tracking_context(
            request,
            order=order,
            found=True,
            order_number=order_number,
            email=email,
            form=_initial_form(),
            show_verification=True,
        ))

    return render(request, 'shop/order_tracking.html', _tracking_context(
        request,
        form=form if form.is_bound else OrderTrackingForm(initial={
            'order_number': order_number or '',
            'email': email or '',
        }),
        show_verification=False,
    ))


def order_history(request):
    """
    Order history page - view all orders by email.
    """
    orders = []
    email = request.GET.get('email')

    if email:
        orders = Order.objects.filter(client_email=email).order_by('-created_at')
        if not orders:
            messages.info(request, 'No orders found for this email address.')

    context = {
        **get_shop_sidebar_context(request),
        'orders': orders,
        'email': email,
        'page_title': 'Order History - Caldan Construction',
    }

    return render(request, 'shop/order_history.html', context)


def order_detail(request, order_number):
    """
    View a single order detail (public).
    """
    order = get_object_or_404(Order, order_number=order_number)
    tracking_steps = order.get_tracking_steps()

    context = {
        **get_shop_sidebar_context(request),
        'order': order,
        'tracking_steps': tracking_steps,
        'order_number': order_number,
        'verified': True,
        'found': True,
        'show_verification': False,
        'form': OrderTrackingForm(initial={
            'order_number': order_number,
            'email': order.client_email,
        }),
        'page_title': f'Order #{order_number} - Caldan Construction',
    }

    return render(request, 'shop/order_tracking.html', context)
