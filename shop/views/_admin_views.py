"""
Admin Views - Shop App
Caldan Construction - "Building Kenya's Future, One Project at a Time."
"""

import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.views.decorators.http import require_http_methods
from django.http import HttpResponse, HttpResponseRedirect

from accounts.permissions.decorators import admin_required
from shop.forms import OrderStatusForm, ProductForm
from shop.services import OrderService, ProductService
from shop.models import Order, Product
from reports.services.pdf_service import PDFService
from notifications.services.email_service import EmailService  # ✅ ADDED

logger = logging.getLogger('caldan.shop')


@login_required
@admin_required
def order_list(request):
    """
    List all orders with filters and pagination.
    Sidebar Page: Shop > Orders
    """
    # Get filters
    search = request.GET.get('search')
    status = request.GET.get('status')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    page = int(request.GET.get('page', 1))

    filters = {
        'search': search,
        'status': status,
        'date_from': date_from,
        'date_to': date_to,
    }

    # Get orders
    result = OrderService.get_orders(
        filters=filters,
        page=page,
        per_page=20
    )

    # Get stats
    stats = OrderService.get_order_stats()

    # Status choices for filter
    status_choices = Order.Status.choices

    context = {
        'orders': result['orders'],
        'total': result['total'],
        'page': result['page'],
        'total_pages': result['total_pages'],
        'search': search,
        'current_status': status,
        'date_from': date_from,
        'date_to': date_to,
        'status_choices': status_choices,
        'stats': stats,
        'page_title': 'Orders',
    }

    return render(request, 'shop/dashboard/admin/orders/list.html', context)


@login_required
@admin_required
def order_detail(request, order_id):
    """
    Order detail page for admin.
    Sidebar Page: Shop > Order Detail
    """
    order = OrderService.get_order(order_id)

    # Status form
    status_form = OrderStatusForm(initial={'status': order.status})

    # Status choices for quick update
    status_choices = Order.Status.choices
    status_labels = dict(status_choices)

    context = {
        'order': order,
        'status_form': status_form,
        'status_choices': status_choices,
        'status_labels': status_labels,
        'page_title': f'Order #{order.order_number}',
    }

    return render(request, 'shop/dashboard/admin/orders/detail.html', context)


@login_required
@admin_required
@require_http_methods(['POST'])
def order_update(request, order_id):
    """
    Update order status with tracking information.
    """
    order = OrderService.get_order(order_id)
    form = OrderStatusForm(request.POST)

    if form.is_valid():
        new_status = form.cleaned_data['status']
        admin_notes = form.cleaned_data.get('admin_notes', '')
        tracking_number = form.cleaned_data.get('tracking_number', '')
        estimated_delivery = form.cleaned_data.get('estimated_delivery')

        try:
            # Update order status
            order = OrderService.update_order_status(
                order_id=order.id,
                new_status=new_status,
                user=request.user,
                admin_notes=admin_notes
            )

            # Update tracking info
            if tracking_number:
                order.tracking_number = tracking_number
            if estimated_delivery:
                order.estimated_delivery = estimated_delivery
            if tracking_number or estimated_delivery:
                order.save(update_fields=['tracking_number', 'estimated_delivery'])

            # ✅ NEW: Send tracking email when order is SHIPPED
            if new_status == 'SHIPPED' and tracking_number:
                try:
                    EmailService.send_tracking_update(order)
                    logger.info(f"Tracking email sent for order {order.order_number}")
                except Exception as e:
                    logger.error(f"Failed to send tracking email: {str(e)}")

                # ✅ NEW: Also notify the admin so they know fulfilment has begun.
                try:
                    EmailService.send_admin_tracking_alert(
                        order,
                        tracking_number=tracking_number,
                        estimated_delivery=estimated_delivery,
                    )
                    logger.info(f"Admin tracking alert sent for order {order.order_number}")
                except Exception as e:
                    logger.error(f"Failed to send admin tracking alert: {str(e)}")

            messages.success(
                request,
                f'Order #{order.order_number} status updated to {order.get_status_display()}'
            )

        except ValueError as e:
            messages.error(request, str(e))
        except Exception as e:
            logger.error(f"Order update failed: {str(e)}")
            messages.error(request, 'Failed to update order status.')

    else:
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(request, f'{field}: {error}')

    return redirect('shop:order_detail', order_id=order.id)


