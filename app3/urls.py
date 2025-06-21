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
    path('salary-certificate/view/<int:employee_id>/', views.view_salary_certificate, name='view_salary_certificate'),
    path('salary-certificates/approve/<int:certificate_id>/', views.approve_salary_certificate, name='approve_salary_certificate'),

#interview management

    path('add_interview_management/', views.add_interview, name='add_interview_management'),
    path('interview_management/', views.interview_management, name='interview_management'),
    path('interview/delete/<int:pk>/', views.delete_interview, name='delete_interview'),
    path('interview/edit/<int:pk>/', views.edit_interview_management, name='edit_interview_management'),
    path('add-rating/<int:interview_id>/', views.add_rating, name='add_rating'),
    path('view-rating/<int:pk>/', views.view_rating, name='view_rating'),
    path('interview/<int:interview_id>/update_status/', views.update_status, name='update_status'),

    


#offer letter

    path('offer-letter/', views.make_offer_letter, name='make_offer_letter'),
    path('add_offer_letter/', views.add_offer_letter, name='add_offer_letter'),
    path('remove-offer-letter-candidate/<int:interview_id>/', views.remove_offer_letter_candidate, name='remove_offer_letter_candidate'),
    path('clear-offer-letter-list/', views.clear_offer_letter_list, name='clear_offer_letter_list'),
    path('offer-letter/<int:interview_id>/', views.generate_offer_letter, name='generate_offer_letter'),
    path('save-offer-letter/', views.save_offer_letter, name='save_offer_letter'),
    path('update-candidate-status/', views.update_candidate_status, name='update_candidate_status'),
    



    
    
]