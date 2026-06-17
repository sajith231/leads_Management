# rrc_clients_new/urls.py

from django.urls import path
from . import views

app_name = "rrc_clients_new"

urlpatterns = [
    path("rrc-clients2/", views.rrc_clients2_list, name="rrc_clients2_list"),
    path("rrc-clients2/api/", views.rrc_clients2_api, name="rrc_clients2_api"),
]