@login_required
@admin_required
@require_http_methods(['POST'])
def order_delete(request, order_id):
    """
    Delete an order.
    """
    order = OrderService.get_order(order_id)
    order_number = order.order_number

    try:
        order.delete()
        messages.success(request, f'Order #{order_number} deleted successfully.')

    except Exception as e:
        logger.error(f"Order deletion failed: {str(e)}")
        messages.error(request, 'Failed to delete order.')

    return redirect('shop:order_list')


@login_required
@admin_required
def order_invoice(request, order_id):
    """
    Generate PDF invoice for an order (Admin only).
    """
    order = OrderService.get_order(order_id)

    try:
        pdf_response = PDFService.generate_order_invoice(order)

        if pdf_response:
            return pdf_response
        else:
            messages.error(request, 'Failed to generate invoice.')

    except Exception as e:
        logger.error(f"Invoice generation failed: {str(e)}")
        messages.error(request, 'Failed to generate invoice.')

    return redirect('shop:order_detail', order_id=order.id)


@login_required
@admin_required
def order_reports(request):
    """
    Order reports page.
    Sidebar Page: Shop > Order Reports
    """
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')

    report_data = OrderService.get_order_report_data(date_from, date_to)

    # Get status choices
    status_choices = Order.Status.choices

    context = {
        'report': report_data,
        'status_choices': status_choices,
        'page_title': 'Order Reports',
    }

    return render(request, 'shop/dashboard/admin/orders/reports.html', context)


# ============================================================================
# PRODUCT MANAGEMENT (Admin)
# ============================================================================

@login_required
@admin_required
def product_list(request):
    """
    List products with search, filters and pagination.
    Sidebar Page: Shop > Products
    """
    search = request.GET.get('search', '').strip()
    category = request.GET.get('category', '').strip()
    section = request.GET.get('section', '').strip()
    is_active = request.GET.get('is_active')
    in_stock = request.GET.get('in_stock')

    # Map "1"/"0" filter values to booleans
    def parse_flag(value):
        if value in ('1', 'true', 'yes'):
            return True
        if value in ('0', 'false', 'no'):
            return False
        return None

    filters = {
        'search': search or None,
        'category': category or None,
        'section': section or None,
        'is_active': parse_flag(is_active),
        'in_stock': parse_flag(in_stock),
    }
    page = int(request.GET.get('page', 1))
    per_page = 15

    result = ProductService.get_products(filters=filters, page=page, per_page=per_page)
    stats = ProductService.get_product_stats()

    context = {
        'products': result['products'],
        'total': result['total'],
        'page': result['page'],
        'total_pages': result['total_pages'],
        'search': search,
        'category': category,
        'section': section,
        'is_active': is_active,
        'in_stock': in_stock,
        'category_choices': Product.Category.choices,
        'section_choices': Product.ShopSection.choices,
        'unit_choices': Product.Unit.choices,
        'stats': stats,
        'page_title': 'Products',
    }
    return render(request, 'shop/dashboard/admin/products/list.html', context)


@login_required
@admin_required
def product_detail(request, product_id):
    """
    Admin product detail page.
    Sidebar Page: Shop > Product Detail
    """
    product = ProductService.get_product(product_id)

    # Recent orders containing this product
    from shop.models import OrderItem
    recent_order_items = (
        OrderItem.objects
        .filter(product=product)
        .select_related('order')
        .order_by('-created_at')[:10]
    )

    # Inventory status if linked
    inventory_info = None
    if product.inventory_material:
        material = product.inventory_material
        inventory_info = {
            'name': material.name,
            'sku': getattr(material, 'sku', ''),
            'current_quantity': material.current_quantity,
            'minimum_threshold': getattr(material, 'minimum_threshold', 0),
            'unit': material.get_unit_display(),
            'low_stock': material.current_quantity <= getattr(material, 'minimum_threshold', 0),
        }

    context = {
        'product': product,
        'recent_order_items': recent_order_items,
        'inventory_info': inventory_info,
        'category_choices': Product.Category.choices,
        'unit_choices': Product.Unit.choices,
        'page_title': product.name,
    }
    return render(request, 'shop/dashboard/admin/products/detail.html', context)


