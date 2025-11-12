from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse
from django.db.models import Q
import requests
from django.utils.timezone import now
from app1.models import Employee, User, LeaveRequest, LateRequest, EarlyRequest, Attendance
from wfh_Request.models import WorkFromHomeRequest
from .models import CancelRequest


# ✅ WhatsApp API details
PHONE_NUMBERS = [
    "9946545535", "7593820007", "7593820005",
    "9846754998", "8129191379", "9061947005", "7306197537"
]

WA_API = "https://app.dxing.in/api/send/whatsapp"
WA_SECRET = "7b8ae820ecb39f8d173d57b51e1fce4c023e359e"
WA_ACCOUNT = "1761365422812b4ba287f5ee0bc9d43bbf5bbe87fb68fc4daea92d8"

import requests
from urllib.parse import quote_plus

def send_whatsapp_message(phone, message):
    """Send WhatsApp message via DX API using same format as browser test"""
    if not phone or not message:
        print("❌ Missing phone or message")
        return

    phone = str(phone).strip()
    if not phone.startswith("91"):
        phone = "91" + phone

    try:
        encoded_msg = quote_plus(message)  # ✅ identical to browser encoding
        url = (
            f"https://app.dxing.in/api/send/whatsapp"
            f"?secret=7b8ae820ecb39f8d173d57b51e1fce4c023e359e"
            f"&account=1761365422812b4ba287f5ee0bc9d43bbf5bbe87fb68fc4daea92d8"
            f"&recipient={phone}"
            f"&type=text"
            f"&message={encoded_msg}"
            f"&priority=1"
        )

        response = requests.get(url, timeout=10)
        print("✅ WhatsApp URL:", url)
        print("✅ WhatsApp Response:", response.text)
        if response.status_code == 200:
            print("✅ WhatsApp message sent successfully to", phone)
        else:
            print("❌ WhatsApp error:", response.status_code, response.text)
    except Exception as e:
        print("❌ WhatsApp send error:", e)





# ✅ USER PAGE
@login_required
def user_cancel_requests(request):
    user_id = request.session.get('custom_user_id')
    if not user_id:
        return render(request, "cancel_requestes.html", {
            'error': "User session not found. Please login again."
        })

    employee = Employee.objects.filter(user_id=user_id).first()
    if not employee:
        user = get_object_or_404(User, id=user_id)
        employee, _ = Employee.objects.get_or_create(
            user_id=user.id,
            defaults={'name': user.name, 'branch': user.branch}
        )

    filter_type = request.GET.get('type', 'all')

    # ✅ Only include requests for today and upcoming dates
    today = now().date()

    leaves = LeaveRequest.objects.filter(
        employee=employee,
        status__in=['approved', 'rejected'],
        end_date__gte=today        # 👈 Only current or future leaves
    )

    late = LateRequest.objects.filter(
        employee=employee,
        status__in=['approved', 'rejected'],
        date__gte=today             # 👈 Only today or future
    )

    early = EarlyRequest.objects.filter(
        employee=employee,
        status__in=['approved', 'rejected'],
        date__gte=today             # 👈 Only today or future
    )

    wfh = WorkFromHomeRequest.objects.filter(
        employee=employee,
        status__in=['approved', 'rejected'],
        end_date__gte=today         # 👈 Only current or future WFH
    )

    # Filter selection (existing logic)
    if filter_type == 'leave':
        late = early = wfh = []
    elif filter_type == 'late':
        leaves = early = wfh = []
    elif filter_type == 'early':
        leaves = late = wfh = []
    elif filter_type == 'wfh':
        leaves = late = early = []

    sent_cancel_requests = CancelRequest.objects.filter(employee=employee).values_list(
        'request_type', 'request_id'
    )
    cancel_lookup = {f"{r_type}-{r_id}": True for r_type, r_id in sent_cancel_requests}

    context = {
        'employee': employee,
        'leaves': leaves,
        'late': late,
        'early': early,
        'wfh': wfh,
        'filter_type': filter_type,
        'cancel_lookup': cancel_lookup,
    }
    return render(request, 'cancel_requestes.html', context)


