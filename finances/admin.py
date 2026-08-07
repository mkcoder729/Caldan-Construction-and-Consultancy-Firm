"""
Admin configuration for Finances app.
Caldan Construction - "Building Kenya's Future, One Project at a Time."
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse

from finances.models import Payment, Expense, Budget


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    """Admin configuration for Payment model."""

    list_display = (
        'id',
        'project_link',
        'amount_display',
        'type_display',
        'method_display',
        'status_display',
        'payment_date',
        'paid_to',
    )
    list_filter = ('type', 'method', 'status', 'payment_date')
    search_fields = ('description', 'paid_to', 'reference', 'invoice_number')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-payment_date',)

    fieldsets = (
        ('Payment Details', {
            'fields': ('project', 'amount', 'type', 'method', 'description')
        }),
        ('Recipient', {
            'fields': ('paid_to', 'paid_to_contact')
        }),
        ('Reference', {
            'fields': ('reference', 'invoice_number', 'receipt')
        }),
        ('Status', {
            'fields': ('status', 'payment_date')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def project_link(self, obj):
        """Link to project admin."""
        if obj.project:
            url = reverse('admin:projects_project_change', args=[obj.project.id])
            return format_html('<a href="{}">{}</a>', url, obj.project.name)
        return '-'
    project_link.short_description = 'Project'

    def amount_display(self, obj):
        """Display amount with KES formatting."""
        return format_html('<strong>KES {}</strong>', f"{obj.amount:,.2f}")
    amount_display.short_description = 'Amount'

    def type_display(self, obj):
        """Display type with nice formatting."""
        return obj.get_type_display()
    type_display.short_description = 'Type'

    def method_display(self, obj):
        """Display method with color coding."""
        colors = {
            'CASH': '#27AE60',
            'MPESA': '#0B66C3',
            'BANK': '#D4AF37',
            'CHEQUE': '#8E44AD',
            'PAYSTACK': '#B9342B',
        }
        color = colors.get(obj.method, '#95A5A6')
        return format_html(
            '<span style="background: {}; color: white; padding: 2px 10px; border-radius: 4px; font-size: 0.7rem; font-weight: 600;">{}</span>',
            color,
            obj.get_method_display()
        )
    method_display.short_description = 'Method'

    def status_display(self, obj):
        """Display status with color coding."""
        colors = {
            'PENDING': '#D4AF37',
            'APPROVED': '#0B66C3',
            'COMPLETED': '#27AE60',
            'CANCELLED': '#B9342B',
        }
        color = colors.get(obj.status, '#95A5A6')
        return format_html(
            '<span style="background: {}; color: white; padding: 2px 10px; border-radius: 4px; font-size: 0.7rem; font-weight: 600;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_display.short_description = 'Status'


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    """Admin configuration for Expense model."""

    list_display = (
        'id',
        'project_link',
        'amount_display',
        'category_display',
        'expense_date',
        'vendor_name',
        'receipt_number',
    )
    list_filter = ('category', 'expense_date')
    search_fields = ('description', 'vendor_name', 'receipt_number')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-expense_date',)

    fieldsets = (
        ('Expense Details', {
            'fields': ('project', 'amount', 'category', 'description')
        }),
        ('Vendor', {
            'fields': ('vendor_name', 'vendor_contact')
        }),
        ('Reference', {
            'fields': ('receipt_number', 'receipt')
        }),
        ('Metadata', {
            'fields': ('notes', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def project_link(self, obj):
        """Link to project admin."""
        if obj.project:
            url = reverse('admin:projects_project_change', args=[obj.project.id])
            return format_html('<a href="{}">{}</a>', url, obj.project.name)
        return '-'
    project_link.short_description = 'Project'

    def amount_display(self, obj):
        """Display amount with KES formatting."""
        return format_html('<strong>KES {}</strong>', f"{obj.amount:,.2f}")
    amount_display.short_description = 'Amount'

    def category_display(self, obj):
        """Display category with nice formatting."""
        return obj.get_category_display()
    category_display.short_description = 'Category'


@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    """Admin configuration for Budget model."""

    list_display = (
        'project_link',
        'category_display',
        'allocated_display',
        'spent_display',
        'remaining_display',
        'spent_percentage',
    )
    list_filter = ('category',)
    search_fields = ('project__name', 'description')
    readonly_fields = ('created_at', 'updated_at')

    def project_link(self, obj):
        """Link to project admin."""
        if obj.project:
            url = reverse('admin:projects_project_change', args=[obj.project.id])
            return format_html('<a href="{}">{}</a>', url, obj.project.name)
        return '-'
    project_link.short_description = 'Project'

    def category_display(self, obj):
        """Display category with nice formatting."""
        return obj.get_category_display()
    category_display.short_description = 'Category'

    def allocated_display(self, obj):
        """Display allocated amount."""
        return f"KES {obj.allocated:,.2f}"
    allocated_display.short_description = 'Allocated'

    def spent_display(self, obj):
        """Display spent amount."""
        return f"KES {obj.spent:,.2f}"
    spent_display.short_description = 'Spent'

    def remaining_display(self, obj):
        """Display remaining amount with color coding."""
        remaining = obj.allocated - obj.spent
        color = '#27AE60' if remaining >= 0 else '#B9342B'
        return format_html(
            '<span style="color: {}; font-weight: 600;">KES {:,.2f}</span>',
            color,
            remaining
        )
    remaining_display.short_description = 'Remaining'

    def spent_percentage(self, obj):
        """Display spent percentage with progress bar."""
        if obj.allocated == 0:
            return '0%'
        percentage = (obj.spent / obj.allocated) * 100
        color = '#27AE60' if percentage < 70 else '#D4AF37' if percentage < 90 else '#B9342B'
        return format_html(
            '<div style="width: 100%; background: #E5E7EB; border-radius: 4px; height: 8px; position: relative;">'
            '<div style="width: {}%; background: {}; border-radius: 4px; height: 100%;"></div>'
            '</div>'
            '<span style="font-size: 0.7rem; color: {};">{:.1f}%</span>',
            min(percentage, 100),
            color,
            color,
            percentage
        )
    spent_percentage.short_description = 'Spent %'