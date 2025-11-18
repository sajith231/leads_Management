from django.urls import path
from . import views

urlpatterns = [
    path('vehicle/details/', views.vehicle_details, name='vehicle_details'),
]
