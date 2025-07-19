# flutter/urls.py
from django.urls import path
from .views import UserLoginView, UserListView, PunchInView, PunchOutView,BreakPunchInView,BreakPunchOutView,BreakStatusView

from .views import (
    create_leave_request,
    get_leave_requests,
    delete_leave_request,   # <-- process_leave_request removed
)




urlpatterns = [
    path('login/', UserLoginView.as_view(), name='user-login'),
    path('users/', UserListView.as_view(), name='user-list'),
    path('punch-in/', PunchInView.as_view(), name='punch-in'),
    path('punch-out/', PunchOutView.as_view(), name='punch-out'),


# http://localhost:8000/flutter/login/

# http://localhost:8000/flutter/users/



# http://localhost:8000/flutter/punch-in/

# http://localhost:8000/flutter/punch-out/

# http://localhost:8000/flutter/break-punch-in/

# http://localhost:8000/flutter/break-punch-out/

# http://localhost:8000/flutter/break-status/







# https://app.dxing.in/api/send/whatsapp?secret=7b8ae820ecb39f8d173d57b51e1fce4c023e359e&account=1748250982812b4ba287f5ee0bc9d43bbf5bbe87fb683431662a427&recipient=$NO$&type=text&message=$MSG$&priority=1




    path('break-punch-in/', BreakPunchInView.as_view(), name='break-punch-in'),
    path('break-punch-out/', BreakPunchOutView.as_view(), name='break-punch-out'),
    path('break-status/', BreakStatusView.as_view(), name='break-status'),











    path('leave/create/', create_leave_request, name='create_leave_request'),
    path('leave/list/',   get_leave_requests,   name='get_leave_requests'),
    path('leave/delete/', delete_leave_request, name='delete_leave_request'),










    
]