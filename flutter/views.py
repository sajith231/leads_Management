from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import UserLoginSerializer


class UserLoginView(APIView):
    def post(self, request):
        serializer = UserLoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            return Response({
                'userid': user.userid,
                'name': user.name,
                'user_level': user.get_user_level_display(),
                'status': user.status,
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    


# flutter/views.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import UserSerializer
from app1.models import User  # Adjust the import based on your actual app name

class UserListView(APIView):
    def get(self, request):
        users = User.objects.all()
        serializer = UserSerializer(users, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    







# http://localhost:8000/flutter/login/

# http://localhost:8000/flutter/users/

# {
#     "userid": "sajiththomas231@gmail.com",
#     "password": "8"
# }