@login_required
@admin_required
def product_create(request):
    """
    Create a new product.
    Sidebar Page: Shop > Create Product
    """
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                product = ProductService.create_product(
                    data=form.cleaned_data,
                    user=request.user,
                )
                messages.success(
                    request,
                    f"Product '{product.name}' created successfully."
                )
                return redirect('shop:product_detail', product_id=product.id)
            except Exception as exc:
                logger.exception("Product creation failed")
                messages.error(request, f"Failed to create product: {exc}")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = ProductForm()

    context = {
        'form': form,
        'mode': 'create',
        'page_title': 'Create Product',
        'category_choices': Product.Category.choices,
        'unit_choices': Product.Unit.choices,
    }
    return render(request, 'shop/dashboard/admin/products/form.html', context)


@login_required
@admin_required
def product_edit(request, product_id):
    """
    Edit an existing product.
    Sidebar Page: Shop > Edit Product
    """
    product = ProductService.get_product(product_id)

    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            try:
                # Don't overwrite image when no new file was uploaded.
                files = request.FILES
                data = form.cleaned_data.copy()
                if 'image' in files and files['image']:
                    pass  # form will set it
                elif 'image-clear' in request.POST:
                    data['image'] = None
                else:
                    data.pop('image', None)

                updated = ProductService.update_product(
                    product_id=product.id,
                    data=data,
                    user=request.user,
                )
                messages.success(
                    request,
                    f"Product '{updated.name}' updated successfully."
                )
                return redirect('shop:product_detail', product_id=updated.id)
            except Exception as exc:
                logger.exception("Product update failed")
                messages.error(request, f"Failed to update product: {exc}")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = ProductForm(instance=product)

    context = {
        'form': form,
        'product': product,
        'mode': 'edit',
        'page_title': f'Edit {product.name}',
        'category_choices': Product.Category.choices,
        'unit_choices': Product.Unit.choices,
    }
    return render(request, 'shop/dashboard/admin/products/form.html', context)


@login_required
@admin_required
@require_http_methods(['POST'])
def product_delete(request, product_id):
    """
    Delete a product. Refuses when there are existing order items.
    """
    try:
        product = ProductService.get_product(product_id)
        name = product.name
        ProductService.delete_product(product_id=product.id, user=request.user)
        messages.success(request, f"Product '{name}' deleted successfully.")
    except ValueError as exc:
        messages.error(request, str(exc))
    except Exception as exc:
        logger.exception("Product deletion failed")
        messages.error(request, f"Failed to delete product: {exc}")

    return redirect('shop:product_list')


@login_required
@admin_required
@require_http_methods(['POST'])
def product_toggle_active(request, product_id):
    """Toggle the product's active flag."""
    try:
        product = ProductService.toggle_active(product_id, user=request.user)
        state = 'activated' if product.is_active else 'deactivated'
        messages.success(request, f"Product '{product.name}' {state}.")
    except Exception as exc:
        logger.exception("Product toggle failed")
        messages.error(request, f"Failed to toggle product: {exc}")
    return redirect('shop:product_list')


@login_required
@admin_required
@require_http_methods(['POST'])
def product_toggle_featured(request, product_id):
    """Toggle the product's featured flag."""
    try:
        product = ProductService.toggle_featured(product_id, user=request.user)
        state = 'featured' if product.is_featured else 'unfeatured'
        messages.success(request, f"Product '{product.name}' {state}.")
    except Exception as exc:
        logger.exception("Product feature toggle failed")
        messages.error(request, f"Failed to toggle product: {exc}")

    # Stay on the same page if the user came from the detail page
    next_url = request.POST.get('next') or request.META.get('HTTP_REFERER')
    if next_url and 'product_detail' in next_url:
        return redirect('shop:product_detail', product_id=product_id)
    return redirect('shop:product_list')


@login_required
@admin_required
@require_http_methods(['POST'])
def product_sync_stock(request, product_id):
    """Re-pull stock from linked inventory material."""
    try:
        product = ProductService.sync_stock_from_inventory(
            product_id, user=request.user
        )
        messages.success(
            request,
            f"Stock synced for '{product.name}'. Current: {product.stock_quantity}."
        )
    except ValueError as exc:
        messages.error(request, str(exc))
    except Exception as exc:
        logger.exception("Product stock sync failed")
        messages.error(request, f"Failed to sync stock: {exc}")
    return redirect('shop:product_detail', product_id=product_id)