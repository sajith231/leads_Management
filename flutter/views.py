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




# flutter/views.py - Add these views to your existing file

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from app1.models import BreakTime, Employee, User
from django.utils import timezone
from datetime import datetime
import pytz

class BreakPunchInView(APIView):
    def post(self, request):
        userid = request.data.get('userid')
        password = request.data.get('password')

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

        # Use Indian timezone
        indian_tz = pytz.timezone('Asia/Kolkata')
        now = datetime.now(indian_tz)
        today = now.date()

        # Check if there's an active break (punch in without punch out)
        active_break = BreakTime.objects.filter(
            employee=employee,
            date=today,
            is_active=True,
            break_punch_in__isnull=False,
            break_punch_out__isnull=True
        ).first()

        if active_break:
            return Response({
                'error': 'You have an active break. Please punch out first.',
                'has_active_break': True
            }, status=status.HTTP_400_BAD_REQUEST)

        # Create new break entry
        break_time = BreakTime.objects.create(
            employee=employee,
            date=today,
            break_punch_in=now,
            is_active=True
        )

        return Response({
            'message': 'Break punch in successful',
            'break_punch_in': now.strftime('%H:%M:%S'),
            'date': str(today),
            'break_id': break_time.id
        }, status=status.HTTP_200_OK)


class BreakPunchOutView(APIView):
    def post(self, request):
        userid = request.data.get('userid')
        password = request.data.get('password')

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

        # Use Indian timezone
        indian_tz = pytz.timezone('Asia/Kolkata')
        now = datetime.now(indian_tz)
        today = now.date()

        # Find the most recent active break
        active_break = BreakTime.objects.filter(
            employee=employee,
            date=today,
            is_active=True,
            break_punch_in__isnull=False,
            break_punch_out__isnull=True
        ).order_by('-break_punch_in').first()

        if not active_break:
            return Response({
                'error': 'No active break found to punch out',
                'has_active_break': False
            }, status=status.HTTP_400_BAD_REQUEST)

        # Update break with punch out time
        active_break.break_punch_out = now
        active_break.is_active = False
        active_break.save()

        # Calculate break duration
        duration = active_break.break_punch_out - active_break.break_punch_in
        duration_str = str(duration).split('.')[0]  # Format as HH:MM:SS

        return Response({
            'message': 'Break punch out successful',
            'break_punch_out': now.strftime('%H:%M:%S'),
            'break_punch_in': active_break.break_punch_in.astimezone(indian_tz).strftime('%H:%M:%S'),
            'duration': duration_str,
            'date': str(today),
            'break_id': active_break.id
        }, status=status.HTTP_200_OK)


class BreakStatusView(APIView):
    def post(self, request):
        userid = request.data.get('userid')
        password = request.data.get('password')

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

        # Use Indian timezone
        indian_tz = pytz.timezone('Asia/Kolkata')
        now = datetime.now(indian_tz)
        today = now.date()

        # Check for active break
        active_break = BreakTime.objects.filter(
            employee=employee,
            date=today,
            is_active=True,
            break_punch_in__isnull=False,
            break_punch_out__isnull=True
        ).order_by('-break_punch_in').first()

        # Get all breaks for today
        all_breaks_today = BreakTime.objects.filter(
            employee=employee,
            date=today
        ).order_by('-break_punch_in')

        break_list = []
        for break_time in all_breaks_today:
            break_data = {
                'break_id': break_time.id,
                'punch_in': break_time.break_punch_in.astimezone(indian_tz).strftime('%H:%M:%S') if break_time.break_punch_in else None,
                'punch_out': break_time.break_punch_out.astimezone(indian_tz).strftime('%H:%M:%S') if break_time.break_punch_out else None,
                'is_active': break_time.is_active
            }
            
            # Calculate duration if both punch in and out exist
            if break_time.break_punch_in and break_time.break_punch_out:
                duration = break_time.break_punch_out - break_time.break_punch_in
                break_data['duration'] = str(duration).split('.')[0]
            else:
                break_data['duration'] = None
                
            break_list.append(break_data)

        response_data = {
            'has_active_break': active_break is not None,
            'can_punch_in': active_break is None,
            'can_punch_out': active_break is not None,
            'breaks_today': break_list,
            'total_breaks_today': len(break_list),
            'current_break_in': active_break.break_punch_in.astimezone(indian_tz).strftime('%H:%M:%S') if active_break else None,
            'date': str(today)
        }

        return Response(response_data, status=status.HTTP_200_OK)
    



    # http://localhost:8000/flutter/break-punch-in/                 break-punch-in

    # http://localhost:8000/flutter/break-punch-out/                break-punch-out

    # http://localhost:8000/flutter/break-status/                   break-status


    