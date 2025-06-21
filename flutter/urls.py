from django.urls import path
from .views import UserLoginView,UserListView

urlpatterns = [
    path('login/', UserLoginView.as_view(), name='user-login'),
    path('users/', UserListView.as_view(), name='user-list'),
]