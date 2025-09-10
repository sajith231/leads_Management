from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import UserLoginSerializer, UserSerializer, AttendanceSerializer
from app1.models import User, Employee, Attendance, BreakTime, LeaveRequest, LateRequest, EarlyRequest
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from rest_framework.decorators import api_view
from django.utils import timezone
from django.utils.decorators import method_decorator
from datetime import datetime, timedelta
import calendar, pytz, json, requests, urllib.parse

# ---------- WHATSAPP HELPER ----------
def send_whatsapp(phone, message):
    secret  = "7b8ae820ecb39f8d173d57b51e1fce4c023e359e"
    account = "1756959119812b4ba287f5ee0bc9d43bbf5bbe87fb68b9118fcf1af"

    # Ensure phone in international format (prepend 91 if 10-digit)
    if len(phone) == 10 and phone.isdigit():
        phone = "91" + phone

    encoded_msg = urllib.parse.quote(str(message))
    url = (
        f"https://app.dxing.in/api/send/whatsapp?secret={secret}&account={account}"
        f"&recipient={phone}&type=text&message={encoded_msg}&priority=1"
    )
    try:
        response = requests.get(url, timeout=10)
        print("WhatsApp API Response:", response.text)
    except Exception as e:
        print("WhatsApp API Error:", str(e))


