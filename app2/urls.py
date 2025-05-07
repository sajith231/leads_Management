# urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('credential-management/', views.credential_management, name='credential_management'),
    path('add-field/', views.add_field, name='add_field'),
    path('edit-field/<int:field_id>/', views.edit_field, name='edit_field'),
    path('delete-field/<int:field_id>/', views.delete_field, name='delete_field'),
    path('add-credential/', views.add_credential, name='add_credential'),
    path('delete-credential/<int:id>/', views.delete_credential, name='delete_credential'),
    path('edit-credential/<int:id>/', views.edit_credential, name='edit_credential'),
    path('add-credential-detail/<int:credential_id>/', views.add_credential_detail, name='add_credential_detail'),
    path('credential-detail/<int:id>/', views.credential_detail, name='credential_detail'),
    path('edit-credential-detail/<int:detail_id>/', views.edit_credential_detail, name='edit_credential_detail'),
    path('delete-credential-detail/<int:detail_id>/', views.delete_credential_detail, name='delete_credential_detail'),

    
]
