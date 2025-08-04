from django.db import models

# Create your models here.
from django.urls import path
from . import views

urlpatterns = [
    path('lecence-type/', views.lecence, name='lecence_type')
]