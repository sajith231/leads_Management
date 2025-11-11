from django.urls import path
from . import views

app_name = 'purchase_order'

urlpatterns = [
    # ========== SUPPLIER MASTER URLS ==========
    path('suppliers/', views.supplier_list, name='supplier_list'),
    path('suppliers/new/', views.supplier_create, name='supplier_create'),
    path('suppliers/<int:pk>/edit/', views.supplier_update, name='supplier_update'),
    path('suppliers/<int:pk>/delete/', views.supplier_delete, name='supplier_delete'),

    # ========== DEPARTMENT MASTER URLS (NEW) ==========
    path('departments/', views.department_list, name='department_list'),
    path('departments/new/', views.department_create, name='department_create'),
    path('departments/<int:pk>/edit/', views.department_update, name='department_update'),
    path('departments/<int:pk>/delete/', views.department_delete, name='department_delete'),
    
    # ========== ITEM MASTER URLS ==========
    path('items/', views.item_list, name='item_list'),
    path('items/add/', views.item_add, name='item_add'),
    path('items/<int:pk>/edit/', views.item_edit, name='item_edit'),
    path('items/<int:pk>/delete/', views.item_delete, name='item_delete'),
    
    # ========== PURCHASE ORDER URLS ==========
    path('purchase-orders/', views.purchase_order_list, name='po_list'),
    path('purchase-orders/new/', views.purchase_order_create, name='po_create'),
    path('purchase-orders/<int:pk>/', views.purchase_order_view, name='po_detail'),
    path('purchase-orders/<int:pk>/edit/', views.purchase_order_update, name='po_update'),
    path('purchase-orders/<int:pk>/delete/', views.purchase_order_delete, name='po_delete'),
    path('purchase-order/<int:pk>/approve/', views.approve_purchase_order, name='po_approve'),
    path('purchase-orders/<int:pk>/send-whatsapp/', views.send_whatsapp_po, name='send_whatsapp_po'),

    # ========== AJAX API ENDPOINTS ==========
    path('api/items/<int:item_id>/', views.get_item_details, name='get_item_details'),
    path('api/suppliers/<int:supplier_id>/', views.get_supplier_details, name='get_supplier_details'),
    path('api/clients/', views.get_clients_from_api, name='get_clients_api'),


    path('supplier-history/<int:supplier_id>/', views.get_supplier_history, name='get_supplier_history'),
    # path('item-history/<int:item_id>/', views.get_item_history, name='get_item_history'),
    path('item-history/<int:item_id>/', views.item_history, name='item_history'),
    path('download-pdf/<int:pk>/', views.download_po_pdf, name='download_po_pdf'),
    path('purchase-orders/<int:pk>/update-pdf-format/', views.update_po_pdf_format,name='update_po_pdf_format'),
]

