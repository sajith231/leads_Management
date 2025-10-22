from django.urls import path
from . import views

urlpatterns = [
    path('', views.software_table, name='software_table'),
    path('add/', views.add_software, name='add_software'),
    path('edit/<int:id>/', views.edit_software, name='edit_software'),
    path('delete/<int:id>/', views.delete_software, name='delete_software'),
]