# ✅ USER SUBMITS CANCEL REQUEST
@login_required
def add_cancel_request(request):
    if request.method == "POST":
        emp = get_object_or_404(Employee, user_id=request.session.get('custom_user_id'))
        req_type = request.POST['request_type']
        req_id = request.POST['request_id']

        already_exists = CancelRequest.objects.filter(
            employee=emp,
            request_type=req_type,
            request_id=req_id,
            status='pending'
        ).exists()

        if already_exists:
            messages.warning(request, "You have already sent a cancel request for this.")
            return redirect('user_cancel_requestes')

        reason = request.POST.get('reason', '')
        cancel_req = CancelRequest.objects.create(
            employee=emp,
            request_type=req_type,
            request_id=req_id,
            reason=reason
        )

        # ✅ Send WhatsApp to all admins
        msg = (
            f"📢 *New Cancel Request Received*\n\n"
            f"👤 Employee: {emp.name}\n"
            # f"🏢 Branch: {emp.branch}\n"
            f"🗂 Type: {req_type.upper()}\n"
            f"📝 Reason: {reason or 'No reason provided'}\n"
            f"🕒 Time: {timezone.now().strftime('%d-%m-%Y %I:%M %p')}"
        )
        for num in PHONE_NUMBERS:
            send_whatsapp_message(num, msg)

        messages.success(request, "Cancel request sent successfully!")
        return redirect('user_cancel_requestes')

    messages.error(request, "Invalid request.")
    return redirect('user_cancel_requestes')


# ✅ ADMIN VIEW PAGE
@login_required
def admin_cancel_requests(request):
    search_name = request.GET.get('name', '').strip()
    filter_type = request.GET.get('type', 'all')

    requests_list = CancelRequest.objects.select_related('employee').order_by('-created_at')

    if search_name:
        requests_list = requests_list.filter(employee__name__icontains=search_name)
    if filter_type != 'all':
        requests_list = requests_list.filter(request_type=filter_type)

    context = {
        'requests': requests_list,
        'search_name': search_name,
        'filter_type': filter_type,
    }
    return render(request, 'admin_cancel_requestes.html', context)


# ✅ ADMIN APPROVE / REJECT CANCEL REQUEST
@login_required
def process_cancel_request(request, req_id, action):
    from app1.views import send_whatsapp_message  # ✅ Use same WhatsApp sender from app1
    from app1.models import Employee, LeaveRequest, LateRequest, EarlyRequest, Attendance
    from wfh_Request.models import WorkFromHomeRequest

    cancel_req = get_object_or_404(CancelRequest, id=req_id)
    cancel_req.status = 'approved' if action == 'approve' else 'rejected'
    cancel_req.processed_by = request.user.username
    cancel_req.processed_at = timezone.now()
    cancel_req.save()

    emp = cancel_req.employee

    # ✅ Get phone number (same logic as leave approval in app1)
    phone = getattr(emp, 'phone_personal', None) or getattr(emp, 'phone_residential', None)

    if phone:
        phone = str(phone).strip()
        if not phone.startswith("91"):
            phone = "91" + phone

        # ✅ WhatsApp message (same format as app1 leave approval)
        status_text = "Approved ✅" if cancel_req.status == 'approved' else "Rejected ❌"
        msg_user = (
            f"📢 *Cancel Request Update*\n\n"
            f"🗂 Type: {cancel_req.request_type.upper()}\n"
            f"📊 Status: {status_text}\n"
            f"👤 Processed By: {cancel_req.processed_by}\n"
            f"🕒 {timezone.now().strftime('%d-%m-%Y %I:%M %p')}"
        )

        # ✅ Send message to the user
        send_whatsapp_message(phone, msg_user)
        print("✅ WhatsApp sent to:", phone)
    else:
        print("⚠️ No phone number found for employee:", emp.name)

    # ✅ If approved → reset original request & update attendance
    if cancel_req.status == 'approved':
        if cancel_req.request_type == 'leave':
            leave = LeaveRequest.objects.filter(id=cancel_req.request_id).first()
            if leave:
                leave.status = 'cancelled'
                leave.save()
                Attendance.objects.filter(
                    employee=emp,
                    date__range=[leave.start_date, leave.end_date]
                ).update(status='initial')

        elif cancel_req.request_type == 'late':
            late = LateRequest.objects.filter(id=cancel_req.request_id).first()
            if late:
                late.status = 'cancelled'
                late.save()
                Attendance.objects.filter(
                    employee=emp,
                    date=late.date
                ).update(status='initial')

        elif cancel_req.request_type == 'early':
            early = EarlyRequest.objects.filter(id=cancel_req.request_id).first()
            if early:
                early.status = 'cancelled'
                early.save()
                Attendance.objects.filter(
                    employee=emp,
                    date=early.date
                ).update(status='initial')

        elif cancel_req.request_type == 'wfh':
            wfh = WorkFromHomeRequest.objects.filter(id=cancel_req.request_id).first()
            if wfh:
                wfh.status = 'cancelled'
                wfh.save()
                Attendance.objects.filter(
                    employee=emp,
                    date__range=[wfh.start_date, wfh.end_date]
                ).update(status='initial')

    return redirect('admin_cancel_requestes')



