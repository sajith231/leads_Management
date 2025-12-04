from django.urls import path
from . import views

urlpatterns = [
    path('claims_list/', views.claims_list, name='claims_list'),
    path('claims_add/', views.claims_add, name='claims_add'),
    path('claims_edit/<int:pk>/', views.claims_edit, name='claims_edit'),
    path('claims_delete/<int:pk>/', views.claims_delete, name='claims_delete'),
    path('api/update-claim-status/<int:pk>/', views.update_claim_status, name='update_claim_status'),
    path('api/get-clients/', views.get_clients, name='get_clients'),
]