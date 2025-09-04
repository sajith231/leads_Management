# app5/urls.py
from django.urls import path
from . import views

app_name = 'app5'        # optional but useful for the {% url %} tag

urlpatterns = [
    path('jobcardlist/', views.jobcard_list, name='jobcard_list'),
    path('jobcardcreate/', views.jobcard_create, name='jobcard_create'),
    path('edit/<int:pk>/', views.jobcard_edit, name='jobcard_edit'),

    # THESE TWO LINES WERE MISSING
    path('update-status/<int:pk>/', views.update_jobcard_status, name='update_jobcard_status'),
    path('delete-ticket/<str:ticket_no>/', views.delete_ticket_by_number, name='delete_ticket_by_number'),

    path('delete-jobcard/<int:pk>/', views.delete_jobcard, name='delete_jobcard'),
    path('api/jobcard/<int:pk>/', views.api_jobcard_detail, name='api_jobcard_detail'),
]