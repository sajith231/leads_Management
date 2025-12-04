from django.urls import path
from . import views

urlpatterns = [
    path('create/',  views.create_wfh_request,  name='create_wfh_request'),
    path('list/',    views.list_wfh_requests,   name='list_wfh_requests'),
    path('process/', views.process_wfh_request, name='process_wfh_request'),
    path('delete/',  views.delete_wfh_request,  name='delete_wfh_request'),
]
