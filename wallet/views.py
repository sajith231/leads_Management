from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from .models import Wallet
from urllib.parse import quote
import os
from django.db.models import Q
import requests
import json
import time

def is_admin_user(request):
    """Determine whether the current request should be treated as admin/superadmin."""
    try:
        if request.user and getattr(request.user, 'is_superuser', False):
            return True
    except Exception:
        pass

    user_level = request.session.get('user_level', '')
    admin_levels = ['admin_level', '5level', '4level', 'superadmin', 'admin']
    return str(user_level) in admin_levels


def wallet_list(request):
    """Display wallets with role-based filtering."""
    if is_admin_user(request):
        wallets = Wallet.objects.all().order_by('-created_at')
    else:
        owner_q = Q()
        if request.user and request.user.is_authenticated:
            owner_q = Q(created_by=request.user)

        custom_user_id = request.session.get('custom_user_id')
        if custom_user_id:
            owner_q = owner_q | Q(created_by__id=custom_user_id)

        user_visibility_q = Q(visibility_priority='user')
        wallets = Wallet.objects.filter(user_visibility_q | owner_q).order_by('-created_at')

    # Type-specific lists
    bank_wallets = wallets.filter(upload_type='bank')
    qr_wallets = wallets.filter(upload_type='qr')
    document_wallets = wallets.filter(upload_type='document')
    pdf_wallets = wallets.filter(upload_type='pdf')
    other_wallets = wallets.filter(upload_type='other')

    context = {
        'wallets': wallets,
        'bank_wallets': bank_wallets,
        'qr_wallets': qr_wallets,
        'document_wallets': document_wallets,
        'pdf_wallets': pdf_wallets,
        'other_wallets': other_wallets,
    }

    return render(request, 'wallet_list.html', context)


def add_wallet(request):
    """Add new wallet item"""
    if request.method == 'POST':
        title = request.POST.get('title')
        upload_type = request.POST.get('upload_type')
        visibility_priority = request.POST.get('visibility_priority')
        description = request.POST.get('description', '')

        image = None
        pdf_file = None
        
        if upload_type == 'bank':
            image = request.FILES.get('image_bank')
        elif upload_type == 'qr':
            image = request.FILES.get('image_qr')
        elif upload_type == 'document':
            image = request.FILES.get('image_document')
        elif upload_type == 'pdf':
            pdf_file = request.FILES.get('pdf_file')
            image = request.FILES.get('image_pdf')
        elif upload_type == 'other':
            image = request.FILES.get('image_other')

        if not title or not upload_type or not visibility_priority:
            messages.error(request, 'Please fill all required fields (Title, Upload Type, Visibility).')
            return render(request, 'add_wallet.html')

        if image:
            allowed_extensions = ['jpg', 'jpeg', 'png']
            file_extension = image.name.split('.')[-1].lower()

            if file_extension not in allowed_extensions:
                messages.error(request, 'Only JPG, JPEG, and PNG images are allowed.')
                return render(request, 'add_wallet.html')

            if image.size > 5 * 1024 * 1024:
                messages.error(request, 'Image file size should not exceed 5MB.')
                return render(request, 'add_wallet.html')

        if pdf_file:
            file_extension = pdf_file.name.split('.')[-1].lower()
            if file_extension != 'pdf':
                messages.error(request, 'Only PDF files are allowed.')
                return render(request, 'add_wallet.html')

            if pdf_file.size > 10 * 1024 * 1024:
                messages.error(request, 'PDF file size should not exceed 10MB.')
                return render(request, 'add_wallet.html')

        wallet = Wallet(
            title=title,
            upload_type=upload_type,
            visibility_priority=visibility_priority,
            description=description,
            image=image,
            pdf_file=pdf_file
        )

        if upload_type == 'bank':
            wallet.account_holder_name = request.POST.get('account_holder_name', '')
            wallet.account_number = request.POST.get('account_number', '')
            wallet.ifsc_code = request.POST.get('ifsc_code', '').upper()
            wallet.bank_address = request.POST.get('bank_address', '')
        elif upload_type == 'qr':
            wallet.qr_name = request.POST.get('qr_name', '')
        elif upload_type == 'pdf':
            wallet.pdf_name = request.POST.get('pdf_name', '')
        elif upload_type == 'other':
            wallet.other_name = request.POST.get('other_name', '')

        if request.user.is_authenticated:
            wallet.created_by = request.user

        wallet.save()
        messages.success(request, 'Wallet item added successfully!')
        return redirect('wallet_list')

    return render(request, 'add_wallet.html')


