from django.urls import path
from . import views

urlpatterns = [
    # Vehicle details pages
    path('details/', views.vehicle_details, name='vehicle_details'),
    path('details/add/', views.details_add, name='details_add'),
    path('details/<int:detail_id>/delete/', views.details_delete, name='details_delete'),
    
    # Challan pages
    path('<int:vehicle_id>/challan/', views.vehicle_challan_activity, name='vehicle_challan_activity'),
    path('<int:vehicle_id>/challan/add/', views.challan_add, name='challan_add'),
    path('challan/<int:challan_id>/update-status/', views.challan_update_status, name='challan_update_status'),
    path('challan/<int:challan_id>/delete/', views.challan_delete, name='challan_delete'),
]