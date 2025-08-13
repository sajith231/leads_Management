from django.urls import path
from . import views

urlpatterns = [
    # Existing key request URLs
    path('license-type/', views.license_type_view, name='license_type'),
    path('add-license/', views.add_license_view, name='add_license'),
    path('license-preview/<int:license_id>/', views.license_preview, name='license_preview'),
    path('license-download/<int:license_id>/', views.license_download, name='license_download'),
    path('license-edit/<int:license_id>/', views.license_edit, name='license_edit'),
    path('license-delete/<int:license_id>/', views.license_delete, name='license_delete'),
    
    # Key request URLs
    path('api/clients/', views.get_clients, name='get_clients'),
    path('key-request/', views.key_request_view, name='key_request'),
    path('key-request-list/', views.key_request_list_view, name='key_request_list'),
]