from django.urls import path
from . import views

urlpatterns = [
    path('', views.wallet_list, name='wallet_list'),               #  /wallet/
    path('add/', views.add_wallet, name='add_wallet'),             #  /wallet/add/
    path('edit/<int:wallet_id>/', views.edit_wallet, name='edit_wallet'),
    path('delete/<int:wallet_id>/', views.delete_wallet, name='delete_wallet'),
    path('whatsapp/<int:wallet_id>/', views.wallet_whatsapp_share, name='wallet_whatsapp_share'),
]