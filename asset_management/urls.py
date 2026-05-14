from django.urls import path

from . import views

urlpatterns = [

    # ══════════════════════════════════════════════════════
    #  ASSET MANAGEMENT — Page  (asset_list.html)
    # ══════════════════════════════════════════════════════

    path('asset-management/', views.asset_management, name='asset_management'),

    # ══════════════════════════════════════════════════════
    #  ASSET MASTER — Page  (assets_master.html)
    # ══════════════════════════════════════════════════════

    path('assets-master/', views.assets_master, name='assets_master'),

    

    path('api/assets/',
         views.asset_list,   name='asset_list'),

    path('api/assets/add/',
         views.asset_add,    name='asset_add'),

    path('api/assets/<str:asset_id>/',
         views.asset_detail, name='asset_detail'),

    path('api/assets/<str:asset_id>/edit/',
         views.asset_edit,   name='asset_edit'),

    path('api/assets/<str:asset_id>/delete/',
         views.asset_delete, name='asset_delete'),

  
    path('assignments/',
         views.assignment_list_page, name='assignment_list'),

    path('assignments/add/',
         views.assignment_add_page,  name='assignment_add'),

    path('assignments/<int:assignment_id>/',
         views.assignment_detail_page, name='assignment_detail_page'),

    path('assignments/<int:assignment_id>/edit/',
         views.assignment_edit_page, name='assignment_edit_page'),

    path('assignments/<int:assignment_id>/return/',
         views.assignment_return_page, name='assignment_return_page'),

    
    path('api/assignments/',
         views.assignment_list,   name='api_assignment_list'),

    path('api/assignments/add/',
         views.assignment_add,    name='api_assignment_add'),

    path('api/assignments/<int:assignment_id>/',
         views.assignment_detail, name='api_assignment_detail'),

    path('api/assignments/<int:assignment_id>/edit/',
         views.assignment_edit,   name='api_assignment_edit'),

    path('api/assignments/<int:assignment_id>/delete/',
         views.assignment_delete, name='api_assignment_delete'),
]