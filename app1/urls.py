# from django.urls import path
# from . import views
# from .views import add_requirement 
# from .views import all_branches
# from .views import all_branches, delete_branch,users_table, delete_user,admin_dashboard, user_dashboard
# from .import views
# urlpatterns = [
#     # Authentication
#     path('', views.login, name='login'),
#     path('logout/', views.logout, name='logout'),
#     path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    
#     # Branch management
#     path('add-branch/', views.add_branch, name='add_branch'),
#     path('all-branches/', views.all_branches, name='all_branches'),
#     path('delete-branch/<int:branch_id>/', views.delete_branch, name='delete_branch'),
    
#     # Requirement management
#     path('add-requirement/', views.add_requirement, name='add_requirement'),
#     path('all-requirements/', views.all_requirements, name='all_requirements'),
#     path('delete-requirement/<int:requirement_id>/', views.delete_requirement, name='delete_requirement'),
    
#     # User management
#     path('add-user/', views.add_user, name='add_user'),
#     path('users-table/', views.users_table, name='users_table'),
#     path('delete-user/<int:user_id>/', views.delete_user, name='delete_user'),
#     path('edit-user/<int:user_id>/', views.edit_user, name='edit_user'),
#     path('admin-dashboard/', admin_dashboard, name='admin_dashboard'),
#     path('user-dashboard/', user_dashboard, name='user_dashboard'), 
# ]


from django.urls import path
from . import views
from .views import edit_lead
from .views import delete_lead 

urlpatterns = [
    # Authentication
    path('', views.login, name='login'),
    path('logout/', views.logout, name='logout'),
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),

    # Branch management
    path('add-branch/', views.add_branch, name='add_branch'),
    path('all-branches/', views.all_branches, name='all_branches'),
    path('delete-branch/<int:branch_id>/', views.delete_branch, name='delete_branch'),

    # Requirement management
    path('add-requirement/', views.add_requirement, name='add_requirement'),
    path('all-requirements/', views.all_requirements, name='all_requirements'),
    path('delete-requirement/<int:requirement_id>/', views.delete_requirement, name='delete_requirement'),

    # User management
    path('add-user/', views.add_user, name='add_user'),
    path('users-table/', views.users_table, name='users_table'),
    path('delete-user/<int:user_id>/', views.delete_user, name='delete_user'),
    path('edit-user/<int:user_id>/', views.edit_user, name='edit_user'),
    path('user-dashboard/', views.user_dashboard, name='user_dashboard'), 
    path('edit_branch/<int:branch_id>/', views.edit_branch, name='edit_branch'),
    path('edit-requirement/<int:requirement_id>/', views.edit_requirement, name='edit_requirement'),



    path('add-lead/', views.add_lead, name='add_lead'),
    path('edit_lead/<int:lead_id>/', edit_lead, name='edit_lead'),
     path('all-leads/', views.all_leads, name='all_leads'),
      path('delete_lead/<int:lead_id>/', delete_lead, name='delete_lead'),

]