def edit_wallet(request, wallet_id):
    """Edit existing wallet with permission guard (admin OR owner)."""
    wallet = get_object_or_404(Wallet, id=wallet_id)

    allowed = False
    if is_admin_user(request):
        allowed = True
    else:
        if request.user and request.user.is_authenticated and wallet.created_by and wallet.created_by == request.user:
            allowed = True
        custom_user_id = request.session.get('custom_user_id')
        if not allowed and custom_user_id and hasattr(wallet, 'created_by') and wallet.created_by:
            try:
                if int(custom_user_id) == int(wallet.created_by.id):
                    allowed = True
            except Exception:
                pass

    if not allowed:
        messages.error(request, 'You do not have permission to edit this wallet.')
        return redirect('wallet_list')

    if request.method == 'POST':
        title = request.POST.get('title')
        upload_type = request.POST.get('upload_type')
        visibility_priority = request.POST.get('visibility_priority')
        description = request.POST.get('description', '')

        if not title or not upload_type or not visibility_priority:
            messages.error(request, 'Please fill all required fields.')
            return render(request, 'edit_wallet.html', {'wallet': wallet})

        new_image = None
        new_pdf = None
        
        if upload_type == 'bank':
            new_image = request.FILES.get('image_bank')
        elif upload_type == 'qr':
            new_image = request.FILES.get('image_qr')
        elif upload_type == 'document':
            new_image = request.FILES.get('image_document')
        elif upload_type == 'pdf':
            new_pdf = request.FILES.get('pdf_file')
            new_image = request.FILES.get('image_pdf')
        elif upload_type == 'other':
            new_image = request.FILES.get('image_other')

        if new_image:
            allowed_extensions = ['jpg', 'jpeg', 'png']
            file_extension = new_image.name.split('.')[-1].lower()
            if file_extension not in allowed_extensions:
                messages.error(request, 'Only JPG, JPEG, and PNG images are allowed.')
                return render(request, 'edit_wallet.html', {'wallet': wallet})
            if new_image.size > 5 * 1024 * 1024:
                messages.error(request, 'Image file size should not exceed 5MB.')
                return render(request, 'edit_wallet.html', {'wallet': wallet})

        if new_pdf:
            file_extension = new_pdf.name.split('.')[-1].lower()
            if file_extension != 'pdf':
                messages.error(request, 'Only PDF files are allowed.')
                return render(request, 'edit_wallet.html', {'wallet': wallet})
            if new_pdf.size > 10 * 1024 * 1024:
                messages.error(request, 'PDF file size should not exceed 10MB.')
                return render(request, 'edit_wallet.html', {'wallet': wallet})

        wallet.title = title
        wallet.upload_type = upload_type
        wallet.visibility_priority = visibility_priority
        wallet.description = description

        if upload_type == 'bank':
            wallet.account_holder_name = request.POST.get('account_holder_name', '')
            wallet.account_number = request.POST.get('account_number', '')
            wallet.ifsc_code = request.POST.get('ifsc_code', '').upper()
            wallet.bank_address = request.POST.get('bank_address', '')
            wallet.qr_name = ''
            wallet.pdf_name = ''
            wallet.other_name = ''
        elif upload_type == 'qr':
            wallet.qr_name = request.POST.get('qr_name', '')
            wallet.account_holder_name = ''
            wallet.account_number = ''
            wallet.ifsc_code = ''
            wallet.bank_address = ''
            wallet.pdf_name = ''
            wallet.other_name = ''
        elif upload_type == 'document':
            wallet.account_holder_name = ''
            wallet.account_number = ''
            wallet.ifsc_code = ''
            wallet.bank_address = ''
            wallet.qr_name = ''
            wallet.pdf_name = ''
            wallet.other_name = ''
        elif upload_type == 'pdf':
            wallet.pdf_name = request.POST.get('pdf_name', '')
            wallet.account_holder_name = ''
            wallet.account_number = ''
            wallet.ifsc_code = ''
            wallet.bank_address = ''
            wallet.qr_name = ''
            wallet.other_name = ''
        elif upload_type == 'other':
            wallet.other_name = request.POST.get('other_name', '')
            wallet.account_holder_name = ''
            wallet.account_number = ''
            wallet.ifsc_code = ''
            wallet.bank_address = ''
            wallet.qr_name = ''
            wallet.pdf_name = ''

        if new_image:
            try:
                if wallet.image and hasattr(wallet.image, 'path'):
                    old_path = wallet.image.path
                    if os.path.exists(old_path):
                        os.remove(old_path)
            except Exception:
                pass
            wallet.image = new_image

        if new_pdf:
            try:
                if wallet.pdf_file and hasattr(wallet.pdf_file, 'path'):
                    old_path = wallet.pdf_file.path
                    if os.path.exists(old_path):
                        os.remove(old_path)
            except Exception:
                pass
            wallet.pdf_file = new_pdf

        wallet.save()
        messages.success(request, 'Wallet item updated successfully!')
        return redirect('wallet_list')

    return render(request, 'edit_wallet.html', {'wallet': wallet})


