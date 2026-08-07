"""
URL Configuration for Inventory App.

All dashboard URLs are prefixed with 'inventory/'.
Follows the dashboard URL pattern for consistency.
"""

from django.urls import path
from inventory.views import *

app_name = 'inventory'

urlpatterns = [
    # =====================================================================
    # MATERIALS
    # =====================================================================
    path('materials/', materials_list, name='materials_list'),
    path('materials/create/', material_create, name='material_create'),
    path('materials/<int:material_id>/', material_detail, name='material_detail'),
    path('materials/<int:material_id>/edit/', material_edit, name='material_edit'),

    # =====================================================================
    # STOCK TRANSACTIONS
    # =====================================================================
    path('stock-in/', stock_in, name='stock_in'),
    path('stock-out/', stock_out, name='stock_out'),
    path('transactions/', transactions_list, name='transactions_list'),

    # =====================================================================
    # STOCK ALERTS
    # =====================================================================
    path('alerts/', alerts_list, name='alerts_list'),
    path('alerts/<int:alert_id>/resolve/', alert_resolve, name='alert_resolve'),

    # =====================================================================
    # SUPPLIERS
    # =====================================================================
    path('suppliers/', suppliers_list, name='suppliers_list'),
    path('suppliers/create/', supplier_create, name='supplier_create'),
    path('suppliers/<int:supplier_id>/', supplier_detail, name='supplier_detail'),
    path('suppliers/<int:supplier_id>/edit/', supplier_edit, name='supplier_edit'),
    path('suppliers/<int:supplier_id>/delete/', supplier_delete, name='supplier_delete'),

    # =====================================================================
    # DELIVERIES
    # =====================================================================
    path('deliveries/', deliveries_list, name='deliveries_list'),
    path('deliveries/create/', delivery_create, name='delivery_create'),
    path('deliveries/<int:delivery_id>/', delivery_detail, name='delivery_detail'),
    path('deliveries/<int:delivery_id>/edit/', delivery_edit, name='delivery_edit'),
    path('deliveries/<int:delivery_id>/receive/', delivery_receive, name='delivery_receive'),
]