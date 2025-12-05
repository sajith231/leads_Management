from django.urls import path
from . import views

urlpatterns = [
    path('user/', views.user_cancel_requests, name='user_cancel_requestes'),
    path('add/', views.add_cancel_request, name='add_cancel_request'),
    path('admin/', views.admin_cancel_requests, name='admin_cancel_requestes'),
    path('process/<int:req_id>/<str:action>/', views.process_cancel_request, name='process_cancel_request'),
]
