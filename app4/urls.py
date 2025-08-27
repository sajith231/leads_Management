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
    
    path('key-request/', views.key_request,name="key_request"),
    path('key-request-list/', views.key_request_list,name="key_request_list"),
    path('key-request-edit/<int:request_id>/', views.key_request_edit, name="key_request_edit"),
    path('key-request-delete/<int:request_id>/', views.key_request_delete, name="key_request_delete"),
    path('key-requests/<int:request_id>/update-status/', views.update_key_request_status, name='update_key_request_status'),
    path("api/clients/", views.clients_proxy, name="clients_proxy"),
]