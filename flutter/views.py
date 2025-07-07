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
    







# https://localhost:8000/flutter/login/

# https://localhost:8000/flutter/users/

# {
#     "userid": "sajiththomas231@gmail.com",
#     "password": "8"
# }

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import AttendanceSerializer
from app1.models import Attendance, Employee, User
from django.utils import timezone
# from rest_framework.permissions import IsAuthenticated
# from rest_framework.authentication import SessionAuthentication, BasicAuthentication


class PunchInView(APIView):
    def post(self, request):
        userid = request.data.get('userid')
        password = request.data.get('password')
        location = request.data.get('location')
        latitude = request.data.get('latitude')
        longitude = request.data.get('longitude')
        enhanced_location = request.data.get('enhanced_location', {})

        # Validate User login
        try:
            user = User.objects.get(userid=userid, password=password)
        except User.DoesNotExist:
            return Response({'error': 'Invalid userid or password'}, status=status.HTTP_401_UNAUTHORIZED)

        # Validate Employee (linked via ForeignKey)
        try:
            employee = Employee.objects.get(user=user)
        except Employee.DoesNotExist:
            return Response({'error': 'Employee not found for this user'}, status=status.HTTP_404_NOT_FOUND)

        # Attendance logic
        today = timezone.now().date()
        day_number = today.weekday()

        attendance, created = Attendance.objects.get_or_create(
            employee=employee,
            date=today,
            defaults={
                'status': 'half',
                'day': day_number
            }
        )

        if not created and attendance.punch_in:
            return Response({'error': 'You have already punched in today'}, status=status.HTTP_400_BAD_REQUEST)

        attendance.punch_in = timezone.now()
        attendance.punch_in_location = location
        attendance.punch_in_latitude = latitude
        attendance.punch_in_longitude = longitude
        attendance.save()

        serializer = AttendanceSerializer(attendance)
        return Response({
            'message': 'Punch in successful',
            'date': str(today),
            'attendance': serializer.data
        }, status=status.HTTP_200_OK)



from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import AttendanceSerializer
from app1.models import Attendance, Employee, User
from django.utils import timezone

class PunchOutView(APIView):
    def post(self, request):
        userid = request.data.get('userid')
        password = request.data.get('password')
        location = request.data.get('location')
        latitude = request.data.get('latitude')
        longitude = request.data.get('longitude')
        enhanced_location = request.data.get('enhanced_location', {})
        today = timezone.now().date()

        # Validate User login
        try:
            user = User.objects.get(userid=userid, password=password)
        except User.DoesNotExist:
            return Response({'error': 'Invalid userid or password'}, status=status.HTTP_401_UNAUTHORIZED)

        # Get Employee linked to this user
        try:
            employee = Employee.objects.get(user=user)
        except Employee.DoesNotExist:
            return Response({'error': 'Employee not found for this user'}, status=status.HTTP_404_NOT_FOUND)

        # Get today's attendance
        try:
            attendance = Attendance.objects.get(employee=employee, date=today)
        except Attendance.DoesNotExist:
            return Response({'error': 'No punch-in record found for today'}, status=status.HTTP_400_BAD_REQUEST)

        if attendance.punch_out:
            return Response({'error': 'You have already punched out today'}, status=status.HTTP_400_BAD_REQUEST)

        attendance.punch_out = timezone.now()
        attendance.punch_out_location = location
        attendance.punch_out_latitude = latitude
        attendance.punch_out_longitude = longitude
        attendance.status = 'full'
        attendance.save()

        serializer = AttendanceSerializer(attendance)
        return Response({
            'message': 'Punch out successful',
            'date': str(today),
            'attendance': serializer.data
        }, status=status.HTTP_200_OK)




#https://localhost:8000/flutter/punch-in/

#https://localhost:8000/flutter/punch-out/





# {
#   "userid": "john123",
#   "password": "secret",
#   "location": "Calicut",
#   "latitude": 11.1234,
#   "longitude": 75.1234,
#   "enhanced_location": {
#     "address": "Calicut, Kerala",
#     "city": "Calicut",
#     "timezone": "Asia/Kolkata"
#   }
# }