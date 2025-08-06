from django.urls import path
from . import views

urlpatterns = [
  path('license-type/', views.license_type_view, name='license_type'),
    path('add-license/', views.add_license_view, name='add_license'),
    path('license-download/<int:license_id>/', views.license_download, name='license_download'),
    path('license-edit/<int:license_id>/', views.license_edit, name='license_edit'),
    path('license-delete/<int:license_id>/', views.license_delete, name='license_delete'),
]
