# app5/urls.py
from django.urls import path,include
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
     path('update-status/<int:pk>/', views.update_status, name='update_status'),
    path('api/jobcard-status/<str:ticket_no>/', views.api_jobcard_status, name='api_jobcard_status'),

   path('suppliermaster/', views.supplier_master, name='supplier_master'),
   path('suppliermaster/add/', views.supplier_master_add, name='supplier_master_add'),
   path("suppliermaster/delete/<int:pk>/", views.supplier_master_delete, name="supplier_master_delete"),
   path("suppliermaster/edit/<int:pk>/", views.supplier_master_edit, name="supplier_master_edit"),
   

   path("jobcard/technician-accept/", views.job_technician_accept, name="job_technician_accept"),
   path("jobcard/<int:pk>/update-status/", views.update_jobcard_status, name="update_jobcard_status"),


   path('jobcard/<int:jobcard_id>/standby-issue/', views.standby_issue_form, name='standby_issue_form'),
    path('jobcard/<int:jobcard_id>/standby-issue-item/', views.standby_issue_item, name='standby_issue_item'),
    path('api/jobcard-detail/<int:pk>/', views.api_jobcard_detail, name='api_jobcard_detail'),
    path('jobcard/<int:jobcard_id>/standby-return/', views.standby_issuance_return, name='standby_return_item'),
    
    path('jobcard/<int:jobcard_id>/standby-details/', views.view_standby_issuance_details, name='view_standby_issuance_details'),
   
    

  
 
   # Warranty URLs
    path('warranty-item/', views.warranty_item_management, name='warranty_item'),
    path('warranty-tickets/', views.warranty_ticket_list, name='warranty_ticket_list'),
    path('warranty-ticket/<int:ticket_id>/', views.warranty_ticket_detail, name='warranty_ticket_detail'),
    path('warranty-ticket/<int:ticket_id>/update-status/', views.update_warranty_item_status, name='update_warranty_item_status'),
    path('process-warranty-tickets/', views.process_warranty_tickets, name='process_warranty_tickets'),
    
    # API endpoints for warranty
    path('api/all-warranty-tickets/', views.api_all_warranty_tickets, name='api_all_warranty_tickets'),
    path('api/ticket-details/', views.api_ticket_details, name='api_ticket_details'),
    path('api/warranty-details/', views.api_warranty_details, name='api_warranty_details'),
    path('warranty/tickets/<int:ticket_id>/edit/', views.warranty_ticket_edit, name='warranty_ticket_edit'),
    path('warranty/tickets/<int:ticket_id>/delete/', views.warranty_ticket_delete, name='warranty_ticket_delete'),
    path('warranty/tickets/<int:ticket_id>/return/', views.return_warranty_item, name='return_warranty_item'),
    path('returns/<int:return_id>/', views.return_item_detail, name='return_item_detail'),
    path('returns/<int:return_id>/delete/', views.return_item_delete, name='return_item_delete'),

    path('service-billing/', views.service_billing_view, name='service_billing_view'),
    path('get-jobcard-details/<str:ticket_no>/', views.get_jobcard_details, name='get_jobcard_details'),
    path('service-billing/list/', views.service_billing_list, name='service_billing_list'),
    # Add this to your urlpatterns in urls.py
    path('service-billing/edit/<str:ticket_no>/', views.service_billing_edit, name='service_billing_edit'),
    path('service-billing/view/<str:ticket_no>/', views.view_service_invoice, name='view_service_invoice'),
    path('delete-service-invoice/<str:ticket_no>/', views.delete_service_invoice, name='delete_service_invoice'),
    path('jobcard/update-status/<int:pk>/', views.update_jobcard_status, name='update_jobcard_status'),
    path('jobcard/update-status-by-ticket/', views.update_jobcard_status_by_ticket, name='update_jobcard_status_by_ticket'),

# lead
    path("lead/", views.lead_form_view, name="lead"),
    path("lead-report/", views.lead_report_view, name="lead_report"),
    # app5/urls.py
   path('requirement-form/', views.requirement_form, name='requirement_form'),
   path('requirements-list/', views.requirements_list_view, name='requirements_list'),
   path('requirement-items/edit/<int:requirement_id>/', views.requirement_edit, name='requirement_edit'),
   path('requirement/delete/<int:item_id>/', views.requirement_delete, name='requirement_delete'),


   path('lead/<int:lead_id>/edit/', views.lead_edit, name='lead_edit'),  
   path('lead/delete/<int:lead_id>/', views.lead_delete, name='lead_delete'),
   path('api/lead/<int:lead_id>/', views.lead_detail_api, name='lead_detail_api'),
   path('requirement-form/', views.requirement_form, name='requirement_form'),
   path('requirement-list/', views.requirement_list, name='requirement_list'),
   # Lead Assignment URLs
    path('lead-assign-list/', views.lead_assign_list_view, name='lead_assign_list'),
    path('assign-lead/', views.assign_lead_view, name='assign_lead'),

    path('lead/assign/edit/<lead_id>/', views.lead_assign_edit, name='lead_assign_edit'),  # <-- this name fixes your template reverse() cal),
    path('delete-lead/<int:lead_id>/', views.delete_lead_view, name='delete_lead'),
   



    path('business-nature/', views.business_nature_list, name='business_nature_list'),
    path('business-nature/create/', views.business_nature_create, name='business_nature_create'),
    path('business-nature/edit/<int:id>/', views.business_nature_edit, name='business_nature_edit'),
    path('business-nature/delete/<int:pk>/', views.business_nature_delete, name='business_nature_delete'),



     path('state/', views.state_list, name='state_master_list'),  # Changed to state_master_list
    path('state/create/', views.state_master_create, name='state_master_create'),
    path('state/<int:id>/edit/', views.state_master_edit, name='state_master_edit'),
    path('state/<int:id>/delete/', views.state_master_delete, name='state_master_delete'),
]


