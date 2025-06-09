# app/urls.py

from django.urls import path
from . import views

urlpatterns = [
    path('salary-certificates/', views.make_salary_certificate, name='make_salary_certificate'),
    path('get-employee-details/', views.get_employee_details, name='get_employee_details'),
    path('add-salary-certificate/', views.add_salary_certificate, name='add_salary_certificate'),
    path('save-salary-certificate/', views.save_salary_certificate, name='save_salary_certificate'),
    path('delete-salary-certificate/<int:salary_certificate_id>/', views.delete_salary_certificate, name='delete_salary_certificate'), 
    path('edit-salary-certificate/<int:salary_certificate_id>/', views.edit_salary_certificate, name='edit_salary_certificate'),
    path('salary-certificate/view/<int:employee_id>/', views.view_salary_certificate, name='view_salary_certificate'),]
