from django.urls import path
from . import views

urlpatterns = [
    # Vehicle URLs
    path('vehicle/', views.vehicle, name='vehicle'),
    path('vehicle_list/', views.vehicle_list, name='vehicle_list'),
    path('vehicle_edit/<int:vehicle_id>/', views.vehicle_edit, name='vehicle_edit'),
    path('vehicle_delete/<int:vehicle_id>/', views.vehicle_delete, name='vehicle_delete'),
    
    # Fuel/Trip URLs
    path('fuel_management/', views.fuel_management, name='fuel_management'),
    path('fuel_entre/', views.fuel_enter, name='fuel_enter'),
    path('fuel/complete/<int:entry_id>/', views.fuel_complete_trip, name='fuel_complete_trip'),
    path('fuel_edit/<int:entry_id>/', views.fuel_edit, name='fuel_edit'),
    path('fuel_delete/<int:entry_id>/', views.fuel_delete, name='fuel_delete'),
    path('fuel_monitoring/', views.fuel_monitoring, name='fuel_monitoring'),
]