import json, requests
from datetime import datetime, timedelta
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.shortcuts import get_object_or_404
from app1.models import Employee, Attendance  # existing
from .models import WorkFromHomeRequest

ADMIN_NUMBERS = ["9061947005"]
WA_SECRET = "7b8ae820ecb39f8d173d57b51e1fce4c023e359e"
WA_ACCOUNT = "1756959119812b4ba287f5ee0bc9d43bbf5bbe87fb68b9118fcf1af"

def send_whatsapp(to, message):
    encoded = requests.utils.quote(message)
    url = (f"https://app.dxing.in/api/send/whatsapp?"
           f"secret={WA_SECRET}&account={WA_ACCOUNT}&recipient={to}"
           f"&type=text&message={encoded}&priority=1")
    try:
        requests.get(url, timeout=10)
    except requests.exceptions.RequestException:
        pass

@login_required
def create_wfh_request(request):
    if request.method != "POST":
        return JsonResponse({'success': False, 'error': 'Invalid request method'})
    try:
        data = json.loads(request.body)
        emp = Employee.objects.get(user_id=request.session.get('custom_user_id'))
        start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
        end_date   = datetime.strptime(data['end_date'],   '%Y-%m-%d').date()
        wfh = WorkFromHomeRequest.objects.create(
            employee=emp, start_date=start_date, end_date=end_date,
            reason=data['reason'], status='pending'
        )
        msg = (f"New WFH request from {emp.name}.\n"
               f"From: {start_date.strftime('%d-%m-%Y')} To: {end_date.strftime('%d-%m-%Y')}\n"
               f"Reason: {wfh.reason}")
        for n in ADMIN_NUMBERS: send_whatsapp(n, msg)
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
def list_wfh_requests(request):
    """Admins see all; users see their own; optional ?status=pending/approved/rejected"""
    status_filter = request.GET.get('status')
    if request.user.is_superuser or request.session.get('user_level') == 'normal':
        qs = WorkFromHomeRequest.objects.select_related('employee').order_by('-created_at')
    else:
        emp = Employee.objects.get(user_id=request.session.get('custom_user_id'))
        qs = WorkFromHomeRequest.objects.filter(employee=emp).select_related('employee').order_by('-created_at')
    if status_filter:
        qs = qs.filter(status=status_filter)
    data = [{
        'id': r.id,
        'employee_name': r.employee.name,
        'start_date': r.start_date.strftime('%d-%m-%Y'),
        'end_date': r.end_date.strftime('%d-%m-%Y'),
        'reason': r.reason,
        'status': r.status,
        'created_at': r.created_at.strftime('%d-%m-%Y')
    } for r in qs]
    return JsonResponse({'success': True, 'wfh_requests': data})

@login_required
def process_wfh_request(request):
    if request.method != "POST":
        return JsonResponse({'success': False, 'error': 'Invalid request method'})
    try:
        data = json.loads(request.body)
        wfh = get_object_or_404(WorkFromHomeRequest, id=data['request_id'])
        action = data['action']  # 'approve' or 'reject'

        # Who is approving/rejecting (build friendly name like your leave/late code)
        approver = (getattr(getattr(request, 'user', None), 'name', None) or
                    (request.user.get_full_name() if hasattr(request.user,'get_full_name') else None) or
                    getattr(request.user, 'username', None) or "Admin")

        if action == 'approve':
            wfh.status = 'approved'
            cur = wfh.start_date
            while cur <= wfh.end_date:
                att, created = Attendance.objects.get_or_create(
                    employee=wfh.employee, date=cur,
                    defaults={'day': cur.day, 'status': 'work_from_home'}
                )
                if not created:
                    att.status = 'work_from_home'
                    att.save()
                cur += timedelta(days=1)
            msg = (f"✅ Your WFH request ({wfh.start_date.strftime('%d-%m-%Y')} "
                   f"to {wfh.end_date.strftime('%d-%m-%Y')}) has been approved.\n"
                   f"📝 Reason: {wfh.reason}\n👤 Approved By: {approver}")
        elif action == 'reject':
            wfh.status = 'rejected'
            cur = wfh.start_date
            while cur <= wfh.end_date:
                Attendance.objects.filter(employee=wfh.employee, date=cur, status='work_from_home').delete()
                cur += timedelta(days=1)
            msg = (f"❌ Your WFH request ({wfh.start_date.strftime('%d-%m-%Y')} "
                   f"to {wfh.end_date.strftime('%d-%m-%Y')}) has been rejected.\n"
                   f"📝 Reason: {wfh.reason}\n👤 Rejected By: {approver}")
        else:
            return JsonResponse({'success': False, 'error': 'Invalid action'})

        wfh.processed_by = request.user
        wfh.processed_at = timezone.now()
        wfh.save()

        # notify employee
        employee_phone = getattr(wfh.employee, 'phone_personal', None) or getattr(wfh.employee, 'phone_number', None)
        if employee_phone: send_whatsapp(str(employee_phone), msg)

        return JsonResponse({
            'success': True,
            'action': action,
            'employee_id': wfh.employee.id,
            'start_date': wfh.start_date.strftime('%Y-%m-%d'),
            'end_date':   wfh.end_date.strftime('%Y-%m-%d')
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
def delete_wfh_request(request):
    if request.method != "POST":
        return JsonResponse({'success': False, 'error': 'Invalid request method'})
    try:
        data = json.loads(request.body)
        wfh = get_object_or_404(WorkFromHomeRequest, id=data['request_id'])

        # only pending deletable; non-admins only their own
        if wfh.status != 'pending':
            return JsonResponse({'success': False, 'error': 'Only pending requests can be deleted'})
        if not (request.user.is_superuser or request.session.get('user_level') == 'normal'):
            if wfh.employee.user_id != request.session.get('custom_user_id'):
                return JsonResponse({'success': False, 'error': 'You can only delete your own requests'})

        wfh.delete()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})
