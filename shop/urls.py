"""
URL Configuration for Shop app.
Caldan Construction - "Building Kenya's Future, One Project at a Time."
"""

from django.urls import path

from shop.views import (
    _public_views as public_views,
    _cart_views as cart_views,
    _checkout_views as checkout_views,
    _order_views as order_views,
    _admin_views as admin_views,
)

app_name = 'shop'

urlpatterns = [
    # =====================================================================
    # PUBLIC PRODUCT VIEWS
    # =====================================================================
    path('', public_views.shop_home, name='index'),
    path('', public_views.shop_home, name='shop_home'),
    # Storefront switcher routes — declared BEFORE the catch-all category
    # route so /shop/section/construction/ doesn't get matched as a
    # category name.
    path('section/<str:section>/', public_views.section_products, name='section_products'),
    path('product/<slug:slug>/', public_views.product_detail, name='product_detail'),
    path('category/<str:category>/', public_views.category_products, name='category_products'),
    path('search/', public_views.search_products, name='search_products'),

    # =====================================================================
    # CART VIEWS
    # =====================================================================
    path('cart/', cart_views.cart_view, name='cart_view'),
    path('cart/add/', cart_views.cart_add, name='cart_add'),
    path('cart/update/<int:item_id>/', cart_views.cart_update, name='cart_update'),
    path('cart/remove/<int:item_id>/', cart_views.cart_remove, name='cart_remove'),
    path('cart/clear/', cart_views.cart_clear, name='cart_clear'),
    path('cart/count/', cart_views.cart_count, name='cart_count'),

    # =====================================================================
    # CHECKOUT VIEWS
    # =====================================================================
    path('checkout/', checkout_views.checkout_view, name='checkout_view'),
    path('checkout/place-order/', checkout_views.place_order, name='place_order'),

    # =====================================================================
    # PAYMENT VIEWS (Paystack)
    # =====================================================================
    path('payment/verify/', checkout_views.payment_verify, name='payment_verify'),
    path('payment/webhook/', checkout_views.payment_webhook, name='payment_webhook'),
    path('payment/mpesa-callback/', checkout_views.mpesa_callback, name='mpesa_callback'),

    # =====================================================================
    # ORDER VIEWS (Public)
    # =====================================================================
    path('order/confirmation/<str:order_number>/', order_views.order_confirmation, name='order_confirmation'),
    path('order/track/', order_views.order_tracking, name='order_tracking'),
    path('order/track/<str:order_number>/', order_views.order_tracking, name='order_tracking_with_number'),
    path('order/history/', order_views.order_history, name='order_history'),
    path('order/<str:order_number>/', order_views.order_detail, name='public_order_detail'),

    # =====================================================================
    # ✅ PUBLIC PDF DOWNLOAD (NO LOGIN REQUIRED)
    # =====================================================================
    path('order/<str:order_number>/receipt/', public_views.download_receipt, name='public_order_receipt'),

    # =====================================================================
    # ADMIN ORDER MANAGEMENT (Requires Login)
    # =====================================================================
    path('admin/orders/', admin_views.order_list, name='order_list'),
    path('admin/orders/<int:order_id>/', admin_views.order_detail, name='order_detail'),
    path('admin/orders/<int:order_id>/update/', admin_views.order_update, name='order_update'),
    path('admin/orders/<int:order_id>/delete/', admin_views.order_delete, name='order_delete'),
    path('admin/orders/<int:order_id>/invoice/', admin_views.order_invoice, name='order_invoice'),
    path('admin/reports/', admin_views.order_reports, name='order_reports'),

    # =====================================================================
    # ADMIN PRODUCT MANAGEMENT (Requires Login)
    # =====================================================================
    path('admin/products/', admin_views.product_list, name='product_list'),
    path('admin/products/create/', admin_views.product_create, name='product_create'),
    path('admin/products/<int:product_id>/', admin_views.product_detail, name='product_detail'),
    path('admin/products/<int:product_id>/edit/', admin_views.product_edit, name='product_edit'),
    path('admin/products/<int:product_id>/delete/', admin_views.product_delete, name='product_delete'),
    path('admin/products/<int:product_id>/toggle-active/', admin_views.product_toggle_active, name='product_toggle_active'),
    path('admin/products/<int:product_id>/toggle-featured/', admin_views.product_toggle_featured, name='product_toggle_featured'),
    path('admin/products/<int:product_id>/sync-stock/', admin_views.product_sync_stock, name='product_sync_stock'),
]

