"""
Admin configuration for Shop app.
Caldan Construction - "Building Kenya's Future, One Project at a Time."
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse

from shop.models import Product, Cart, CartItem, Order, OrderItem, Wishlist


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """Admin configuration for Product model."""

    list_display = (
        'name',
        'category_display',
        'price_display',
        'stock_quantity',
        'in_stock',
        'is_active',
        'is_featured',
        'image_preview',
    )
    list_filter = ('category', 'is_active', 'is_featured', 'in_stock')
    search_fields = ('name', 'description', 'sku')
    readonly_fields = ('created_at', 'updated_at')
    prepopulated_fields = {'slug': ('name',)}
    ordering = ('-created_at',)

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'category', 'unit')
        }),
        ('Description', {
            'fields': ('description', 'short_description')
        }),
        ('Pricing & Stock', {
            'fields': ('price', 'compare_price', 'inventory_material', 'stock_quantity')
        }),
        ('Images', {
            'fields': ('image', 'additional_images')
        }),
        ('Status', {
            'fields': ('is_active', 'is_featured', 'in_stock')
        }),
        ('SEO', {
            'fields': ('meta_title', 'meta_description'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def category_display(self, obj):
        return obj.get_category_display()
    category_display.short_description = 'Category'

    def price_display(self, obj):
        return format_html('<strong>KES {}</strong>', f"{obj.price:,.2f}")
    price_display.short_description = 'Price'

    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" width="50" height="50" style="object-fit:cover;border-radius:4px;" />',
                obj.image.url
            )
        return '-'
    image_preview.short_description = 'Image'


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """Admin configuration for Order model."""

    list_display = (
        'order_number',
        'client_name',
        'client_email',
        'total_display',
        'status_display',
        'created_at',
        'actions_display',
    )
    list_filter = ('status', 'created_at')
    search_fields = ('order_number', 'client_name', 'client_email', 'client_phone')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-created_at',)

    fieldsets = (
        ('Order Information', {
            'fields': ('order_number', 'status')
        }),
        ('Client Details', {
            'fields': ('client_name', 'client_email', 'client_phone')
        }),
        ('Delivery', {
            'fields': ('delivery_address', 'delivery_county', 'delivery_town', 'delivery_notes')
        }),
        ('Financial', {
            'fields': ('subtotal', 'delivery_fee', 'total')
        }),
        ('Tracking', {
            'fields': ('tracking_number', 'estimated_delivery'),
            'classes': ('collapse',)
        }),
        ('Notes', {
            'fields': ('notes', 'admin_notes')
        }),
        ('Payment', {
            'fields': ('paystack_reference', 'paid_at'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def total_display(self, obj):
        return format_html('<strong>KES {}</strong>', f"{obj.total:,.2f}")
    total_display.short_description = 'Total'

    def status_display(self, obj):
        colors = {
            'PENDING': '#D4AF37',
            'PAID': '#0B66C3',
            'PROCESSING': '#8E44AD',
            'SHIPPED': '#2980B9',
            'DELIVERED': '#27AE60',
            'COMPLETED': '#1ABC9C',
            'CANCELLED': '#B9342B',
        }
        color = colors.get(obj.status, '#95A5A6')
        return format_html(
            '<span style="background:{};color:white;padding:2px 10px;border-radius:4px;font-size:0.7rem;font-weight:600;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_display.short_description = 'Status'

    def actions_display(self, obj):
        url = reverse('admin:shop_order_change', args=[obj.id])
        return format_html(
            '<a href="{}" class="button">View</a>',
            url
        )
    actions_display.short_description = 'Actions'


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('session_key', 'total_items', 'subtotal_display', 'created_at', 'updated_at')
    search_fields = ('session_key',)
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-created_at',)

    def total_items(self, obj):
        return obj.items.count()
    total_items.short_description = 'Items'

    def subtotal_display(self, obj):
        return format_html('KES {}', f"{obj.subtotal:,.2f}")
    subtotal_display.short_description = 'Subtotal'


@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ('id', 'client', 'product', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('client__name', 'client__email', 'product__name')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)