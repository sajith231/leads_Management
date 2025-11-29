# public_folder/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path("public-upload/", views.public_upload, name="public_upload"),
    path("public-list/", views.public_list, name="public_list"),
    path("download-file/<uuid:file_id>/", views.download_file, name="download_file"),
    path("delete-file/<uuid:file_id>/", views.delete_file, name="delete_file"),
    path("send-whatsapp/", views.send_whatsapp, name="send_whatsapp"),
]