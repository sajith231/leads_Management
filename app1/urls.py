


from django.urls import path
from . import views
from .views import edit_lead
from .views import delete_lead 
from .views import load_areas

urlpatterns = [
    # Authentication
    path('', views.login, name='login'),
    path('logout/', views.logout, name='logout'),
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),

    # Branch management
    path('add-branch/', views.add_branch, name='add_branch'),
    path('all-branches/', views.all_branches, name='all_branches'),
    path('delete-branch/<int:branch_id>/', views.delete_branch, name='delete_branch'),

    # Requirement management
    path('add-requirement/', views.add_requirement, name='add_requirement'),
    path('all-requirements/', views.all_requirements, name='all_requirements'),
    path('delete-requirement/<int:requirement_id>/', views.delete_requirement, name='delete_requirement'),

    # User management
    path('add-user/', views.add_user, name='add_user'),
    path('users-table/', views.users_table, name='users_table'),
    path('delete-user/<int:user_id>/', views.delete_user, name='delete_user'),
    path('edit-user/<int:user_id>/', views.edit_user, name='edit_user'),
    path('user-dashboard/', views.user_dashboard, name='user_dashboard'), 
    path('edit_branch/<int:branch_id>/', views.edit_branch, name='edit_branch'),
    path('edit-requirement/<int:requirement_id>/', views.edit_requirement, name='edit_requirement'),



    path('add-lead/', views.add_lead, name='add_lead'),
    path('edit_lead/<int:lead_id>/', edit_lead, name='edit_lead'),
    path('all-leads/', views.all_leads, name='all_leads'),
    path('delete_lead/<int:lead_id>/', delete_lead, name='delete_lead'),
    path('toggle-planet-entry/', views.toggle_planet_entry, name='toggle_planet_entry'),
    path('toggle_status/', views.toggle_status, name='toggle_status'),


    path('districts/add/', views.add_district, name='add_district'),
    path('districts/', views.all_districts, name='all_districts'),
    path('districts/delete/<int:district_id>/', views.delete_district, name='delete_district'),
    path('districts/edit/<int:district_id>/', views.edit_district, name='edit_district'),

    path('area/add/', views.add_area, name='add_area'),
    path('area/all/', views.all_areas, name='all_areas'),
    path('area/delete/<int:area_id>/', views.delete_area, name='delete_area'),
    path('area/edit/<int:area_id>/', views.edit_area, name='edit_area'),

    path('locations/', views.all_locations, name='all_locations'),
    path('locations/add/', views.add_location, name='add_location'),
    path('locations/<int:location_id>/edit/', views.edit_location, name='edit_location'),
    path('locations/<int:location_id>/delete/', views.delete_location, name='delete_location'),
    path('ajax/load-areas/', load_areas, name='load_areas'),
    path('load-locations/', views.load_locations, name='load_locations'),
    path('get-location-details/', views.get_location_details, name='get_location_details'),
    path('get-location-details/', views.get_location_details, name='get_location_details'),



    path('add_hardware/', views.add_hardware, name='add_hardware'),
    path('all_hardwares/', views.all_hardwares, name='all_hardwares'),
    path('edit_hardware/<int:hardware_id>/', views.edit_hardware, name='edit_hardware'),
    path('delete_hardware/<int:hardware_id>/', views.delete_hardware, name='delete_hardware'),


    

    

    

]
