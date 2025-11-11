from django.urls import path
from . import views

urlpatterns = [
    path('wallet/', views.wallet_list, name='wallet_list'),
    path('wallet/add/', views.add_wallet, name='add_wallet'),
    path('wallet/delete/<int:wallet_id>/', views.delete_wallet, name='delete_wallet'),
    path('wallet/edit/<int:wallet_id>/', views.edit_wallet, name='edit_wallet'),
    path('wallet/whatsapp/<int:wallet_id>/', views.wallet_whatsapp_share, name='wallet_whatsapp_share'),
]