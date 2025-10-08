from django.urls import path
from . import views

urlpatterns = [
    # keep the SAME paths so existing frontend code still works
    path('today-requests/', views.today_requests, name='today_requests'),
    path('attendance/punchout-reminder/', views.send_punchout_reminders, name='punchout_reminder'),
]
