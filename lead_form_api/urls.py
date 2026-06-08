"""
lead_form_api/urls.py

URL configuration for the lead_form_api app.

Include this in your project's main urls.py:

    from django.urls import path, include

    urlpatterns = [
        ...
        path("api/", include("lead_form_api.urls")),
    ]

After that, the endpoints will be:
  POST   /api/leads/
  GET    /api/leads/
  GET    /api/leads/<id>/
  PUT    /api/leads/<id>/
  PATCH  /api/leads/<id>/
  DELETE /api/leads/<id>/
"""

from django.urls import path
from .views import LeadListCreateAPIView, LeadDetailAPIView

app_name = "lead_form_api"

urlpatterns = [
    path("leads/", LeadListCreateAPIView.as_view(), name="lead-list-create"),
    path("leads/<int:pk>/", LeadDetailAPIView.as_view(), name="lead-detail"),
]