def delete_wallet(request, wallet_id):
    """Delete wallet item with permission guard (admin OR owner)."""
    if request.method == 'POST':
        try:
            wallet = Wallet.objects.get(id=wallet_id)
        except Wallet.DoesNotExist:
            messages.error(request, 'Wallet item not found.')
            return redirect('wallet_list')

        allowed = False
        if is_admin_user(request):
            allowed = True
        else:
            if request.user and request.user.is_authenticated and wallet.created_by and wallet.created_by == request.user:
                allowed = True
            custom_user_id = request.session.get('custom_user_id')
            if not allowed and custom_user_id and hasattr(wallet, 'created_by') and wallet.created_by:
                try:
                    if int(custom_user_id) == int(wallet.created_by.id):
                        allowed = True
                except Exception:
                    pass

        if not allowed:
            messages.error(request, 'You do not have permission to delete this wallet.')
            return redirect('wallet_list')

        try:
            if wallet.image and hasattr(wallet.image, 'path'):
                if os.path.exists(wallet.image.path):
                    os.remove(wallet.image.path)
        except Exception:
            pass

        try:
            if wallet.pdf_file and hasattr(wallet.pdf_file, 'path'):
                if os.path.exists(wallet.pdf_file.path):
                    os.remove(wallet.pdf_file.path)
        except Exception:
            pass

        wallet.delete()
        messages.success(request, 'Wallet item deleted successfully!')

    return redirect('wallet_list')


import os
import json
import time
import requests
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from dotenv import load_dotenv

from .models import Wallet  # make sure this import matches your app structure

# ✅ Load environment variables
load_dotenv()

# ✅ WhatsApp API credentials from .env
WHATSAPP_API_URL = os.getenv("WHATSAPP_API_URL", "https://app.dxing.in/api/send/whatsapp")
WHATSAPP_API_SECRET = os.getenv("WHATSAPP_API_SECRET")
WHATSAPP_API_ACCOUNT = os.getenv("WHATSAPP_API_ACCOUNT")


