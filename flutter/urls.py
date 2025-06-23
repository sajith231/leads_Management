# flutter/urls.py
from django.urls import path
from .views import UserLoginView, UserListView, PunchInView, PunchOutView

urlpatterns = [
    path('login/', UserLoginView.as_view(), name='user-login'),
    path('users/', UserListView.as_view(), name='user-list'),
    path('punch-in/', PunchInView.as_view(), name='punch-in'),
    path('punch-out/', PunchOutView.as_view(), name='punch-out'),
]

# http://localhost:8000/flutter/login/

# http://localhost:8000/flutter/users/



# http://localhost:8000/flutter/punch-in/

# http://localhost:8000/flutter/punch-out/