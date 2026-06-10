from django.urls import path
from . import views
from .api_views import EnquiryListCreateAPIView, EnquiryDetailAPIView

urlpatterns = [
    # ── HTML views ─────────────────────────────────────────
    path('',                 views.enquiry_list,   name='enquiry_list'),
    path('add/',             views.enquiry_add,    name='enquiry_form'),
    path('edit/<int:pk>/',   views.enquiry_edit,   name='enquiry_edit'),
    path('delete/<int:pk>/', views.enquiry_delete, name='enquiry_delete'),

    # ── REST API (mobile app) ───────────────────────────────
    path('api/',             EnquiryListCreateAPIView.as_view(), name='enquiry_api_list'),
    path('api/<int:pk>/',    EnquiryDetailAPIView.as_view(),     name='enquiry_api_detail'),
]