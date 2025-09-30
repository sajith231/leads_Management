from django.urls import path
from . import views


urlpatterns = [
     path('vechicle/', views.vehicle, name='vehicle'),
     path('vechicle_list/', views.vehicle_list, name='vehicle_list'),
     



     path('fuel-management/', views.fuel_management, name='fuel_management'),
     path('fuel-enter/', views.fuel_enter, name='fuel_enter'),
]
