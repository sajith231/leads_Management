from django.urls import path
from . import views

urlpatterns = [
    path('', views.campaigning_list, name="campaigning_list"),
    path('add/', views.campaigning_add, name="campaigning_add"),
    path('edit/<int:pk>/', views.campaigning_edit, name="campaigning_edit"),
    path('delete/<int:pk>/', views.campaigning_delete, name="campaigning_delete"),
]
