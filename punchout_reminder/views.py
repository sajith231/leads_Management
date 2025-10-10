from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.utils import timezone
from datetime import datetime
from urllib.parse import quote_plus, quote
import pytz, requests

# pull models from app1 (they already exist there)
from app1.models import LeaveRequest, LateRequest, EarlyRequest, Employee, Attendance

# ---------- TODAY REQUESTS (moved from app1.views) ----------
@require_GET
def today_requests(request):
    """
    Send today's requests summary + all detailed lines combined into a single message.

    Auto send times (IST): 11:00, 16:00 (minute == 0)
    Query:
      - force=1       -> force send regardless of IST time
      - dry_run=1     -> build payload but don't send
      - debug=1       -> include extra timing/info
      - limit=N       -> cap number of detail lines
      - recipients=comma,separated,numbers
      - date=YYYY-MM-DD -> override day (defaults to today in IST)
    """
    date_str = request.GET.get('date')
    try:
        if date_str:
            query_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        else:
            # use localdate (respects TIME_ZONE) for “today”
            query_date = timezone.localdate()
    except ValueError:
        return JsonResponse({'success': False, 'error': 'Invalid date format. Use YYYY-MM-DD.'}, status=400)

    requests_list = []
    status_counts = {'approved': 0, 'pending': 0, 'rejected': 0, 'other': 0}
    totals = {'leave': 0, 'late': 0, 'early': 0}

    def fmt_date(d):
        if not d:
            return ''
        try:
            return d.strftime('%d-%m-%Y')
        except Exception:
            try:
                dt = datetime.fromisoformat(str(d))
                return dt.strftime('%d-%m-%Y')
            except Exception:
                return str(d)

    # ---- Leaves
    leave_qs = LeaveRequest.objects.filter(
        start_date__lte=query_date, end_date__gte=query_date
    ).select_related('employee').order_by('-created_at')

    for lr in leave_qs:
        totals['leave'] += 1
        st = (lr.status or '').lower()
        if st in ['approved', 'pending', 'rejected']:
            status_counts[st] += 1
        else:
            status_counts['other'] += 1

        requests_list.append({
            'type': 'Leave',
            'employee_id': lr.employee.id,
            'employee_name': lr.employee.name,
            'start_date': fmt_date(lr.start_date),
            'end_date'  : fmt_date(lr.end_date),
            'date'      : fmt_date(query_date),
            'details'   : lr.get_leave_type_display() if hasattr(lr, 'get_leave_type_display') else '',
            'reason'    : getattr(lr, 'reason', '') or '',
            'status'    : st or 'unknown',
            'created_at': lr.created_at.strftime('%d-%m-%Y %H:%M') if getattr(lr, 'created_at', None) else ''
        })

    # ---- Late
    late_qs = LateRequest.objects.filter(
        date=query_date
    ).select_related('employee').order_by('-created_at')

    for lt in late_qs:
        totals['late'] += 1
        st = (lt.status or '').lower()
        if st in ['approved', 'pending', 'rejected']:
            status_counts[st] += 1
        else:
            status_counts['other'] += 1

        created_dt = getattr(lt, 'created_at', None)
        requests_list.append({
            'type': 'Late',
            'employee_id': lt.employee.id,
            'employee_name': lt.employee.name,
            'start_date': fmt_date(lt.date),
            'end_date'  : fmt_date(lt.date),
            'date'      : fmt_date(lt.date),
            'details'   : getattr(lt, 'delay_time', '') or '',
            'reason'    : getattr(lt, 'reason', '') or '',
            'status'    : st or 'unknown',
            'created_at': (created_dt.strftime('%d-%m-%Y %H:%M') if created_dt else '')
        })

    # ---- Early
    early_qs = EarlyRequest.objects.filter(
        date=query_date
    ).select_related('employee').order_by('-created_at')
    
    for er in early_qs:
        totals['early'] += 1
        st = (er.status or '').lower()
        if st in ['approved', 'pending', 'rejected']:
            status_counts[st] += 1
        else:
            status_counts['other'] += 1
            
        created_dt = getattr(er, 'created_at', None)
        requests_list.append({
            'type': 'Early',
            'employee_id': er.employee.id,
            'employee_name': er.employee.name,
            'start_date': fmt_date(er.date),
            'end_date'  : fmt_date(er.date),
            'date'      : fmt_date(er.date),
            'details'   : getattr(er, 'early_time', '') or '',
            'reason'    : getattr(er, 'reason', '') or '',
            'status'    : st or 'unknown',
            'created_at': (created_dt.strftime('%d-%m-%Y %H:%M') if created_dt else '')
        })

    total_requests = totals['leave'] + totals['late'] + totals['early']
    counts = {
        'total': total_requests,
        'leave': totals['leave'],
        'late' : totals['late'],
        'early': totals['early'],
        'status_counts': status_counts
    }

    json_payload = {
        'success': True,
        'date': fmt_date(query_date),
        'counts': counts,
        'requests': requests_list,
    }

    # --- sending config (same credentials as before)
    recipients_param = request.GET.get('recipients')
    if recipients_param:
        recipients = [r.strip() for r in recipients_param.split(',') if r.strip()]
    else:
        recipients = ['9061947005','7306197537','9946545535','7593820007','7593820005']

    dxing_url = "https://app.dxing.in/api/send/whatsapp"
    dxing_secret = "7b8ae820ecb39f8d173d57b51e1fce4c023e359e"
    dxing_account = "1756959119812b4ba287f5ee0bc9d43bbf5bbe87fb68b9118fcf1af"

    send_results = []
    send_attempted = False

    # --- time window: IST 11:00 or 16:00 (minute==0), or force
    try:
        ist = pytz.timezone('Asia/Kolkata')
        ist_now = datetime.now(ist)
    except Exception:
        try:
            ist_now = timezone.now().astimezone(pytz.timezone('Asia/Kolkata'))
        except Exception:
            ist_now = timezone.now()

    force_send = request.GET.get('force') in ('1', 'true', 'True')
    dry_run = request.GET.get('dry_run') in ('1', 'true', 'True')
    debug = request.GET.get('debug') in ('1', 'true', 'True')

    try:
        limit = int(request.GET.get('limit', 100))
    except Exception:
        limit = 100

    AUTO_HOURS_IST = (11, 16)
    ist_now_hour = getattr(ist_now, 'hour', 0)
    ist_now_minute = getattr(ist_now, 'minute', 0)
    should_send_now = force_send or (ist_now_hour in AUTO_HOURS_IST and ist_now_minute == 0)

    # build combined message
    header = f"🗓️ Requests for {fmt_date(query_date)}\nTotal: {counts['total']} (Leave {counts['leave']}, Late {counts['late']}, Early {counts['early']})"
    lines = []
    for r in requests_list[:limit]:
        if r['type'] == 'Leave':
            lines.append(f"• {r['employee_name']} | Leave {r['start_date']} → {r['end_date']} | {r['status']}")
        elif r['type'] == 'Late':
            lines.append(f"• {r['employee_name']} | Late {r['date']} | {r['details']} | {r['status']}")
        else:
            lines.append(f"• {r['employee_name']} | Early {r['date']} | {r['details']} | {r['status']}")

    combined_text = header + ("\n\n" + "\n".join(lines) if lines else "\n\n(No requests)")
    encoded_text = quote_plus(combined_text)

    if should_send_now and not dry_run:
        send_attempted = True
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        session = requests.Session()

        norm_recipients = []
        for r in recipients:
            rno = "".join(ch for ch in r if ch.isdigit())
            if rno:
                norm_recipients.append(rno)

        for rno in norm_recipients:
            try:
                payload = f"secret={dxing_secret}&account={dxing_account}&recipient={rno}&type=text&message={encoded_text}&priority=1"
                resp = session.post(dxing_url, data=payload, headers=headers)
                send_results.append({
                    'recipient': rno,
                    'phase': 'combined',
                    'ok': resp.status_code in (200, 201),
                    'status_code': resp.status_code,
                    'response_text': resp.text[:500],
                    'message_length': len(combined_text)
                })
            except Exception as e:
                send_results.append({
                    'recipient': rno,
                    'phase': 'combined',
                    'ok': False,
                    'error': str(e),
                    'message_length': len(combined_text)
                })
        session.close()

    json_payload['send_attempted'] = send_attempted
    json_payload['should_send_logic'] = {
        'force_send': force_send,
        'current_hour': ist_now_hour,
        'current_minute': ist_now_minute,
        'is_auto_hour': ist_now_hour in AUTO_HOURS_IST,
        'is_exact_minute': ist_now_minute == 0
    }
    if send_attempted:
        json_payload['send_results'] = send_results
        json_payload['message_sent'] = combined_text
        json_payload['recipients_count'] = len(norm_recipients)

    if debug:
        json_payload['ist_now'] = ist_now.isoformat()
        json_payload['total_requests_found'] = len(requests_list)

    return JsonResponse(json_payload)


