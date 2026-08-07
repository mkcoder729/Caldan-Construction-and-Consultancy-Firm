"""
Django Admin Configuration for Inventory App.

Provides admin interface for managing materials, transactions,
alerts, suppliers, and deliveries.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from django.db.models import Sum

from inventory.models import (
    Material,
    StockTransaction,
    StockAlert,
    Supplier,
    Delivery,
    DeliveryItem,
)


@admin.register(Material)
class MaterialAdmin(admin.ModelAdmin):
    """Admin interface for materials."""

    list_display = [
        'name',
        'category',
        'current_quantity_display',
        'unit',
        'is_low_stock_display',
        'is_available_in_shop',
        'supplier_link',
        'created_at',
    ]
    list_filter = [
        'category',
        'unit',
        'is_low_stock',
        'is_active',
        'is_available_in_shop',
        'created_at',
    ]
    search_fields = ['name', 'sku', 'description', 'supplier__name']
    readonly_fields = ['total_cost', 'created_at', 'updated_at']
    fieldsets = (
        ('Identity', {
            'fields': ('name', 'category', 'unit', 'description', 'sku')
        }),
        ('Stock', {
            'fields': ('current_quantity', 'minimum_threshold', 'reorder_quantity')
        }),
        ('Cost', {
            'fields': ('unit_cost', 'total_cost')
        }),
        ('Supplier & Shop', {
            'fields': ('supplier', 'is_available_in_shop', 'shop_price')
        }),
        ('Status', {
            'fields': ('is_active', 'is_low_stock')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'created_by'),
            'classes': ('collapse',)
        }),
    )

    def current_quantity_display(self, obj):
        """Display current quantity with unit."""
        return f"{obj.current_quantity} {obj.get_unit_display()}"
    current_quantity_display.short_description = 'Quantity'

    def is_low_stock_display(self, obj):
        """Display low stock status with color coding."""
        if obj.is_low_stock:
            return format_html('<span style="color: #D69723; font-weight: bold;">⚠️ Low</span>')
        if obj.current_quantity == 0:
            return format_html('<span style="color: #B9342B; font-weight: bold;">🔴 Out</span>')
        return format_html('<span style="color: #27AE60;">✅ OK</span>')
    is_low_stock_display.short_description = 'Stock Status'

    def supplier_link(self, obj):
        """Link to supplier admin."""
        if obj.supplier:
            url = f"/admin/inventory/supplier/{obj.supplier.id}/change/"
            return format_html('<a href="{}">{}</a>', url, obj.supplier.name)
        return '-'
    supplier_link.short_description = 'Supplier'


@admin.register(StockTransaction)
class StockTransactionAdmin(admin.ModelAdmin):
    """Admin interface for stock transactions."""

    list_display = [
        'id',
        'material_link',
        'type_display',
        'quantity_display',
        'unit_cost_display',
        'status_display',
        'performed_by',
        'transaction_date',
    ]
    list_filter = [
        'type',
        'status',
        'transaction_date',
        'performed_by',
    ]
    search_fields = ['material__name', 'reference', 'receipt_number', 'notes']
    readonly_fields = [
        'quantity_before',
        'quantity_after',
        'total_cost',
        'created_at',
        'updated_at',
    ]
    fieldsets = (
        ('Transaction', {
            'fields': ('material', 'type', 'quantity', 'unit_cost', 'total_cost')
        }),
        ('Reference', {
            'fields': ('reference', 'receipt_number', 'notes')
        }),
        ('Receipt', {
            'fields': ('receipt',)
        }),
        ('Status', {
            'fields': ('status', 'performed_by', 'cancelled_by')
        }),
        ('Quantity Tracking', {
            'fields': ('quantity_before', 'quantity_after'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('transaction_date', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def material_link(self, obj):
        """Link to material."""
        url = f"/admin/inventory/material/{obj.material.id}/change/"
        return format_html('<a href="{}">{}</a>', url, obj.material.name)
    material_link.short_description = 'Material'

    def type_display(self, obj):
        """Display transaction type with color."""
        colors = {
            'IN': '#27AE60',
            'OUT': '#B9342B',
            'ADJUSTMENT': '#F39C12',
            'RETURN': '#2980B9',
        }
        color = colors.get(obj.type, '#6B7280')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_type_display()
        )
    type_display.short_description = 'Type'

    def quantity_display(self, obj):
        """Display quantity with unit."""
        return f"{obj.quantity} {obj.material.get_unit_display()}"
    quantity_display.short_description = 'Quantity'

    def unit_cost_display(self, obj):
        """Display unit cost in KES."""
        if obj.unit_cost:
            return f"KES {obj.unit_cost:,.2f}"
        return '-'
    unit_cost_display.short_description = 'Unit Cost'

    def status_display(self, obj):
        """Display status with color."""
        colors = {
            'PENDING': '#F39C12',
            'CONFIRMED': '#27AE60',
            'CANCELLED': '#B9342B',
        }
        color = colors.get(obj.status, '#6B7280')
        return format_html(
            '<span style="color: {};">{}</span>',
            color,
            obj.get_status_display()
        )
    status_display.short_description = 'Status'


@admin.register(StockAlert)
class StockAlertAdmin(admin.ModelAdmin):
    """Admin interface for stock alerts."""

    list_display = [
        'material_link',
        'status_display',
        'current_quantity_at_alert',
        'threshold_quantity',
        'created_at',
        'resolved_at',
    ]
    list_filter = ['status', 'created_at', 'resolved_at']
    search_fields = ['material__name', 'message']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('Alert', {
            'fields': ('material', 'message', 'status')
        }),
        ('Quantities', {
            'fields': ('current_quantity_at_alert', 'threshold_quantity')
        }),
        ('Resolution', {
            'fields': ('resolved_by', 'resolved_at', 'resolution_notes')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def material_link(self, obj):
        """Link to material."""
        url = f"/admin/inventory/material/{obj.material.id}/change/"
        return format_html('<a href="{}">{}</a>', url, obj.material.name)
    material_link.short_description = 'Material'

    def status_display(self, obj):
        """Display status with color."""
        colors = {
            'OPEN': '#B9342B',
            'RESOLVED': '#27AE60',
            'IGNORED': '#6B7280',
        }
        color = colors.get(obj.status, '#6B7280')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_display.short_description = 'Status'


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    """Admin interface for suppliers."""

    list_display = [
        'name',
        'contact_person',
        'phone',
        'email',
        'is_active_display',
        'is_preferred_display',
        'material_count_display',
        'created_at',
    ]
    list_filter = ['is_active', 'is_preferred', 'payment_terms', 'county']
    search_fields = ['name', 'contact_person', 'phone', 'email', 'tax_id']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('Identity', {
            'fields': ('name', 'contact_person')
        }),
        ('Contact', {
            'fields': ('phone', 'alternative_phone', 'email')
        }),
        ('Address', {
            'fields': ('address', 'county', 'town')
        }),
        ('Business', {
            'fields': ('payment_terms', 'tax_id', 'business_registration')
        }),
        ('Status', {
            'fields': ('is_active', 'is_preferred')
        }),
        ('Notes', {
            'fields': ('notes',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'created_by'),
            'classes': ('collapse',)
        }),
    )

    def is_active_display(self, obj):
        """Display active status."""
        if obj.is_active:
            return format_html('<span style="color: #27AE60;">✅ Active</span>')
        return format_html('<span style="color: #B9342B;">❌ Inactive</span>')
    is_active_display.short_description = 'Status'

    def is_preferred_display(self, obj):
        """Display preferred status."""
        if obj.is_preferred:
            return format_html('<span style="color: #D69723;">⭐ Preferred</span>')
        return '-'
    is_preferred_display.short_description = 'Preferred'

    def material_count_display(self, obj):
        """Display count of materials from this supplier."""
        count = obj.materials.filter(is_active=True).count()
        return format_html(
            '<a href="/admin/inventory/material/?supplier__id__exact={}">{}</a>',
            obj.id,
            count
        )
    material_count_display.short_description = 'Materials'


class DeliveryItemInline(admin.TabularInline):
    """Inline admin for delivery items."""

    model = DeliveryItem
    extra = 1
    fields = ['material', 'quantity', 'unit_cost', 'total_cost']
    readonly_fields = ['total_cost']
    autocomplete_fields = ['material']


@admin.register(Delivery)
class DeliveryAdmin(admin.ModelAdmin):
    """Admin interface for deliveries."""

    list_display = [
        'delivery_number',
        'supplier_link',
        'status_display',
        'expected_date',
        'actual_date',
        'total_display',
        'item_count_display',
        'created_at',
    ]
    list_filter = ['status', 'expected_date', 'actual_date', 'created_at']
    search_fields = ['delivery_number', 'supplier__name', 'tracking_number']
    readonly_fields = ['created_at', 'updated_at', 'subtotal', 'total']
    inlines = [DeliveryItemInline]
    fieldsets = (
        ('Delivery', {
            'fields': ('delivery_number', 'supplier', 'status')
        }),
        ('Dates', {
            'fields': ('expected_date', 'actual_date')
        }),
        ('Costs', {
            'fields': ('subtotal', 'delivery_fee', 'total')
        }),
        ('Documentation', {
            'fields': ('receipt', 'tracking_number')
        }),
        ('Notes', {
            'fields': ('notes',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'created_by'),
            'classes': ('collapse',)
        }),
    )

    def supplier_link(self, obj):
        """Link to supplier."""
        url = f"/admin/inventory/supplier/{obj.supplier.id}/change/"
        return format_html('<a href="{}">{}</a>', url, obj.supplier.name)
    supplier_link.short_description = 'Supplier'

    def status_display(self, obj):
        """Display status with color."""
        colors = {
            'EXPECTED': '#F39C12',
            'IN_TRANSIT': '#2980B9',
            'DELIVERED': '#27AE60',
            'CANCELLED': '#B9342B',
        }
        color = colors.get(obj.status, '#6B7280')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_display.short_description = 'Status'

    def total_display(self, obj):
        """Display total in KES."""
        return f"KES {obj.total:,.2f}"
    total_display.short_description = 'Total'

    def item_count_display(self, obj):
        """Display number of items."""
        return obj.items.count()
    item_count_display.short_description = 'Items'