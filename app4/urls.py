from django.urls import path
from . import views 
from .views import clients_proxy 

urlpatterns = [
    # Existing key request URLs
    path('license-type/', views.license_type_view, name='license_type'),
    path('add-license/', views.add_license_view, name='add_license'),
    path('license-preview/<int:license_id>/', views.license_preview, name='license_preview'),
    path('license-download/<int:license_id>/', views.license_download, name='license_download'),
    path('license-edit/<int:license_id>/', views.license_edit, name='license_edit'),
    path('license-delete/<int:license_id>/', views.license_delete, name='license_delete'),
    
    path('key-request/', views.key_request,name="key_request"),
    path('key-request-list/', views.key_request_list,name="key_request_list"),
    path('key-request-edit/<int:request_id>/', views.key_request_edit, name="key_request_edit"),
    path('key-request-delete/<int:request_id>/', views.key_request_delete, name="key_request_delete"),
    path('key-requests/<int:request_id>/update-status/', views.update_key_request_status, name='update_key_request_status'),
    path('key-requests/<int:request_id>/update-requested-status/', views.update_key_request_requested_status, name='update_key_request_requested_status'),  # ADD THIS LINE
    path("api/clients/", views.clients_proxy, name="clients_proxy"),



path("collections/", views.collections_list, name="collections_list"),
path('collections/add/', views.collections_add, name='collections_add'),
path('api/clients/', clients_proxy, name='clients_proxy'),
path('collections/<int:collection_id>/details/', views.collection_details, name='collection_details'),
path('collections/<int:collection_id>/edit/', views.collections_edit, name='collections_edit'),
path('collections/<int:collection_id>/delete/', views.collections_delete, name='collections_delete'),
path('collections/<int:collection_id>/receipt/', views.collection_receipt, name='collection_receipt'),
path('collections/<int:collection_id>/update-status/', views.collection_update_status, name='collection_update_status'),

    path("api/collections/", views.api_collections_list, name="api_collections_list"),
    path("api/collections/add/", views.api_collections_add, name="api_collections_add"),
    path("api/collections/whatsapp-test/", views.send_collection_whatsapp, name="collection_whatsapp_test"),

    ]