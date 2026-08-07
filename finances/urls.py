"""
URL Configuration for Finances app.
Caldan Construction - "Building Kenya's Future, One Project at a Time."
"""

from django.urls import path

from finances.views import _admin_views as admin_views

app_name = 'finances'

urlpatterns = [
    # =====================================================================
    # PAYMENT URLS
    # =====================================================================
    path('', admin_views.payment_list, name='payment_list'),
    path('payments/', admin_views.payment_list, name='payment_list_alt'),
    path('payments/create/', admin_views.payment_create, name='payment_create'),
    path('payments/<int:payment_id>/', admin_views.payment_detail, name='payment_detail'),
    path('payments/<int:payment_id>/edit/', admin_views.payment_edit, name='payment_edit'),
    path('payments/<int:payment_id>/delete/', admin_views.payment_delete, name='payment_delete'),
    path('payments/<int:payment_id>/approve/', admin_views.payment_approve, name='payment_approve'),
    path('payments/<int:payment_id>/complete/', admin_views.payment_complete, name='payment_complete'),
    path('payments/<int:payment_id>/cancel/', admin_views.payment_cancel, name='payment_cancel'),

    # =====================================================================
    # EXPENSE URLS
    # =====================================================================
    path('expenses/', admin_views.expense_list, name='expense_list'),
    path('expenses/create/', admin_views.expense_create, name='expense_create'),
    path('expenses/<int:expense_id>/edit/', admin_views.expense_edit, name='expense_edit'),
    path('expenses/<int:expense_id>/delete/', admin_views.expense_delete, name='expense_delete'),

    # =====================================================================
    # BUDGET URLS
    # =====================================================================
    path('budgets/', admin_views.budget_list, name='budget_list'),
    path('budgets/create/', admin_views.budget_create, name='budget_create'),
    path('budgets/<int:budget_id>/edit/', admin_views.budget_edit, name='budget_edit'),
    path('budgets/<int:budget_id>/delete/', admin_views.budget_delete, name='budget_delete'),

    # =====================================================================
    # PAYSTACK WEBHOOK (for payment verification)
    # =====================================================================
    path('webhook/paystack/', admin_views.paystack_webhook, name='paystack_webhook'),
]