# ---------- LOGIN ----------
class UserLoginView(APIView):
    def post(self, request):
        serializer = UserLoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']

            image_url = request.build_absolute_uri(user.image.url) if user.image else None
            return Response({
                'userid': user.userid,
                'name': user.name,
                'user_level': user.get_user_level_display(),
                'status': user.status,
                'image': user.image.url if user.image else None,
                'image_url': image_url,
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ---------- USER LIST ----------
class UserListView(APIView):
    def get(self, request):
        users = User.objects.all()
        serializer = UserSerializer(users, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)


# ---------- ATTENDANCE PUNCH IN ----------
class PunchInView(APIView):
    def post(self, request):
        userid = request.data.get('userid')
        password = request.data.get('password')
        location = request.data.get('location')
        latitude = request.data.get('latitude')
        longitude = request.data.get('longitude')

        try:
            user = User.objects.get(userid=userid, password=password)
            employee = Employee.objects.get(user=user)
        except (User.DoesNotExist, Employee.DoesNotExist):
            return Response({'error': 'Invalid userid or password'}, status=status.HTTP_401_UNAUTHORIZED)

        today = timezone.now().date()
        day_number = today.weekday()

        attendance, created = Attendance.objects.get_or_create(
            employee=employee,
            date=today,
            defaults={'status': 'half', 'day': day_number}
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


# ---------- ATTENDANCE PUNCH OUT ----------
class PunchOutView(APIView):
    def post(self, request):
        userid = request.data.get('userid')
        password = request.data.get('password')
        location = request.data.get('location')
        latitude = request.data.get('latitude')
        longitude = request.data.get('longitude')
        today = timezone.now().date()

        try:
            user = User.objects.get(userid=userid, password=password)
            employee = Employee.objects.get(user=user)
        except (User.DoesNotExist, Employee.DoesNotExist):
            return Response({'error': 'Invalid userid or password'}, status=status.HTTP_401_UNAUTHORIZED)

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


# ---------- MONTHLY ATTENDANCE (GET + POST) ----------
@api_view(['GET'])
def get_monthly_attendance(request):
    from .serializers import AttendanceMonthlyQuerySerializer, AttendanceDetailSerializer

    serializer = AttendanceMonthlyQuerySerializer(data=request.GET)
    if not serializer.is_valid():
        return JsonResponse({'success': False, 'error': serializer.errors}, status=400)

    data = serializer.validated_data
    userid, password, month, year = data['userid'], data['password'], data['month'], data['year']

    try:
        user = User.objects.get(userid=userid, password=password, is_active=True)
        employee = Employee.objects.get(user=user)
    except (User.DoesNotExist, Employee.DoesNotExist):
        return JsonResponse({'success': False, 'error': 'Invalid credentials'}, status=401)

    first_day = datetime(year, month, 1).date()
    last_day = datetime(year, month, calendar.monthrange(year, month)[1]).date()
    total_days_in_month = calendar.monthrange(year, month)[1]

    attendance_records = Attendance.objects.filter(
        employee=employee, date__range=[first_day, last_day]
    ).order_by('date')

    attendance_dict = {record.date: record for record in attendance_records}
    complete_month_data, present_days, full_days, half_days, leave_days, absent_days, total_minutes = [], 0, 0, 0, 0, 0, 0

    for day in range(1, total_days_in_month + 1):
        current_date = datetime(year, month, day).date()
        day_name = current_date.strftime('%A')

        if current_date in attendance_dict:
            record = attendance_dict[current_date]
            working_hours, day_minutes = None, 0
            if record.punch_in and record.punch_out:
                duration = record.punch_out - record.punch_in
                day_minutes = int(duration.total_seconds() / 60)
                total_minutes += day_minutes
                hours, minutes = day_minutes // 60, day_minutes % 60
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

            if record.status in ['full', 'half']: present_days += 1
            if record.status == 'full': full_days += 1
            elif record.status == 'half': half_days += 1
            elif record.status == 'leave': leave_days += 1
            elif record.status == 'initial': absent_days += 1
        else:
            day_data = {
                'date': current_date.strftime('%Y-%m-%d'),
                'date_formatted': current_date.strftime('%d-%m-%Y'),
                'day': day,
                'day_name': day_name,
                'status': 'no_record',
                'punch_in': None, 'punch_out': None,
                'punch_in_time': None, 'punch_out_time': None,
                'punch_in_location': None, 'punch_out_location': None,
                'working_hours': None, 'verified': False, 'note': None,
                'has_record': False
            }
            absent_days += 1

        complete_month_data.append(day_data)

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


@csrf_exempt
@api_view(['POST'])
def get_monthly_attendance_post(request):
    # Reuse the same logic but with POST body
    return get_monthly_attendance(request)


# ---------- BREAK TIME ----------
class BreakPunchInView(APIView):
    def post(self, request):
        userid, password = request.data.get('userid'), request.data.get('password')
        try:
            user = User.objects.get(userid=userid, password=password)
            employee = Employee.objects.get(user=user)
        except (User.DoesNotExist, Employee.DoesNotExist):
            return Response({'error': 'Invalid userid or password'}, status=401)

        indian_tz = pytz.timezone('Asia/Kolkata')
        now = datetime.now(indian_tz)
        today = now.date()

        active_break = BreakTime.objects.filter(employee=employee, date=today, is_active=True,
                                                break_punch_in__isnull=False, break_punch_out__isnull=True).first()
        if active_break:
            return Response({'error': 'You have an active break. Please punch out first.'}, status=400)

        break_time = BreakTime.objects.create(employee=employee, date=today, break_punch_in=now, is_active=True)
        return Response({'message': 'Break punch in successful', 'break_punch_in': now.strftime('%H:%M:%S'),
                         'date': str(today), 'break_id': break_time.id}, status=200)


class BreakPunchOutView(APIView):
    def post(self, request):
        userid, password = request.data.get('userid'), request.data.get('password')
        try:
            user = User.objects.get(userid=userid, password=password)
            employee = Employee.objects.get(user=user)
        except (User.DoesNotExist, Employee.DoesNotExist):
            return Response({'error': 'Invalid userid or password'}, status=401)

        indian_tz = pytz.timezone('Asia/Kolkata')
        now = datetime.now(indian_tz)
        today = now.date()

        active_break = BreakTime.objects.filter(employee=employee, date=today, is_active=True,
                                                break_punch_in__isnull=False, break_punch_out__isnull=True).order_by('-break_punch_in').first()
        if not active_break:
            return Response({'error': 'No active break found to punch out'}, status=400)

        active_break.break_punch_out = now
        active_break.is_active = False
        active_break.save()

        duration = active_break.break_punch_out - active_break.break_punch_in
        duration_str = str(duration).split('.')[0]

        return Response({'message': 'Break punch out successful',
                         'break_punch_out': now.strftime('%H:%M:%S'),
                         'break_punch_in': active_break.break_punch_in.strftime('%H:%M:%S'),
                         'duration': duration_str, 'date': str(today),
                         'break_id': active_break.id}, status=200)


class BreakStatusView(APIView):
    def post(self, request):
        userid, password = request.data.get('userid'), request.data.get('password')
        try:
            user = User.objects.get(userid=userid, password=password)
            employee = Employee.objects.get(user=user)
        except (User.DoesNotExist, Employee.DoesNotExist):
            return Response({'error': 'Invalid userid or password'}, status=401)

        indian_tz = pytz.timezone('Asia/Kolkata')
        now = datetime.now(indian_tz)
        today = now.date()

        active_break = BreakTime.objects.filter(employee=employee, date=today, is_active=True,
                                                break_punch_in__isnull=False, break_punch_out__isnull=True).first()
        all_breaks_today = BreakTime.objects.filter(employee=employee, date=today).order_by('-break_punch_in')

        break_list = []
        for b in all_breaks_today:
            data = {
                'break_id': b.id,
                'punch_in': b.break_punch_in.strftime('%H:%M:%S') if b.break_punch_in else None,
                'punch_out': b.break_punch_out.strftime('%H:%M:%S') if b.break_punch_out else None,
                'is_active': b.is_active,
                'duration': str((b.break_punch_out - b.break_punch_in)).split('.')[0] if b.break_punch_in and b.break_punch_out else None
            }
            break_list.append(data)

        return Response({'has_active_break': active_break is not None,
                         'can_punch_in': active_break is None,
                         'can_punch_out': active_break is not None,
                         'breaks_today': break_list, 'total_breaks_today': len(break_list),
                         'current_break_in': active_break.break_punch_in.strftime('%H:%M:%S') if active_break else None,
                         'date': str(today)}, status=200)


# ---------- LEAVE REQUEST ----------
@csrf_exempt
def create_leave_request(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            userid, password = data.get('userid'), data.get('password')

            try:
                user = User.objects.get(userid=userid, password=password)
                employee = Employee.objects.get(user=user)
            except (User.DoesNotExist, Employee.DoesNotExist):
                return JsonResponse({'success': False, 'error': 'Invalid credentials'})

            start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
            end_date = datetime.strptime(data['end_date'], '%Y-%m-%d').date()

            leave_request = LeaveRequest.objects.create(
                employee=employee, start_date=start_date, end_date=end_date,
                leave_type=data['leave_type'], reason=data['reason'], status='pending'
            )

            phones = ["9946545535", "7593820007", "7593820005", "9846754998"]
            msg = f"New leave request from {employee.name}. {start_date:%d-%m-%Y} → {end_date:%d-%m-%Y} Type: {leave_request.get_leave_type_display()} Reason: {data['reason']}"
            for p in phones:
                send_whatsapp(p, msg)

            return JsonResponse({'success': True, 'message': 'Leave request submitted'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Only POST allowed'})


def get_leave_requests(request):
    from .serializers import LeaveRequestListQuerySerializer
    ser = LeaveRequestListQuerySerializer(data=request.GET)
    if not ser.is_valid():
        return JsonResponse({'success': False, 'error': ser.errors})

    cleaned = ser.validated_data
    userid, password, status_filter = cleaned['userid'], cleaned['password'], cleaned.get('status')

    try:
        user = User.objects.get(userid=userid, password=password)
        employee = Employee.objects.get(user=user)
    except (User.DoesNotExist, Employee.DoesNotExist):
        return JsonResponse({'success': False, 'error': 'Invalid credentials'})

    qs = LeaveRequest.objects.filter(employee=employee)
    if status_filter:
        qs = qs.filter(status=status_filter)
    qs = qs.order_by('-created_at')

    payload = [{'id': lr.id, 'start_date': lr.start_date.strftime('%d-%m-%Y'),
                'end_date': lr.end_date.strftime('%d-%m-%Y'),
                'leave_type': lr.get_leave_type_display(),
                'reason': lr.reason, 'status': lr.status} for lr in qs]
    return JsonResponse({'leave_requests': payload})


@csrf_exempt
def delete_leave_request(request):
    from .serializers import LeaveRequestDeleteSerializer
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            ser = LeaveRequestDeleteSerializer(data=data)
            if not ser.is_valid():
                return JsonResponse({'success': False, 'error': ser.errors})

            cleaned = ser.validated_data
            userid, password, request_id = cleaned['userid'], cleaned['password'], cleaned['request_id']

            try:
                user = User.objects.get(userid=userid, password=password)
                employee = Employee.objects.get(user=user)
            except (User.DoesNotExist, Employee.DoesNotExist):
                return JsonResponse({'success': False, 'error': 'Invalid credentials'})

            LeaveRequest.objects.get(id=request_id, employee=employee, status='pending').delete()
            return JsonResponse({'success': True})
        except LeaveRequest.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Leave request not found or not pending'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Only POST allowed'})


# ---------- LATE REQUEST ----------
def _auth_user(userid, password):
    try:
        user = User.objects.get(userid=userid, password=password)
        return Employee.objects.get(user=user)
    except (User.DoesNotExist, Employee.DoesNotExist):
        return None


@csrf_exempt
@api_view(['POST'])
def create_late_request(request):
    from .serializers import LateRequestCreateSerializer
    ser = LateRequestCreateSerializer(data=request.data)
    if not ser.is_valid():
        return JsonResponse({'success': False, 'error': ser.errors}, status=400)

    data = ser.validated_data
    emp = _auth_user(data['userid'], data['password'])
    if not emp:
        return JsonResponse({'success': False, 'error': 'Invalid credentials'}, status=401)

    late = LateRequest.objects.create(employee=emp, date=data['date'],
                                      delay_time=data['delay_time'], reason=data['reason'], status='pending')

    phones = ["9946545535", "7593820007", "7593820005", "9846754998","8129191379","9061947005"]
    msg = f"New late request from {emp.name}. Date: {late.date:%d-%m-%Y}, Delay: {late.delay_time}, Reason: {late.reason}"
    for p in phones:
        send_whatsapp(p, msg)

    return JsonResponse({'success': True, 'message': 'Late request submitted'}, status=200)


@api_view(['GET'])
def get_late_requests(request):
    from .serializers import LateRequestListQuerySerializer
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

    payload = [{'id': lr.id, 'employee_name': lr.employee.name, 'date': lr.date.strftime('%Y-%m-%d'),
                'delay_time': lr.delay_time, 'reason': lr.reason, 'status': lr.status,
                'created_at': lr.created_at.strftime('%Y-%m-%d %H:%M')} for lr in qs]
    return JsonResponse({'success': True, 'late_requests': payload}, status=200)


@csrf_exempt
@api_view(['POST'])
def delete_late_request(request):
    from .serializers import LateRequestDeleteSerializer
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


# ---------- EARLY REQUEST ----------
@csrf_exempt
@api_view(['POST'])
def create_early_request(request):
    from .serializers import EarlyRequestCreateSerializer
    ser = EarlyRequestCreateSerializer(data=request.data)
    if not ser.is_valid():
        return JsonResponse({'success': False, 'error': ser.errors}, status=400)

    data = ser.validated_data
    emp = _auth_user(data['userid'], data['password'])
    if not emp:
        return JsonResponse({'success': False, 'error': 'Invalid credentials'}, status=401)

    early = EarlyRequest.objects.create(employee=emp, date=data['date'],
                                        early_time=data['early_time'], reason=data['reason'], status='pending')

    phones = ["9946545535", "7593820007", "7593820005", "9846754998","8129191379","9061947005"]
    msg = f"New early request from {emp.name}. Date: {early.date:%d-%m-%Y}, Early Time: {early.early_time}, Reason: {early.reason}"
    for p in phones:
        send_whatsapp(p, msg)

    return JsonResponse({'success': True, 'message': 'Early request submitted'}, status=200)


@api_view(['GET'])
def get_early_requests(request):
    from .serializers import EarlyRequestListQuerySerializer
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

    payload = [{'id': er.id, 'employee_name': er.employee.name, 'date': er.date.strftime('%Y-%m-%d'),
                'early_time': er.early_time.strftime('%H:%M'), 'reason': er.reason,
                'status': er.status, 'created_at': er.created_at.strftime('%Y-%m-%d %H:%M')} for er in qs]
    return JsonResponse({'success': True, 'early_requests': payload}, status=200)


@csrf_exempt
@api_view(['POST'])
def delete_early_request(request):
    from .serializers import EarlyRequestDeleteSerializer
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
