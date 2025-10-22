from django.urls import path
from . import views

urlpatterns = [
    # Folder routes
    path("drive/", views.drive_list, name="drive_list"),
    path("drives/add/", views.drive_add, name="drive_add"),
    path("drives/delete/<int:pk>/", views.drive_delete, name="drive_delete"),
    path("drives/<int:pk>/", views.drive_detail, name="drive_detail"),
    path("drives/<int:parent_pk>/add-subfolder/", views.subfolder_add, name="subfolder_add"),
    path("drives/<int:pk>/edit/", views.drive_edit, name="drive_edit"),  # optional

    # File routes
    path("files/<int:pk>/delete/", views.file_delete, name="file_delete"),
    path("files/<int:pk>/edit/", views.file_edit, name="file_edit"),      # ✅ this is what the modal calls
    path("files/<int:pk>/preview/", views.file_preview, name="file_preview"),
    path("files/<int:pk>/download/", views.file_download, name="file_download"),
    
    # Subfolder route
    path("subfolder/<int:pk>/delete/", views.subfolder_delete, name="subfolder_delete"),
    path("files/<int:pk>/edit_name/", views.file_edit_page, name="file_edit_page"),

]