# ---------- PUNCH-OUT REMINDER (moved from app1.views) ----------
@require_GET
def send_punchout_reminders(request):
    """
    WhatsApp 'Punch-out reminder' at 6:15 PM IST for employees
    who punched in today but not punched out yet.
    ?force=1 -> bypass time gate
    ?dry_run=1 -> build list but don't send
    """
    ist = pytz.timezone("Asia/Kolkata")
    now_ist = timezone.now().astimezone(ist)
    today = now_ist.date()

    force = request.GET.get("force") in ("1", "true", "True")
    dry_run = request.GET.get("dry_run") in ("1", "true", "True")

    if not force:
        if not (now_ist.hour == 18 and now_ist.minute == 15):
            return JsonResponse({
                "success": False,
                "error": "Not reminder time",
                "now_ist": now_ist.strftime("%Y-%m-%d %H:%M:%S"),
                "expected_ist": "18:15",
            }, status=400)

    qs = Attendance.objects.select_related("employee", "employee__user") \
        .filter(date=today, punch_in__isnull=False, punch_out__isnull=True)

    DX_URL = "https://app.dxing.in/api/send/whatsapp"
    DX_SECRET = "7b8ae820ecb39f8d173d57b51e1fce4c023e359e"
    DX_ACCOUNT = "1756959119812b4ba287f5ee0bc9d43bbf5bbe87fb68b9118fcf1af"

    targets = []
    for att in qs:
        phone = getattr(getattr(att.employee, "user", None), "phone_number", None) or getattr(att.employee, "phone_number", None)
        if phone:
            targets.append((att, "".join([c for c in str(phone) if c.isdigit()])))  # normalize digits

    if not targets:
        return JsonResponse({"success": True, "message": "No pending punch-outs.", "count": 0})

    text = "⏰ Reminder: Please punch out before leaving for the day."
    encoded_text = quote(text)

    results = []
    if not dry_run:
        for _att, msisdn in targets:
            try:
                url = f"{DX_URL}?secret={DX_SECRET}&account={DX_ACCOUNT}&recipient={msisdn}&type=text&message={encoded_text}&priority=1"
                r = requests.get(url, timeout=15)
                results.append({"msisdn": msisdn, "ok": r.status_code in (200, 201), "code": r.status_code, "resp": r.text[:300]})
            except Exception as e:
                results.append({"msisdn": msisdn, "ok": False, "error": str(e)})
    else:
        results = [{"msisdn": msisdn, "ok": True, "dry_run": True} for _, msisdn in targets]

    return JsonResponse({"success": True, "count": len(targets), "results": results})
