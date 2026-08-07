"""
Public Views - Shop App
Caldan Construction - "Building Kenya's Future, One Project at a Time."
"""

import logging

from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.contrib import messages
from django.conf import settings
from django.urls import reverse

from shop.models import Product, Order
from reports.services.pdf_service import PDFService

logger = logging.getLogger('caldan.shop')


def get_cart_count(request):
    """Helper function to get cart count from session."""
    from shop.models import Cart
    session_key = request.session.session_key
    if not session_key:
        return 0
    try:
        cart = Cart.objects.get(session_key=session_key)
        return cart.items.count()
    except Cart.DoesNotExist:
        return 0


def get_shop_sidebar_context(request):
    """
    Return the standard context that powers the shop sidebar
    (Categories widget + Need Help widget) and the cart badge.

    Every view that renders a template extending shop/base_shop.html
    MUST merge this into its context so the sidebar looks identical
    on /shop/, /cart/, /checkout/, /order/track/, /order/history/,
    /order/<n>/, and /order/<n>/receipt/.
    """
    categories = Product.Category.choices

    category_counts = {}
    for cat in Product.Category.choices:
        count = Product.objects.filter(category=cat[0], is_active=True).count()
        if count > 0:
            category_counts[cat[0]] = count

    return {
        'categories': categories,
        'category_counts': category_counts,
        'total_products': Product.objects.filter(is_active=True).count(),
        'cart_count': get_cart_count(request),
    }


def shop_home(request: HttpRequest) -> HttpResponse:
    """
    Shop homepage with product catalog.
    """
    products = Product.objects.filter(is_active=True)

    category_filter = request.GET.get('category')
    if category_filter:
        products = products.filter(category=category_filter)

    search_query = request.GET.get('search', '').strip()
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(short_description__icontains=search_query)
        )

    sort = request.GET.get('sort', '')
    if sort == 'price_asc':
        products = products.order_by('price')
    elif sort == 'price_desc':
        products = products.order_by('-price')
    elif sort == 'name':
        products = products.order_by('name')
    else:
        products = products.order_by('-created_at')

    paginator = Paginator(products, 12)
    page = request.GET.get('page', 1)
    products_page = paginator.get_page(page)

    context = {
        **get_shop_sidebar_context(request),
        'products': products_page,
        'current_category': category_filter,
        'search_query': search_query,
        'current_sort': sort or 'newest',
        'page_title': 'Shop - Caldan Construction',
        'meta_description': 'Buy quality construction materials online from Caldan Construction.',
    }

    return render(request, 'shop/index.html', context)


def product_detail(request: HttpRequest, slug: str) -> HttpResponse:
    """
    Product detail page.
    """
    product = get_object_or_404(Product, slug=slug, is_active=True)

    related_products = Product.objects.filter(
        category=product.category,
        is_active=True
    ).exclude(id=product.id)[:4]

    context = {
        **get_shop_sidebar_context(request),
        'product': product,
        'related_products': related_products,
        'page_title': f'{product.name} - Caldan Construction Shop',
        'meta_description': product.short_description or product.description[:150],
    }

    return render(request, 'shop/product_detail.html', context)


def category_products(request: HttpRequest, category: str) -> HttpResponse:
    """
    Products filtered by category.
    """
    products = Product.objects.filter(category=category, is_active=True)

    category_display = dict(Product.Category.choices).get(category, category)

    paginator = Paginator(products, 12)
    page = request.GET.get('page', 1)
    products_page = paginator.get_page(page)

    context = {
        **get_shop_sidebar_context(request),
        'products': products_page,
        'category': category,
        'category_display': category_display,
        'current_category': category,
        'page_title': f'{category_display} - Shop - Caldan Construction',
    }

    return render(request, 'shop/index.html', context)


def search_products(request: HttpRequest) -> HttpResponse:
    """
    Search products by name or description.
    """
    query = request.GET.get('q', '').strip()

    if query:
        products = Product.objects.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query) |
            Q(short_description__icontains=query)
        ).filter(is_active=True)
    else:
        products = Product.objects.filter(is_active=True)

    paginator = Paginator(products, 12)
    page = request.GET.get('page', 1)
    products_page = paginator.get_page(page)

    context = {
        **get_shop_sidebar_context(request),
        'products': products_page,
        'search_query': query,
        'page_title': f'Search Results: {query}' if query else 'Shop - Caldan Construction',
    }

    return render(request, 'shop/index.html', context)


# ============================================================
# ✅ PUBLIC PDF DOWNLOAD — WITH DEBUG
# ============================================================

def download_receipt(request, order_number):
    """
    Public endpoint for customers to download their receipt PDF.
    No login required — uses order number to fetch the order.
    URL: /shop/order/<order_number>/receipt/
    """
    print(f"🔍 [DOWNLOAD] Starting PDF download for order: {order_number}")

    try:
        order = get_object_or_404(Order, order_number=order_number)
        print(f"🔍 [DOWNLOAD] Order found: {order.order_number}, Status: {order.status}")

        # ✅ Get email from query params
        email = request.GET.get('email')
        print(f"🔍 [DOWNLOAD] Email from URL: {email}")

        # ✅ If email is provided, verify it matches the order
        if email:
            if not order.verify_email(email):
                print(f"❌ [DOWNLOAD] Email mismatch: {email} vs {order.client_email}")
                messages.error(request, 'Email does not match this order. Please check and try again.')
                return redirect('shop:order_tracking_with_number', order_number=order_number)
            print(f"✅ [DOWNLOAD] Email verified from URL")
        else:
            # ✅ Check session for verified email (from tracking flow)
            verified_email = request.session.get('verified_order_email')
            print(f"🔍 [DOWNLOAD] Email from session: {verified_email}")
            if verified_email and order.verify_email(verified_email):
                print(f"✅ [DOWNLOAD] Email verified from session")
                pass
            else:
                print(f"❌ [DOWNLOAD] No valid email found")
                messages.warning(request, 'Please verify your email to download the receipt.')
                return redirect('shop:order_tracking_with_number', order_number=order_number)

        # Only allow download for paid orders
        if order.status == 'PENDING':
            print(f"⚠️ [DOWNLOAD] Order is PENDING, not paid")
            messages.warning(request, 'This order has not been paid yet. Receipt will be available after payment.')
            return redirect('shop:order_tracking_with_number', order_number=order_number)

        if order.status == 'CANCELLED':
            print(f"⚠️ [DOWNLOAD] Order is CANCELLED")
            messages.warning(request, 'This order has been cancelled. No receipt available.')
            return redirect('shop:order_tracking_with_number', order_number=order_number)

        print(f"✅ [DOWNLOAD] Generating PDF for order: {order.order_number}")

        # Generate the PDF
        response = PDFService.generate_order_invoice(order)

        print(f"✅ [DOWNLOAD] PDF generated, response type: {type(response)}")
        print(f"✅ [DOWNLOAD] Response content length: {len(response.content) if hasattr(response, 'content') else 'unknown'}")

        # Force download headers
        pretty_name = f"Caldan_Receipt_{order.order_number}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{pretty_name}"'
        response['Content-Type'] = 'application/pdf'
        response['Content-Length'] = len(response.content)
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        response['X-Content-Type-Options'] = 'nosniff'

        print(f"✅ [DOWNLOAD] Headers set, returning response")
        return response

    except Exception as e:
        print(f"❌ [DOWNLOAD] ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        logger.error(f"Public PDF download failed for order {order_number}: {str(e)}")
        messages.error(request, 'Unable to generate receipt. Please contact support.')
        return redirect('shop:order_tracking')


