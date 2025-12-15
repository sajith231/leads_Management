# urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('details/', views.vehicle_details, name='vehicle_details'),
    path('details/add/', views.details_add, name='details_add'),
    path('details/<int:detail_id>/delete/', views.details_delete, name='details_delete'),

    path('check/add/', views.add_check, name='add_check'),

    # AJAX/info endpoints used by add_check page:
    path('vehicle/<int:vehicle_id>/info/', views.vehicle_info_json, name='vehicle_info_json'),
    path('vehicle/<int:vehicle_id>/challans-json/', views.vehicle_challans_json, name='vehicle_challans_json'),

    # report page
    path('report/', views.report_list, name='report_list'),

    # Challan pages (require vehicle_id)
    path('<int:vehicle_id>/challan/', views.vehicle_challan_activity, name='vehicle_challan_activity'),
    path('<int:vehicle_id>/challan/add/', views.challan_add, name='challan_add'),

    path('challan/<int:challan_id>/update-status/', views.challan_update_status, name='challan_update_status'),
    path('challan/<int:challan_id>/delete/', views.challan_delete, name='challan_delete'),
]

