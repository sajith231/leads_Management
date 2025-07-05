from django.urls import path
from . import views
from .views import edit_lead
from .views import delete_lead 
from .views import load_areas
from .views import toggle_interview_status

from .views import save_offer_letter_details,get_offer_letter_details
from .views import employee_management, add_employee,edit_employee,delete_employee
from .views import document_list,DocumentSetting,add_document,add_document_setting,edit_document,delete_document,get_document_settings

from .views import add_document_setting, get_document_settings, delete_document_setting
from .views import document_detail,save_document_settings
from .views import get_document_setting_fields

from .views import view_attachment
from .views import save_attendance
from .views import update_setting_positions

from .views import reminder_type_view, add_reminder_type, edit_reminder_type, delete_reminder_type,update_attendance
from .views import update_attendance_status,get_customers,attendance_summary
from .views import attendance_total_summary
from .views import edit_profile


urlpatterns = [
    # Authentication
    path('', views.login, name='login'),
    path('logout/', views.logout, name='logout'),
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),

    # Branch management
    path('add-branch/', views.add_branch, name='add_branch'),
    path('all-branches/', views.all_branches, name='all_branches'),
    path('delete-branch/<int:branch_id>/', views.delete_branch, name='delete_branch'),

    # Requirement management
    path('add-requirement/', views.add_requirement, name='add_requirement'),
    path('all-requirements/', views.all_requirements, name='all_requirements'),
    path('delete-requirement/<int:requirement_id>/', views.delete_requirement, name='delete_requirement'),

    # User management
    path('add-user/', views.add_user, name='add_user'),
    path('users-table/', views.users_table, name='users_table'),
    path('delete-user/<int:user_id>/', views.delete_user, name='delete_user'),
    path('edit-user/<int:user_id>/', views.edit_user, name='edit_user'),
    path('user-dashboard/', views.user_dashboard, name='user_dashboard'), 
    path('edit_branch/<int:branch_id>/', views.edit_branch, name='edit_branch'),
    path('edit-requirement/<int:requirement_id>/', views.edit_requirement, name='edit_requirement'),


    #LEADS URLSS
    path('add-lead/', views.add_lead, name='add_lead'),
    path('edit_lead/<int:lead_id>/', edit_lead, name='edit_lead'),
    path('all-leads/', views.all_leads, name='all_leads'),
    path('delete_lead/<int:lead_id>/', delete_lead, name='delete_lead'),
    path('toggle-planet-entry/', views.toggle_planet_entry, name='toggle_planet_entry'),
    path('toggle_status/', views.toggle_status, name='toggle_status'),

    # DISTRICT URLS
    path('districts/add/', views.add_district, name='add_district'),
    path('districts/', views.all_districts, name='all_districts'),
    path('districts/delete/<int:district_id>/', views.delete_district, name='delete_district'),
    path('districts/edit/<int:district_id>/', views.edit_district, name='edit_district'),
    #AREA URLS
    path('area/add/', views.add_area, name='add_area'),
    path('area/all/', views.all_areas, name='all_areas'),
    path('area/delete/<int:area_id>/', views.delete_area, name='delete_area'),
    path('area/edit/<int:area_id>/', views.edit_area, name='edit_area'),
    #LOCATION URLS
    path('locations/', views.all_locations, name='all_locations'),
    path('locations/add/', views.add_location, name='add_location'),
    path('locations/<int:location_id>/edit/', views.edit_location, name='edit_location'),
    path('locations/<int:location_id>/delete/', views.delete_location, name='delete_location'),
    path('ajax/load-areas/', load_areas, name='load_areas'),
    path('load-locations/', views.load_locations, name='load_locations'),
    path('get-location-details/', views.get_location_details, name='get_location_details'),
    path('get-location-details/', views.get_location_details, name='get_location_details'),


    #HARDWARE URLS
    path('add_hardware/', views.add_hardware, name='add_hardware'),
    path('all_hardwares/', views.all_hardwares, name='all_hardwares'),
    path('edit_hardware/<int:hardware_id>/', views.edit_hardware, name='edit_hardware'),
    path('delete_hardware/<int:hardware_id>/', views.delete_hardware, name='delete_hardware'),



    #COMPLAINT URLS
    path('add-complaint/', views.add_complaint, name='add_complaint'),
    path('all-complaints/', views.all_complaints, name='all_complaints'),
    path('edit_complaint/<int:complaint_id>/', views.edit_complaint, name='edit_complaint'),
    path('delete_complaint/<int:complaint_id>/', views.delete_complaint, name='delete_complaint'),
    

   
    path('service-entry/', views.service_entry, name='service_entry'),
    path('service-entry/add/', views.add_service_entry, name='add_service_entry'),
    path('service_entry/edit/<int:entry_id>/', views.edit_service_entry, name='edit_service_entry'),
    path('service_entry/delete/<int:entry_id>/', views.delete_service_entry, name='delete_service_entry'),
    #SERVICE ENTRY URLS
    path('user/service-entry/', views.user_service_entry, name='user_service_entry'),
    path('user/service-entry/add/', views.user_add_service_entry, name='user_add_service_entry'),
    path('user/service-entry/edit/<int:entry_id>/', views.user_edit_service_entry, name='user_edit_service_entry'),
    path('user/service-entry/delete/<int:entry_id>/', views.user_delete_service_entry, name='user_delete_service_entry'),
    #AGENT URLS
    path('agents/', views.agent_list, name='agent_list'),
    path('agents/add/', views.add_agent, name='add_agent'),
    path('agents/edit/<int:agent_id>/', views.edit_agent, name='edit_agent'),
    path('agents/delete/<int:agent_id>/', views.delete_agent, name='delete_agent'),
    #CV URLS
    path('cvmanagement/', views.cv_management, name='cv_management'),
    path('add/', views.add_cv, name='add_cv'),
    path('edit/<int:id>/', views.edit_cv, name='edit_cv'),
    path('delete/<int:id>/', views.delete_cv, name='delete_cv'),
    path('toggle-interview-status/', toggle_interview_status, name='toggle_interview_status'),

    #JOB TITILE URLS
    path('job-titles/', views.job_titles, name='job_titles'),
    path('add-job-title/', views.add_job_title, name='add_job_title'),
    path('edit-job-title/<int:title_id>/', views.edit_job_title, name='edit_job_title'),
    path('delete-job-title/<int:title_id>/', views.delete_job_title, name='delete_job_title'),

    
    



      
      



    path('business-types/', views.business_type_list, name='business_type_list'),
    path('business-type/create/', views.create_business_type, name='create_business_type'),
    path('business-type/<int:id>/update/', views.update_business_type, name='update_business_type'),
    path('business-type/<int:id>/delete/', views.delete_business_type, name='delete_business_type'),

    path('offer-letter/<int:cv_id>/', views.offer_letter, name='offer_letter'),
    path('save-offer-letter-details/<int:cv_id>/', save_offer_letter_details, name='save_offer_letter_details'),

    path('get-offer-letter-details/<int:cv_id>/', get_offer_letter_details, name='get_offer_letter_details'),

    path('employee_management/', employee_management, name='employee_management'),
    path('add_employee/', add_employee, name='add_employee'),
    path('edit_employee/<int:emp_id>/', edit_employee, name='edit_employee'),  # 🔥 Fixing the issue
    path('delete_employee/<int:emp_id>/', delete_employee, name='delete_employee'),

    

    


    path('documents/', document_list, name='document_list'),
    path('documents/add/', add_document, name='add_document'),
    path('documents/edit/<int:id>/', edit_document, name='edit_document'),
    path('documents/delete/<int:id>/', delete_document, name='delete_document'),
    path('documents/settings/add/', add_document_setting, name='add_document_setting'),
    path('documents/settings/get/<int:doc_id>/', get_document_settings, name='get_document_settings'),
    path('settings/delete/<int:setting_id>/', views.delete_document_setting, name='delete_document_setting'),

    path('document/<int:doc_id>/', document_detail, name='document_detail'),
    path('update_setting_positions/<int:doc_id>/', update_setting_positions, name='update_setting_positions'),
    path('update_field_positions/<int:setting_id>/', views.update_field_positions, name='update_field_positions'),
    path('settings/edit/<int:setting_id>/', views.edit_document_setting, name='edit_document_setting'),
    path('documents/settings/save/<int:doc_id>/', save_document_settings, name='save_document_settings'),

    path('documents/settings/fields/get/<int:setting_id>/', get_document_setting_fields, name='get_document_setting_fields'),
    path('attachment/setting/<int:setting_id>/', views.view_attachment, name='view_setting_attachment'),
    path('attachment/field/<int:field_id>/', view_attachment, name='view_field_attachment'),

    
    

    
    path('generate_offer_letter/<int:cv_id>/', views.generate_offer_letter, name='generate_offer_letter'),

    path('save_offer_letter_details/<int:cv_id>/', views.save_offer_letter_details, name='save_offer_letter_details'),
    path('get_offer_letter_details/<int:cv_id>/', views.get_offer_letter_details, name='get_offer_letter_details'),
    path('generate_offer_letter/<int:cv_id>/', views.generate_offer_letter, name='generate_offer_letter'),

    
    path('user-control/<int:user_id>/', views.user_control, name='user_control'),


    path('attendance/', views.attendance, name='attendance'),
    path('attendance_user/', views.attendance_user, name='attendance_user'),
    path('save_attendance/<int:employee_id>/<int:day>/<str:status>/', save_attendance, name='save_attendance'),
    path('punch_in/', views.punch_in, name='punch_in'),
    path('punch_out/', views.punch_out, name='punch_out'),
    path('get_attendance_status/', views.get_attendance_status, name='get_attendance_status'),
    path('update_attendance/', views.update_attendance, name='update_attendance'),
    path('get_attendance_data/', views.get_attendance_data, name='get_attendance_data'),

    








    path('reminder-types/', reminder_type_view, name='reminder_type'),
    path('add-reminder-type/', add_reminder_type, name='add_reminder_type'),
    path('edit-reminder-type/<int:id>/', edit_reminder_type, name='edit_reminder_type'),
    path('delete-reminder-type/<int:id>/', delete_reminder_type, name='delete_reminder_type'),
    
    path("update_attendance_status/", update_attendance_status, name="update_attendance_status"),
    path('get_current_employee_id/', views.get_current_employee_id, name='get_current_employee_id'),




    path('reminders/', views.reminders, name='reminders'),
    path("add-reminder/", views.add_reminder, name="add_reminder"),
    path('reminders/add/', views.add_reminder, name='add_reminder'),
    path('reminder/edit/<int:reminder_no>/', views.edit_reminder, name='edit_reminder'),
    path('reminders/delete/<int:reminder_id>/', views.delete_reminder, name='delete_reminder'),




    path('add_holiday/', views.add_holiday, name='add_holiday'),
    path('get_holidays/', views.get_holidays, name='get_holidays'),
    path('delete_holiday/', views.delete_holiday, name='delete_holiday'),
    path("proxy/customers/", get_customers, name="proxy_customers"),



    
    path('leave_request/create/', views.create_leave_request, name='create_leave_request'),
    path('leave_request/list/', views.get_leave_requests, name='get_leave_requests'),
    path('leave_request/process/', views.process_leave_request, name='process_leave_request'),
    path('leave_request/delete/', views.delete_leave_request, name='delete_leave_request'),
    
    
    path('late_request/create/', views.create_late_request, name='create_late_request'),
    path('late_request/list/', views.get_late_requests, name='get_late_requests'),
    path('late_request/process/', views.process_late_request, name='process_late_request'),
    path('late_request/delete/', views.delete_late_request, name='delete_late_request'),
    path('attendance/summary/<int:employee_id>/', attendance_summary, name='attendance_summary'),
    path('attendance/total-summary/', attendance_total_summary, name='attendance_total_summary'),




    
    
    #Project Management
    #Project Management
    path('project-management/', views.project_management, name='project_management'),
    path('add-project/', views.add_project, name='add_project'),
    path('project_work/', views.project_work, name='project_work'),
    path('project/edit/<int:project_id>/', views.edit_project, name='edit_project'),
    path('project/delete/<int:project_id>/', views.delete_project, name='delete_project'),
    path('user-projects/', views.user_projects, name='user_projects'),
    path('update-project-status/', views.update_project_status, name='update_project_status'),
    path('project/work/edit/<int:work_id>/', views.edit_project_work, name='edit_project_work'),
    path('project-work/delete/<int:work_id>/', views.delete_project_work, name='delete_project_work'),

    #Task
    path('tasks/', views.task_list, name='task_list'),
    path('tasks/add/', views.add_task, name='add_task'),
    path('tasks/update-status/<int:task_id>/', views.update_task_status, name='update_task_status'),


    
    path('user_menu_control/', views.user_menu_control, name='user_menu_control'),
    path('configure_user_menu/<int:user_id>/', views.configure_user_menu, name='configure_user_menu'),
    path('default_menus/', views.default_menus, name='default_menus'),
    path('edit-profile/', edit_profile, name='edit_profile'),
    




   
    path('break_time_management/', views.break_time_management, name='break_time_management'),
    path('handle_break_punch/<str:action>/', views.handle_break_punch, name='handle_break_punch'),
    path('get_break_status/', views.get_break_status, name='get_break_status'),



    path('early_request/create/', views.create_early_request, name='create_early_request'),
    path('early_request/list/', views.get_early_requests, name='list_early_requests'),
    path('early_request/process/', views.process_early_request, name='process_early_request'),
    path('early_request/delete/', views.delete_early_request, name='delete_early_request'),




    path('service-log/', views.servicelog_list, name='servicelog_list'),
    path('service-log/add/', views.add_service_log, name='add_service_log'),
    path('service-log/edit/<int:log_id>/', views.edit_service_log, name='edit_service_log'),
    path('service-log/delete/<int:log_id>/', views.delete_service_log, name='delete_service_log'),

    path('user-service-logs/', views.user_service_log, name='user_service_log'),
    path('update_status/', views.update_status, name='update_status'),
    path('assign_service_logs/', views.assign_service_logs, name='assign_service_logs'),
    path('assign_work/<int:log_id>/', views.assign_work, name='assign_work'),
    path('my_assigned_service_logs/', views.my_assigned_service_logs, name='my_assigned_service_logs'),
    path('reassign_work/<int:log_id>/', views.reassign_work, name='reassign_work'),
    path('update_complaint_status/', views.update_complaint_status, name='update_complaint_status'),
    path('reassign_complaint/', views.reassign_complaint, name='reassign_complaint'),






    






    


    

    



    

    


    

    

    

]
