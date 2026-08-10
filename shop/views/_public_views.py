"""
Public Views - Shop App
Caldan Construction - "Building Kenya's Future, One Project at a Time."
"""

import logging

from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.http import HttpRequest, HttpResponse, Http404, JsonResponse
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

    Exposes both top-level `sections` (CONSTRUCTION, GENERAL_STORE) and
    the inner `categories` so templates can show section-aware filters.
    """
    sections = Product.ShopSection.choices

    # Section counts — total active products per top-level storefront.
    section_counts_qs = (
        Product.objects.filter(is_active=True)
        .values('shop_section')
        .annotate(count=Count('id'))
    )
    section_counts = {row['shop_section']: row['count'] for row in section_counts_qs}

    # Categories scoped by section for the per-section filter chip loops.
    categories_by_section = {}
    for cat_value, cat_label in Product.Category.choices:
        cat_section = Product.CATEGORY_TO_SECTION.get(cat_value)
        categories_by_section.setdefault(cat_section, []).append((cat_value, cat_label))

    category_counts = {}
    for cat in Product.Category.choices:
        count = Product.objects.filter(category=cat[0], is_active=True).count()
        if count > 0:
            category_counts[cat[0]] = count

    return {
        'sections': sections,
        'section_counts': section_counts,
        'categories_by_section': categories_by_section,
        'categories': Product.Category.choices,
        'category_counts': category_counts,
        'total_products': Product.objects.filter(is_active=True).count(),
        'cart_count': get_cart_count(request),
    }


def shop_home(request: HttpRequest) -> HttpResponse:
    """
    Shop landing page.

    Behaviour:
    - Without ?section= and no other filters → shows the storefront
      switcher (all products grouped by section).
    - With ?section=CONSTRUCTION or =GENERAL_STORE → shows only that
      storefront, with its own category chips.
    """
    products = Product.objects.filter(is_active=True)

    category_filter = request.GET.get('category')
    if category_filter:
        products = products.filter(category=category_filter)

    section_filter = request.GET.get('section')
    current_section = None
    if section_filter:
        # Accept either 'CONSTRUCTION' or 'construction' (case-insensitive)
        valid = dict(Product.ShopSection.choices)
        normalized = next(
            (code for code in valid.keys() if code.upper() == section_filter.upper()),
            None,
        )
        if normalized:
            current_section = normalized
            products = products.filter(shop_section=normalized)

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
        'current_section': current_section,
        'search_query': search_query,
        'current_sort': sort or 'newest',
        'page_title': 'Shop - Caldan Construction',
        'meta_description': 'Buy construction materials and general-store essentials online from Caldan Construction.',
    }

    return render(request, 'shop/index.html', context)


def section_products(request: HttpRequest, section: str) -> HttpResponse:
    """
    Storefront-scoped product list.

    Validates the section slug against ShopSection.choices; renders the
    same template as shop_home but with current_section set, so the
    hero copy, storefront switcher, and category chips all reflect the
    chosen storefront.
    """
    valid = dict(Product.ShopSection.choices)
    normalized = next(
        (code for code in valid.keys() if code.upper() == section.upper()),
        None,
    )
    if not normalized:
        # Unknown section → 404 rather than silently showing everything
        raise Http404(f"Unknown shop section: {section}")

    products = Product.objects.filter(is_active=True, shop_section=normalized)

    # Optional ?category= sub-filter within the section
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

    section_label = valid[normalized]

    context = {
        **get_shop_sidebar_context(request),
        'products': products_page,
        'current_section': normalized,
        'current_category': category_filter,
        'search_query': search_query,
        'current_sort': sort or 'newest',
        'page_title': f'{section_label} - Caldan Shop',
        'meta_description': f'Shop {section_label.lower()} online from Caldan Construction.',
    }

    return render(request, 'shop/index.html', context)


def product_detail(request: HttpRequest, slug: str) -> HttpResponse:
    """
    Product detail page.
    """
    product = get_object_or_404(Product, slug=slug, is_active=True)

    # Related products must share BOTH category AND shop_section so a
    # cement product doesn't show a notebook as "related" simply because
    # both happen to have category=OTHER.
    related_products = Product.objects.filter(
        category=product.category,
        shop_section=product.shop_section,
        is_active=True,
    ).exclude(id=product.id)[:4]

    context = {
        **get_shop_sidebar_context(request),
        'product': product,
        'related_products': related_products,
        'current_section': product.shop_section,
        'page_title': f'{product.name} - Caldan Construction Shop',
        'meta_description': product.short_description or product.description[:150],
    }

    return render(request, 'shop/product_detail.html', context)


def category_products(request: HttpRequest, category: str) -> HttpResponse:
    """
    Products filtered by category.

    Section is derived from the category via Product.CATEGORY_TO_SECTION
    so the breadcrumb, hero copy, and related-products on the rendered
    template all reflect the correct storefront.
    """
    products = Product.objects.filter(category=category, is_active=True)

    category_display = dict(Product.Category.choices).get(category, category)
    current_section = Product.CATEGORY_TO_SECTION.get(category)

    paginator = Paginator(products, 12)
    page = request.GET.get('page', 1)
    products_page = paginator.get_page(page)

    context = {
        **get_shop_sidebar_context(request),
        'products': products_page,
        'category': category,
        'category_display': category_display,
        'current_section': current_section,
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
            messages.warning(
                request,
                'Your payment is still being confirmed. The receipt will be available once payment is verified — usually a few seconds.'
            )
            return redirect('shop:order_confirmation', order_number=order_number)

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
        return redirect('shop:order_tracking_with_number', order_number=order_number)


