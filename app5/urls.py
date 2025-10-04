# app5/urls.py
from django.urls import path
from . import views

app_name = 'app5'        # optional but useful for the {% url %} tag

urlpatterns = [
    path('jobcardlist/', views.jobcard_list, name='jobcard_list'),
    path('jobcardcreate/', views.jobcard_create, name='jobcard_create'),
    path('edit/<int:pk>/', views.jobcard_edit, name='jobcard_edit'),

    # THESE TWO LINES WERE MISSING
    path("update_status/<int:pk>/", views.update_jobcard_status, name="update_jobcard_status"),
    path('delete-ticket/<str:ticket_no>/', views.delete_ticket_by_number, name='delete_ticket_by_number'),
    path('item-master/', views.item_master, name='item_master'),
    path('delete-jobcard/<int:pk>/', views.delete_jobcard, name='delete_jobcard'),
    path('api/jobcard/<int:pk>/', views.api_jobcard_detail, name='api_jobcard_detail'),

   
    path("jobcardlist/", views.jobcard_list, name="jobcard_list"),
    path("item-master/", views.item_master, name="item_master"),
    path("item/add/", views.add_item, name="add_item"),
    path("item/edit/<int:item_id>/", views.edit_item, name="edit_item"),
    path("item/delete/<int:item_id>/", views.delete_item, name="delete_item"),



    path("jobcard/assign-table/", views.jobcard_assign_table, name="jobcard_assign_table"),
    path("assign-new/", views.assign_new_job, name="assign_new_job"),
    path("assign/edit/<int:pk>/", views.jobcard_assign_edit, name="jobcard_assign_edit"),

    # Add this to your urlpatterns
    path('get-customer-by-ticket/<str:ticket_no>/', views.get_customer_by_ticket, name='get_customer_by_ticket'),

   path('suppliermaster/', views.supplier_master, name='supplier_master'),
   path('suppliermaster/add/', views.supplier_master_add, name='supplier_master_add'),
   path("suppliermaster/delete/<int:pk>/", views.supplier_master_delete, name="supplier_master_delete"),
   path("suppliermaster/edit/<int:pk>/", views.supplier_master_edit, name="supplier_master_edit"),
   

   path("jobcard/technician-accept/", views.job_technician_accept, name="job_technician_accept"),
   path("jobcard/<int:pk>/update-status/", views.update_jobcard_status, name="update_jobcard_status"),


   path('jobcard/<int:jobcard_id>/standby-issue/', views.standby_issue_form, name='standby_issue_form'),
    path('jobcard/<int:jobcard_id>/standby-issue-item/', views.standby_issue_item, name='standby_issue_item'),
    path('jobcard/<int:jobcard_id>/standby-return/', views.standby_return_item, name='standby_return_item'),
    path('jobcard/<int:jobcard_id>/standby-details/', views.view_standby_issuance_details, name='view_standby_issuance_details'),


]


