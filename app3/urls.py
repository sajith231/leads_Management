from django.urls import path
from . import views

urlpatterns = [
    path('salary-certificate/', views.make_salary_certificate, name='make_salary_certificate'),
]