"""
Cart Views - Shop App
Caldan Construction - "Building Kenya's Future, One Project at a Time."
"""

import logging

from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.contrib import messages

from shop.services import CartService, CheckoutService
from shop.views._public_views import get_shop_sidebar_context

logger = logging.getLogger('caldan.shop')


def cart_view(request):
    """
    Display the shopping cart.
    """
    session_key = request.session.session_key

    if not session_key:
        request.session.create()
        session_key = request.session.session_key

    cart_data = CartService.get_cart_data(session_key)

    # The cart template reads these as top-level keys; unpack the dict.
    cart_items = list(cart_data.get("items", []))
    subtotal = cart_data.get("subtotal") or 0
    delivery_fee = CheckoutService.DELIVERY_FEE if cart_items else 0
    total = subtotal + delivery_fee

    context = {
        **get_shop_sidebar_context(request),
        "cart_items": cart_items,
        "subtotal": subtotal,
        "delivery_fee": delivery_fee,
        "total": total,
        "page_title": "Shopping Cart - Caldan Construction",
    }

    return render(request, "shop/cart.html", context)


def cart_add(request):
    """
    Add an item to the cart via AJAX.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=405)

    # Ensure session exists
    if not request.session.session_key:
        request.session.create()

    session_key = request.session.session_key
    product_id = request.POST.get('product_id')
    quantity = int(request.POST.get('quantity', 1))

    if not product_id:
        return JsonResponse({'success': False, 'error': 'Product ID required'}, status=400)

    try:
        cart_item = CartService.add_item(session_key, product_id, quantity)
        cart_count = CartService.get_cart_count(session_key)

        return JsonResponse({
            'success': True,
            'message': 'Item added to cart',
            'cart_count': cart_count,
            'item_id': cart_item.id,
        })

    except ValueError as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
    except Exception as e:
        logger.error(f"Cart add failed: {str(e)}")
        return JsonResponse({'success': False, 'error': 'Failed to add item to cart'}, status=500)


def cart_update(request, item_id):
    """
    Update quantity of a cart item via AJAX.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=405)

    quantity = int(request.POST.get('quantity', 0))

    try:
        cart_item = CartService.update_quantity(item_id, quantity)

        if cart_item:
            # Get updated cart data
            session_key = request.session.session_key
            cart_data = CartService.get_cart_data(session_key)

            return JsonResponse({
                'success': True,
                'message': 'Cart updated',
                'item_total': float(cart_item.total_price),
                'subtotal': float(cart_data['subtotal']),
                'cart_count': cart_data['total_items'],
            })
        else:
            # Item was removed
            session_key = request.session.session_key
            cart_data = CartService.get_cart_data(session_key)

            return JsonResponse({
                'success': True,
                'message': 'Item removed from cart',
                'subtotal': float(cart_data['subtotal']),
                'cart_count': cart_data['total_items'],
                'removed': True,
            })

    except ValueError as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
    except Exception as e:
        logger.error(f"Cart update failed: {str(e)}")
        return JsonResponse({'success': False, 'error': 'Failed to update cart'}, status=500)


def cart_remove(request, item_id):
    """
    Remove an item from the cart via AJAX.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=405)

    try:
        CartService.remove_item(item_id)

        session_key = request.session.session_key
        cart_data = CartService.get_cart_data(session_key)

        return JsonResponse({
            'success': True,
            'message': 'Item removed from cart',
            'subtotal': float(cart_data['subtotal']),
            'cart_count': cart_data['total_items'],
        })

    except Exception as e:
        logger.error(f"Cart remove failed: {str(e)}")
        return JsonResponse({'success': False, 'error': 'Failed to remove item'}, status=500)


def cart_clear(request):
    """
    Clear the entire cart.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=405)

    try:
        session_key = request.session.session_key
        CartService.clear_cart(session_key)

        return JsonResponse({
            'success': True,
            'message': 'Cart cleared',
            'cart_count': 0,
        })

    except Exception as e:
        logger.error(f"Cart clear failed: {str(e)}")
        return JsonResponse({'success': False, 'error': 'Failed to clear cart'}, status=500)


def cart_count(request):
    """
    Get the current cart count via AJAX.
    """
    session_key = request.session.session_key

    if not session_key:
        return JsonResponse({'count': 0})

    try:
        count = CartService.get_cart_count(session_key)
        return JsonResponse({'count': count})

    except Exception as e:
        logger.error(f"Cart count failed: {str(e)}")
        return JsonResponse({'count': 0})