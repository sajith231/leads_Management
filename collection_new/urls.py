from django.urls import path
from . import views

app_name = 'collection_new'

urlpatterns = [

    # ── Template views (web) ──────────────────────────────────────────────────
    path('collections/list/',
         views.collection_list,
         name='collection_list'),

    path('collections/add/',
         views.collection_add,
         name='collection_add'),

    path('collections/edit/<int:pk>/',
         views.collection_edit,
         name='collection_edit'),

    path('collections/delete/<int:pk>/',
         views.collection_delete,
         name='collection_delete'),

    path('collections/toggle-status/<int:pk>/',
         views.collection_toggle_status,
         name='collection_toggle_status'),

    path('acc-proxy/',
         views.acc_master_proxy,
         name='acc_master_proxy'),

    path('acc-dept-proxy/',
         views.acc_departments_proxy,
         name='acc_departments_proxy'),

    # ── REST API (mobile app) ─────────────────────────────────────────────────
    path('collections/api/list/',
         views.api_collection_list,
         name='api_collection_list'),

    path('collections/api/add/',
         views.api_collection_add,
         name='api_collection_add'),

    path('collections/api/<int:pk>/',
         views.api_collection_detail,
         name='api_collection_detail'),

    path('collections/api/<int:pk>/toggle-status/',
         views.api_collection_toggle_status,
         name='api_collection_toggle_status'),
]