from django.urls import path
from . import views

urlpatterns = [
    path('software_update', views.software_update, name='software_update'),
    path('software-add/', views.software_add, name='software_add'),
    path('software/edit/<int:pk>/', views.software_edit, name='software_edit'),
    path('software/delete/<int:pk>/', views.software_delete, name='software_delete'),
    path('software/details/<int:pk>/', views.software_details, name='software_details'),
    path('software/update-status/<int:pk>/', views.software_update_status, name='software_update_status'),
    path('api/rrc-clients/', views.get_rrc_clients, name='get_rrc_clients'),
]