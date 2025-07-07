# urls.py
from django.urls import path
from . import views
from .views import InformationCenterListView, add_information_center,edit_information_center,delete_information_center
from .views import get_next_position
from .views import socialmedia_all_projects, socialmedia_add_project, socialmedia_edit_project, socialmedia_delete_project
from .views import socialmedia_all_tasks, socialmedia_add_task, socialmedia_edit_task, socialmedia_delete_task

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



    path('add-category/', views.add_category, name='add_category'),
    path('edit-category/<int:category_id>/', views.edit_category, name='edit_category'),
    path('delete-category/<int:category_id>/', views.delete_category, name='delete_category'),

    path('information-center/', InformationCenterListView.as_view(), name='information_center'),
    path('add-information-center/', add_information_center, name='add_information_center'),
    path('edit-information-center/<int:pk>/', edit_information_center, name='edit_information_center'),
    path('api/get_next_position/', get_next_position, name='get_next_position'),

    path('information_center_table/', views.information_center_table, name='information_center_table'),
    
    path('delete-information-center/<int:pk>/', views.delete_information_center, name='delete_information_center'),





    path('product-types/', views.product_type_list, name='product_type_list'),
    path('add-product-type/', views.add_product_type, name='add_product_type'),
    path('edit-product-type/<int:id>/', views.edit_product_type, name='edit_product_type'),
    path('delete-product-type/<int:id>/', views.delete_product_type, name='delete_product_type'),
    
    # Product Category URLs
    path('product-categories/', views.product_category_list, name='product_category_list'),
    path('add-product-category/', views.add_product_category, name='add_product_category'),
    path('edit-product-category/<int:id>/', views.edit_product_category, name='edit_product_category'),
    path('delete-product-category/<int:id>/', views.delete_product_category, name='delete_product_category'),


    path('category-detail/<int:category_id>/', views.category_detail, name='category_detail'),

    path('stop_task/', views.stop_task, name='stop_task'),


    








    
    path('daily_task_admin/', views.daily_task_admin, name='daily_task_admin'),
    path('daily_task_user/', views.daily_task_user, name='daily_task_user'),
    path('add_daily_task/', views.add_daily_task, name='add_daily_task'),
    path('edit_daily_task/<int:task_id>/', views.edit_daily_task, name='edit_daily_task'),
    path('delete_daily_task/<int:task_id>/', views.delete_daily_task, name='delete_daily_task'),




    path('clients/', views.show_clients, name='show_clients'),


    path('departments/', views.all_department, name='all_department'),
    path('departments/add/', views.add_department, name='add_department'),
    path('departments/edit/<int:id>/', views.edit_department, name='edit_department'),
    path('departments/delete/<int:id>/', views.delete_department, name='delete_department'),
    path('job-roles/', views.job_roles, name='job_roles'),
    path('job-roles/add/', views.add_job_role, name='add_job_role'),
    path('job-roles/edit/<int:id>/', views.edit_job_role, name='edit_job_role'),
    path('job-roles/delete/<int:id>/', views.delete_job_role, name='delete_job_role'),




    path('customers/', views.all_customers, name='all_customers'),
    path('customers/add/', views.add_customer, name='add_customer'),
    path('customers/edit/<int:id>/', views.edit_customer, name='edit_customer'),
    path('customers/delete/<int:id>/', views.delete_customer, name='delete_customer'),

    path('socialmedia/projects/', socialmedia_all_projects, name='socialmedia_all_projects'),
    path('socialmedia/projects/add/', socialmedia_add_project, name='socialmedia_add_project'),
    path('socialmedia/projects/edit/<int:id>/', socialmedia_edit_project, name='socialmedia_edit_project'),
    path('socialmedia/projects/delete/<int:id>/', socialmedia_delete_project, name='socialmedia_delete_project'),


    path('tasks/', socialmedia_all_tasks, name='socialmedia_all_tasks'),
    path('tasks/add/', socialmedia_add_task, name='socialmedia_add_task'),
    path('tasks/edit/<int:id>/', socialmedia_edit_task, name='socialmedia_edit_task'),
    path('tasks/delete/<int:id>/', socialmedia_delete_task, name='socialmedia_delete_task'),
    

    
    

    
]
