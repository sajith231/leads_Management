from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import UserLoginSerializer
from django.views.decorators.csrf import csrf_exempt
import calendar


class UserLoginView(APIView):
    def post(self, request):
        serializer = UserLoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            
            # Build image URL if image exists
            image_url = None
            if user.image:
                image_url = request.build_absolute_uri(user.image.url)
            
            return Response({
                'userid': user.userid,
                'name': user.name,
                'user_level': user.get_user_level_display(),
                'status': user.status,
                'image': user.image.url if user.image else None,
                'image_url': image_url,
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
        serializer = UserSerializer(users, many=True, context={'request': request})
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





from rest_framework.decorators import api_view
from django.http import JsonResponse
from app1.models import Attendance, Employee, User
from .serializers import AttendanceMonthlyQuerySerializer, AttendanceDetailSerializer
from datetime import datetime, timedelta
import calendar

from rest_framework.decorators import api_view
from django.http import JsonResponse
from app1.models import Attendance, Employee, User
from .serializers import AttendanceMonthlyQuerySerializer, AttendanceDetailSerializer
from datetime import datetime, timedelta
import calendar

@api_view(['GET'])
def get_monthly_attendance(request):
    """
    Get attendance records for a specific month and year for a user
    URL: /flutter/attendance/monthly/
    Query params: userid, password, month, year
    """
    serializer = AttendanceMonthlyQuerySerializer(data=request.GET)
    if not serializer.is_valid():
        return JsonResponse({'success': False, 'error': serializer.errors}, status=400)

    data = serializer.validated_data
    userid = data['userid']
    password = data['password']
    month = data['month']
    year = data['year']

    # Authenticate user
    try:
        user = User.objects.get(userid=userid, password=password, is_active=True)
        employee = Employee.objects.get(user=user)
    except (User.DoesNotExist, Employee.DoesNotExist):
        return JsonResponse({'success': False, 'error': 'Invalid credentials'}, status=401)

    # Get first and last day of the month
    first_day = datetime(year, month, 1).date()
    last_day = datetime(year, month, calendar.monthrange(year, month)[1]).date()
    total_days_in_month = calendar.monthrange(year, month)[1]

    # Get attendance records for the month
    attendance_records = Attendance.objects.filter(
        employee=employee,
        date__range=[first_day, last_day]
    ).order_by('date')

    # Create a dictionary for quick lookup
    attendance_dict = {record.date: record for record in attendance_records}

    # Create complete month data with all days
    complete_month_data = []
    present_days = 0
    full_days = 0
    half_days = 0
    leave_days = 0
    absent_days = 0
    total_minutes = 0

    for day in range(1, total_days_in_month + 1):
        current_date = datetime(year, month, day).date()
        day_name = current_date.strftime('%A')
        
        if current_date in attendance_dict:
            # Attendance record exists
            record = attendance_dict[current_date]
            
            # Calculate working hours for this day
            working_hours = None
            if record.punch_in and record.punch_out:
                duration = record.punch_out - record.punch_in
                day_minutes = int(duration.total_seconds() / 60)
                total_minutes += day_minutes
                hours = day_minutes // 60
                minutes = day_minutes % 60
                working_hours = f"{hours:02d}:{minutes:02d}"
            
            day_data = {
                'date': current_date.strftime('%Y-%m-%d'),
                'date_formatted': current_date.strftime('%d-%m-%Y'),
                'day': day,
                'day_name': day_name,
                'status': record.status,
                'punch_in': record.punch_in.isoformat() if record.punch_in else None,
                'punch_out': record.punch_out.isoformat() if record.punch_out else None,
                'punch_in_time': record.punch_in.strftime('%H:%M:%S') if record.punch_in else None,
                'punch_out_time': record.punch_out.strftime('%H:%M:%S') if record.punch_out else None,
                'punch_in_location': record.punch_in_location,
                'punch_out_location': record.punch_out_location,
                'working_hours': working_hours,
                'verified': record.verified,
                'note': record.note,
                'has_record': True
            }
            
            # Count statistics
            if record.status in ['full', 'half']:
                present_days += 1
            if record.status == 'full':
                full_days += 1
            elif record.status == 'half':
                half_days += 1
            elif record.status == 'leave':
                leave_days += 1
            elif record.status == 'initial':
                absent_days += 1
                
        else:
            # No attendance record for this day
            day_data = {
                'date': current_date.strftime('%Y-%m-%d'),
                'date_formatted': current_date.strftime('%d-%m-%Y'),
                'day': day,
                'day_name': day_name,
                'status': 'no_record',
                'punch_in': None,
                'punch_out': None,
                'punch_in_time': None,
                'punch_out_time': None,
                'punch_in_location': None,
                'punch_out_location': None,
                'working_hours': None,
                'verified': False,
                'note': None,
                'has_record': False
            }
            absent_days += 1
        
        complete_month_data.append(day_data)

    # Calculate total working hours
    total_working_hours = total_minutes // 60
    remaining_minutes = total_minutes % 60

    response_data = {
        'success': True,
        'employee_name': employee.name,
        'month': month,
        'year': year,
        'month_name': calendar.month_name[month],
        'summary': {
            'total_days_in_month': total_days_in_month,
            'total_attendance_records': len(attendance_records),
            'present_days': present_days,
            'full_days': full_days,
            'half_days': half_days,
            'leave_days': leave_days,
            'absent_days': absent_days,
            'no_record_days': total_days_in_month - len(attendance_records),
            'total_working_hours': f"{total_working_hours:02d}:{remaining_minutes:02d}",
            'attendance_percentage': round((present_days / total_days_in_month) * 100, 2) if total_days_in_month > 0 else 0
        },
        'attendance_records': complete_month_data
    }

    return JsonResponse(response_data, status=200)

# Alternative POST method (if you prefer POST over GET)
@csrf_exempt
@api_view(['POST'])
def get_monthly_attendance_post(request):
    """
    Get attendance records for a specific month and year for a user (POST method)
    URL: /flutter/attendance/monthly-post/
    POST body: {"userid": "", "password": "", "month": 7, "year": 2025}
    """
    serializer = AttendanceMonthlyQuerySerializer(data=request.data)
    if not serializer.is_valid():
        return JsonResponse({'success': False, 'error': serializer.errors}, status=400)

    data = serializer.validated_data
    userid = data['userid']
    password = data['password']
    month = data['month']
    year = data['year']

    # Authenticate user
    try:
        user = User.objects.get(userid=userid, password=password, is_active=True)
        employee = Employee.objects.get(user=user)
    except (User.DoesNotExist, Employee.DoesNotExist):
        return JsonResponse({'success': False, 'error': 'Invalid credentials'}, status=401)

    # Get first and last day of the month
    first_day = datetime(year, month, 1).date()
    last_day = datetime(year, month, calendar.monthrange(year, month)[1]).date()
    total_days_in_month = calendar.monthrange(year, month)[1]

    # Get attendance records for the month
    attendance_records = Attendance.objects.filter(
        employee=employee,
        date__range=[first_day, last_day]
    ).order_by('date')

    # Create a dictionary for quick lookup
    attendance_dict = {record.date: record for record in attendance_records}

    # Create complete month data with all days
    complete_month_data = []
    present_days = 0
    full_days = 0
    half_days = 0
    leave_days = 0
    absent_days = 0
    total_minutes = 0

    for day in range(1, total_days_in_month + 1):
        current_date = datetime(year, month, day).date()
        day_name = current_date.strftime('%A')
        
        if current_date in attendance_dict:
            # Attendance record exists
            record = attendance_dict[current_date]
            
            # Calculate working hours for this day
            working_hours = None
            if record.punch_in and record.punch_out:
                duration = record.punch_out - record.punch_in
                day_minutes = int(duration.total_seconds() / 60)
                total_minutes += day_minutes
                hours = day_minutes // 60
                minutes = day_minutes % 60
                working_hours = f"{hours:02d}:{minutes:02d}"
            
            day_data = {
                'date': current_date.strftime('%Y-%m-%d'),
                'date_formatted': current_date.strftime('%d-%m-%Y'),
                'day': day,
                'day_name': day_name,
                'status': record.status,
                'punch_in': record.punch_in.isoformat() if record.punch_in else None,
                'punch_out': record.punch_out.isoformat() if record.punch_out else None,
                'punch_in_time': record.punch_in.strftime('%H:%M:%S') if record.punch_in else None,
                'punch_out_time': record.punch_out.strftime('%H:%M:%S') if record.punch_out else None,
                'punch_in_location': record.punch_in_location,
                'punch_out_location': record.punch_out_location,
                'working_hours': working_hours,
                'verified': record.verified,
                'note': record.note,
                'has_record': True
            }
            
            # Count statistics
            if record.status in ['full', 'half']:
                present_days += 1
            if record.status == 'full':
                full_days += 1
            elif record.status == 'half':
                half_days += 1
            elif record.status == 'leave':
                leave_days += 1
            elif record.status == 'initial':
                absent_days += 1
                
        else:
            # No attendance record for this day
            day_data = {
                'date': current_date.strftime('%Y-%m-%d'),
                'date_formatted': current_date.strftime('%d-%m-%Y'),
                'day': day,
                'day_name': day_name,
                'status': 'no_record',
                'punch_in': None,
                'punch_out': None,
                'punch_in_time': None,
                'punch_out_time': None,
                'punch_in_location': None,
                'punch_out_location': None,
                'working_hours': None,
                'verified': False,
                'note': None,
                'has_record': False
            }
            absent_days += 1
        
        complete_month_data.append(day_data)

    # Calculate total working hours
    total_working_hours = total_minutes // 60
    remaining_minutes = total_minutes % 60

    response_data = {
        'success': True,
        'employee_name': employee.name,
        'month': month,
        'year': year,
        'month_name': calendar.month_name[month],
        'summary': {
            'total_days_in_month': total_days_in_month,
            'total_attendance_records': len(attendance_records),
            'present_days': present_days,
            'full_days': full_days,
            'half_days': half_days,
            'leave_days': leave_days,
            'absent_days': absent_days,
            'no_record_days': total_days_in_month - len(attendance_records),
            'total_working_hours': f"{total_working_hours:02d}:{remaining_minutes:02d}",
            'attendance_percentage': round((present_days / total_days_in_month) * 100, 2) if total_days_in_month > 0 else 0
        },
        'attendance_records': complete_month_data
    }

    return JsonResponse(response_data, status=200)






# URL: http://127.0.0.1:8000/flutter/attendance/monthly/?userid=2&password=2&month=7&year=2025
# Method: GET



# URL: http://127.0.0.1:8000/flutter/attendance/monthly-post/
# Method: POST
# Body: 
# {
#     "userid": "2",
#     "password": "2",
#     "month": 7,
#     "year": 2025
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


    # {
    # "userid":"2",
    # "password":"2"
    # }







import json
import requests
from datetime import datetime, timedelta
from django.http import JsonResponse
from django.utils import timezone
from app1.models import LeaveRequest, Employee, Attendance, User
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator


# ---------- CREATE ----------
@csrf_exempt 
def create_leave_request(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            userid   = data.get('userid')
            password = data.get('password')
            try:
                user = User.objects.get(userid=userid, password=password)
                employee = Employee.objects.get(user=user)
            except (User.DoesNotExist, Employee.DoesNotExist):
                return JsonResponse({'success': False, 'error': 'Invalid credentials'})

            start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
            end_date   = datetime.strptime(data['end_date'],   '%Y-%m-%d').date()

            leave_request = LeaveRequest.objects.create(
                employee   = employee,
                start_date = start_date,
                end_date   = end_date,
                leave_type = data['leave_type'],
                reason     = data['reason'],
                status     = 'pending'
            )

            # Optional WhatsApp notification
            phone_numbers = ["9946545535", "7593820007", "7593820005", "9846754998"]
            msg = (f"New leave request from {employee.name}. "
                   f"{start_date:%d-%m-%Y} → {end_date:%d-%m-%Y} "
                   f"Type: {leave_request.get_leave_type_display()} "
                   f"Reason: {data['reason']}")
            for number in phone_numbers:
                _send_whatsapp(number, msg)

            return JsonResponse({'success': True, 'message': 'Leave request submitted'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Only POST allowed'})

# ---------- LIST ----------
def get_leave_requests(request):
    from .serializers import LeaveRequestListQuerySerializer

    serializer = LeaveRequestListQuerySerializer(data=request.GET)
    if not serializer.is_valid():
        return JsonResponse({'success': False, 'error': serializer.errors})

    cleaned = serializer.validated_data
    userid   = cleaned['userid']
    password = cleaned['password']
    status_filter = cleaned.get('status')

    try:
        user = User.objects.get(userid=userid, password=password)
        employee = Employee.objects.get(user=user)
    except (User.DoesNotExist, Employee.DoesNotExist):
        return JsonResponse({'success': False, 'error': 'Invalid credentials'})

    qs = LeaveRequest.objects.filter(employee=employee)
    if status_filter:
        qs = qs.filter(status=status_filter)
    qs = qs.order_by('-created_at')

    payload = [{
        'id': lr.id,
        'start_date': lr.start_date.strftime('%d-%m-%Y'),
        'end_date':   lr.end_date.strftime('%d-%m-%Y'),
        'leave_type': lr.get_leave_type_display(),
        'reason':     lr.reason,
        'status':     lr.status
    } for lr in qs]
    return JsonResponse({'leave_requests': payload})

# ---------- DELETE ----------
@csrf_exempt
def delete_leave_request(request):
    from .serializers import LeaveRequestDeleteSerializer

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            serializer = LeaveRequestDeleteSerializer(data=data)
            if not serializer.is_valid():
                return JsonResponse({'success': False, 'error': serializer.errors})

            cleaned = serializer.validated_data
            userid     = cleaned['userid']
            password   = cleaned['password']
            request_id = cleaned['request_id']

            try:
                user = User.objects.get(userid=userid, password=password)
                employee = Employee.objects.get(user=user)
            except (User.DoesNotExist, Employee.DoesNotExist):
                return JsonResponse({'success': False, 'error': 'Invalid credentials'})

            lr = LeaveRequest.objects.get(
                id=request_id,
                employee=employee,
                status='pending'
            )
            lr.delete()
            return JsonResponse({'success': True})
        except LeaveRequest.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Leave request not found or not in pending'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Only POST allowed'})

# ---------- helper ----------
def _send_whatsapp(phone, message):
    secret  = "7b8ae820ecb39f8d173d57b51e1fce4c023e359e"
    account = "1756959119812b4ba287f5ee0bc9d43bbf5bbe87fb68b9118fcf1af"
    url = (
        f"https://app.dxing.in/api/send/whatsapp?secret={secret}&account={account}"
        f"&recipient={phone}&type=text&message={message}&priority=1"
    )
    requests.get(url)








# http://127.0.0.1:8000/flutter/leave/create/       POST CREATE LEAVE REQUEST



# {
#   "userid": "2",
#   "password": "2",
#   "start_date": "2025-07-20",
#   "end_date": "2025-07-20",
#   "leave_type": "full_day",
#   "reason": "TEST TEST TEST TEST"
# }




# http://127.0.0.1:8000/flutter/leave/list/?userid=2&password=2         GET ALL LEAVE REQUEST


#http://127.0.0.1:8000/flutter/leave/delete/                            POST DELETE LEAVE REQUEST


# {
#   "userid": "2",
#   "password": "2",
#   "request_id": 12
# }






import json
import requests
from datetime import datetime
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework import status
from rest_framework.decorators import api_view
from app1.models import Employee, User, LateRequest, EarlyRequest
from .serializers import (
    LateRequestCreateSerializer, LateRequestListQuerySerializer, LateRequestDeleteSerializer,
    EarlyRequestCreateSerializer, EarlyRequestListQuerySerializer, EarlyRequestDeleteSerializer,
)

# ---------- HELPERS ----------
def _auth_user(userid, password):
    try:
        user = User.objects.get(userid=userid, password=password)
        return Employee.objects.get(user=user)
    except (User.DoesNotExist, Employee.DoesNotExist):
        return None

def _send_whatsapp(phone, message):
    secret  = "7b8ae820ecb39f8d173d57b51e1fce4c023e359e"
    account = "1756959119812b4ba287f5ee0bc9d43bbf5bbe87fb68b9118fcf1af"
    url = f"https://app.dxing.in/api/send/whatsapp?secret={secret}&account={account}&recipient={phone}&type=text&message={message}&priority=1"
    requests.get(url)


# ---------- LATE ----------
@csrf_exempt
@api_view(['POST'])
def create_late_request(request):
    ser = LateRequestCreateSerializer(data=request.data)
    if not ser.is_valid():
        return JsonResponse({'success': False, 'error': ser.errors}, status=400)

    data = ser.validated_data
    emp = _auth_user(data['userid'], data['password'])
    if not emp:
        return JsonResponse({'success': False, 'error': 'Invalid credentials'}, status=401)

    late = LateRequest.objects.create(
        employee=emp,
        date=data['date'],
        delay_time=data['delay_time'],
        reason=data['reason'],
        status='pending'
    )

    # WhatsApp to managers
    phones = ["9946545535", "7593820007", "7593820005", "9846754998"]
    msg = (f"New late request from {emp.name}. "
           f"Date: {late.date:%d-%m-%Y}, Delay: {late.delay_time}, Reason: {late.reason}")
    for p in phones:
        _send_whatsapp(p, msg)

    return JsonResponse({'success': True, 'message': 'Late request submitted'}, status=200)

@api_view(['GET'])
def get_late_requests(request):
    ser = LateRequestListQuerySerializer(data=request.GET)
    if not ser.is_valid():
        return JsonResponse({'success': False, 'error': ser.errors}, status=400)

    data = ser.validated_data
    emp = _auth_user(data['userid'], data['password'])
    if not emp:
        return JsonResponse({'success': False, 'error': 'Invalid credentials'}, status=401)

    qs = LateRequest.objects.filter(employee=emp)
    if data.get('status'):
        qs = qs.filter(status=data['status'])
    qs = qs.order_by('-created_at')

    payload = [{
        'id': lr.id,
        'employee_name': lr.employee.name,
        'date': lr.date.strftime('%Y-%m-%d'),
        'delay_time': lr.delay_time,
        'reason': lr.reason,
        'status': lr.status,
        'created_at': lr.created_at.strftime('%Y-%m-%d %H:%M')
    } for lr in qs]

    return JsonResponse({'success': True, 'late_requests': payload}, status=200)

@csrf_exempt
@api_view(['POST'])
def delete_late_request(request):
    ser = LateRequestDeleteSerializer(data=request.data)
    if not ser.is_valid():
        return JsonResponse({'success': False, 'error': ser.errors}, status=400)

    data = ser.validated_data
    emp = _auth_user(data['userid'], data['password'])
    if not emp:
        return JsonResponse({'success': False, 'error': 'Invalid credentials'}, status=401)

    try:
        LateRequest.objects.get(id=data['request_id'], employee=emp, status='pending').delete()
    except LateRequest.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Request not found or not pending'}, status=404)

    return JsonResponse({'success': True}, status=200)

# ---------- EARLY ----------
@csrf_exempt
@api_view(['POST'])
def create_early_request(request):
    ser = EarlyRequestCreateSerializer(data=request.data)
    if not ser.is_valid():
        return JsonResponse({'success': False, 'error': ser.errors}, status=400)

    data = ser.validated_data
    emp = _auth_user(data['userid'], data['password'])
    if not emp:
        return JsonResponse({'success': False, 'error': 'Invalid credentials'}, status=401)

    early = EarlyRequest.objects.create(
        employee=emp,
        date=data['date'],
        early_time=data['early_time'],
        reason=data['reason'],
        status='pending'
    )

    phones = ["9946545535", "7593820007", "7593820005", "9846754998"]
    msg = (f"New early request from {emp.name}. "
           f"Date: {early.date:%d-%m-%Y}, Early Time: {early.early_time}, Reason: {early.reason}")
    for p in phones:
        _send_whatsapp(p, msg)

    return JsonResponse({'success': True, 'message': 'Early request submitted'}, status=200)

@api_view(['GET'])
def get_early_requests(request):
    ser = EarlyRequestListQuerySerializer(data=request.GET)
    if not ser.is_valid():
        return JsonResponse({'success': False, 'error': ser.errors}, status=400)

    data = ser.validated_data
    emp = _auth_user(data['userid'], data['password'])
    if not emp:
        return JsonResponse({'success': False, 'error': 'Invalid credentials'}, status=401)

    qs = EarlyRequest.objects.filter(employee=emp)
    if data.get('status'):
        qs = qs.filter(status=data['status'])
    qs = qs.order_by('-created_at')

    payload = [{
        'id': er.id,
        'employee_name': er.employee.name,
        'date': er.date.strftime('%Y-%m-%d'),
        'early_time': er.early_time.strftime('%H:%M'),
        'reason': er.reason,
        'status': er.status,
        'created_at': er.created_at.strftime('%Y-%m-%d %H:%M')
    } for er in qs]

    return JsonResponse({'success': True, 'early_requests': payload}, status=200)

@csrf_exempt
@api_view(['POST'])
def delete_early_request(request):
    ser = EarlyRequestDeleteSerializer(data=request.data)
    if not ser.is_valid():
        return JsonResponse({'success': False, 'error': ser.errors}, status=400)

    data = ser.validated_data
    emp = _auth_user(data['userid'], data['password'])
    if not emp:
        return JsonResponse({'success': False, 'error': 'Invalid credentials'}, status=401)

    try:
        EarlyRequest.objects.get(id=data['request_id'], employee=emp, status='pending').delete()
    except EarlyRequest.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Request not found or not pending'}, status=404)

    return JsonResponse({'success': True}, status=200)







# http://127.0.0.1:8000/flutter/late/create/
# {
#   "userid": "2",
#   "password": "2",
#   "date": "2025-07-25",
#   "delay_time": "20 minutes",
#   "reason": "TEST TEST"
# }


# LATE GET

# http://127.0.0.1:8000/flutter/late/list/?userid=2&password=2



# DELETE

# http://127.0.0.1:8000/flutter/late/delete/



# {
#   "userid": "2",
#   "password": "2",
#   "request_id": 7
# }






#EARLY CREATE
# http://127.0.0.1:8000/flutter/early/create/


# {
#   "userid": "2",
#   "password": "2",
#   "date": "2025-07-25",
#   "early_time": "15:00",
#   "reason": "Doctor appointment"
# }




#EARLY GET

# http://127.0.0.1:8000/flutter/early/list/?userid=2&password=2


#EARLT DELETE
# http://127.0.0.1:8000/flutter/early/delete/

# {
#   "userid": "2",
#   "password": "2",
#   "request_id": 3
# }