def wallet_whatsapp_share(request, wallet_id):
    """
    Send wallet details to WhatsApp via DXing API.
    Order: 1. text  2. image (if any)  3. PDF (if any)
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)

    try:
        data = json.loads(request.body)
        phone_raw = data.get('phone_number', '')
        phone = ''.join(filter(str.isdigit, phone_raw))
        if len(phone) < 10:
            return JsonResponse({'success': False, 'error': 'Invalid phone number'}, status=400)

        wallet = get_object_or_404(Wallet, id=wallet_id)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

    # ----------------------------------------------------------
    # Helper: Send one message payload
    # ----------------------------------------------------------
    def _send(payload: dict) -> bool:
        try:
            print('[DXing] Sending ->', payload)
            r = requests.get(WHATSAPP_API_URL, params=payload, timeout=30)
            print('[DXing] Response:', r.status_code, r.text[:200])

            if r.status_code == 200:
                try:
                    res = r.json()
                    return str(res.get('status', '')).lower() in ['true', '200', 'success']
                except Exception:
                    return True  # non-JSON 200 is still considered success
        except Exception as e:
            print('[DXing] Exception:', e)
        return False

    # ----------------------------------------------------------
    # 1️⃣ TEXT MESSAGE
    # ----------------------------------------------------------
    lines = [f"*{wallet.title}*"]

    if wallet.upload_type == 'bank':
        lines += [
            "*🏦 Bank details*",
            f"👤 Account holder: {wallet.account_holder_name or 'N/A'}",
            f"🔢 A/c No: {wallet.account_number or 'N/A'}",
            f"🏛️ IFSC: {wallet.ifsc_code or 'N/A'}",
            f"📍 Address: {wallet.bank_address or 'N/A'}"
        ]
    elif wallet.upload_type == 'qr' and wallet.qr_name:
        lines.append(f"📱 QR name: {wallet.qr_name}")
    elif wallet.upload_type == 'pdf' and wallet.pdf_name:
        lines.append(f"📄 PDF name: {wallet.pdf_name}")
    elif wallet.upload_type == 'other' and wallet.other_name:
        lines.append(f"💼 Wallet name: {wallet.other_name}")

    if wallet.description:
        lines += ["", f"📝 {wallet.description}"]

    text_ok = _send({
        'secret': WHATSAPP_API_SECRET,
        'account': WHATSAPP_API_ACCOUNT,
        'recipient': phone,
        'type': 'text',
        'message': '\n'.join(lines),
        'priority': '1'
    })

    # ----------------------------------------------------------
    # 2️⃣ IMAGE (if any)
    # ----------------------------------------------------------
    image_ok = False
    if wallet.image:
        try:
            image_url = request.build_absolute_uri(wallet.image.url)
            image_ok = _send({
                'secret': WHATSAPP_API_SECRET,
                'account': WHATSAPP_API_ACCOUNT,
                'recipient': phone,
                'type': 'image',
                'message': image_url,
                'priority': '1'
            })
            time.sleep(1)
        except Exception as e:
            print(f"[DXing] Image send error: {e}")

    # ----------------------------------------------------------
    # 3️⃣ PDF (if any)
    # ----------------------------------------------------------
    pdf_ok = False
    if hasattr(wallet, 'pdf_file') and wallet.pdf_file:
        try:
            pdf_url = request.build_absolute_uri(wallet.pdf_file.url)
            pdf_ok = _send({
                'secret': WHATSAPP_API_SECRET,
                'account': WHATSAPP_API_ACCOUNT,
                'recipient': phone,
                'type': 'file',
                'message': pdf_url,
                'priority': '1'
            })
        except Exception as e:
            print(f"[DXing] PDF send error: {e}")

    # ----------------------------------------------------------
    # ✅ Final Response to AJAX Caller
    # ----------------------------------------------------------
    if any([text_ok, image_ok, pdf_ok]):
        return JsonResponse({
            'success': True,
            'text_sent': text_ok,
            'image_sent': image_ok,
            'pdf_sent': pdf_ok
        })

    return JsonResponse({
        'success': False,
        'error': 'Nothing could be delivered – check server logs'
    }, status=500)
