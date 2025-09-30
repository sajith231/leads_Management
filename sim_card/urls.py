from django.urls import path
from . import views

urlpatterns = [
    path('sim-management/', views.sim_management, name='sim_management'),
    path("sim-management/add/", views.add_sim, name="add_sim"),
    path('sim/<int:sim_id>/edit/', views.edit_sim, name='edit_sim'),
    path('sim/<int:sim_id>/delete/', views.delete_sim, name='delete_sim'),
    path('sim/reminder/', views.sim_reminder, name='sim_reminder'),
    path('sim/<int:sim_id>/recharge/add/', views.add_recharge, name='add_recharge'),
    path('sim/<int:sim_id>/recharges/', views.sim_recharge_history, name='sim_recharge_history'),
    path('recharge/<int:recharge_id>/delete/', views.delete_recharge, name='delete_recharge'),


]