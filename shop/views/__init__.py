"""
Views for Shop app.
Caldan Construction - "Building Kenya's Future, One Project at a Time."
"""

from shop.views._public_views import (
    shop_home,
    product_detail,
    category_products,
    search_products,
    download_receipt,  # ✅ ADDED
)

from shop.views._cart_views import (
    cart_view,
    cart_add,
    cart_update,
    cart_remove,
    cart_clear,
    cart_count,
)

from shop.views._checkout_views import (
    checkout_view,
    place_order,
    payment_verify,
    payment_webhook,
    mpesa_callback,
)

from shop.views._order_views import (
    order_confirmation,
    order_tracking,
    order_history,
    order_detail,
)

from shop.views._admin_views import (
    order_list,
    order_detail as admin_order_detail,
    order_update,
    order_delete,
    order_invoice,
    order_reports,
    product_list,
    product_detail,
    product_create,
    product_edit,
    product_delete,
    product_toggle_active,
    product_toggle_featured,
    product_sync_stock,
)

__all__ = [
    # Public Views
    'shop_home',
    'product_detail',
    'category_products',
    'search_products',
    'download_receipt',
    # Cart Views
    'cart_view',
    'cart_add',
    'cart_update',
    'cart_remove',
    'cart_clear',
    'cart_count',

    # Checkout Views
    'checkout_view',
    'place_order',
    'payment_verify',
    'payment_webhook',
    'mpesa_callback',

    # Order Views
    'order_confirmation',
    'order_tracking',
    'order_history',
    'order_detail',

    # Admin Views - Orders
    'order_list',
    'admin_order_detail',
    'order_update',
    'order_delete',
    'order_invoice',
    'order_reports',

    # Admin Views - Products
    'product_list',
    'product_detail',
    'product_create',
    'product_edit',
    'product_delete',
    'product_toggle_active',
    'product_toggle_featured',
    'product_sync_stock',
]