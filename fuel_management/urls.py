from django.urls import path
from . import views


urlpatterns = [
    path('vehicle/', views.vehicle, name='vehicle'),
    path('vehicle/list/', views.vehicle_list, name='vehicle_list'),
    path('vehicle/edit/<int:vehicle_id>/', views.vehicle_edit, name='vehicle_edit'),
    path('vehicle/delete/<int:vehicle_id>/', views.vehicle_delete, name='vehicle_delete'),
     



     path('fuel-management/', views.fuel_management, name='fuel_management'),
     path('fuel-enter/', views.fuel_enter, name='fuel_enter'),
     path('fuel-monitoring/', views.fuel_monitoring, name='fuel_monitoring'),
     path('fuel-edit/<int:entry_id>/', views.fuel_edit, name='fuel_edit'),
     path('fuel-delete/<int:entry_id>/', views.fuel_delete, name='fuel_delete'),
]
