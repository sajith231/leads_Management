from django.urls import path
from . import views

app_name = 'purchase_order'

urlpatterns = [
    # ================= SUPPLIER MASTER =================
    path('suppliers/', views.supplier_list, name='supplier_list'),
    path('suppliers/new/', views.supplier_create, name='supplier_create'),
    path('suppliers/<int:pk>/edit/', views.supplier_update, name='supplier_update'),
    path('suppliers/<int:pk>/delete/', views.supplier_delete, name='supplier_delete'),

    # ================= DEPARTMENT MASTER =================
    path('departments/', views.department_list, name='department_list'),
    path('departments/new/', views.department_create, name='department_create'),
    path('departments/<int:pk>/edit/', views.department_update, name='department_update'),
    path('departments/<int:pk>/delete/', views.department_delete, name='department_delete'),

    # ================= ITEM MASTER =================
    path('items/', views.item_list, name='item_list'),
    path('items/add/', views.item_add, name='item_add'),
    path('items/<int:pk>/edit/', views.item_edit, name='item_edit'),
    path('items/<int:pk>/delete/', views.item_delete, name='item_delete'),

    # ================= PURCHASE ORDER =================
    path('purchase-orders/', views.purchase_order_list, name='po_list'),
    path('purchase-orders/new/', views.purchase_order_create, name='po_create'),
    path('purchase-orders/<int:pk>/', views.purchase_order_view, name='po_detail'),
    path('purchase-orders/<int:pk>/edit/', views.purchase_order_update, name='po_update'),
    path('purchase-orders/<int:pk>/delete/', views.purchase_order_delete, name='po_delete'),
    path('purchase-order/<int:pk>/approve/', views.approve_purchase_order, name='po_approve'),

    # ================= AJAX APIs =================
    path('api/items/<int:item_id>/', views.get_item_details, name='get_item_details'),
    path('api/suppliers/<int:supplier_id>/', views.get_supplier_details, name='get_supplier_details'),
    path('api/clients/', views.get_clients_from_api, name='get_clients_api'),

    path('supplier-history/<int:supplier_id>/', views.get_supplier_history, name='get_supplier_history'),
    path('item-history/<int:item_id>/', views.get_item_history, name='get_item_history'),

    # ================= PDF & WHATSAPP =================
    # path('po/<int:pk>/download/', views.download_po_pdf, name='download_po_pdf'),
    path('po/<int:pk>/whatsapp/', views.send_whatsapp_po, name='send_whatsapp_po'),

    # Update PDF Format preference
    path('po/<int:pk>/update-format/', views.update_po_pdf_format, name='update_po_pdf_format'),

    # Preview PDF in browser
    path('po/<int:pk>/preview/', views.preview_pdf_template, name='preview_pdf_template'),

    # Bulk ZIP download for multiple POs
    path('po/bulk-download/', views.bulk_download_pdfs, name='bulk_download_pdfs'),
]
