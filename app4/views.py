import base64
import requests  # ADD THIS IMPORT
import logging
import json
import requests
import os
import os, json, logging, requests
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.core.exceptions import ValidationError
from app1.models import Branch
from app1.models import User
from datetime import datetime, date
from datetime import datetime, date
from .models import License, KeyRequest ,Collection
from django.views.decorators.csrf import csrf_exempt
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from datetime import datetime, timedelta
from django.utils import timezone
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.conf import settings
from django.shortcuts import get_object_or_404
from django.core.cache import cache
from django.contrib.auth.decorators import login_required


# Set up logging
logger = logging.getLogger(__name__)

# ------------------------
# License Views
# ------------------------

def license_type_view(request):
    licenses = License.objects.select_related('branch').all().order_by('-id')
    branches = Branch.objects.all()
    return render(request, 'license_type.html', {'licenses': licenses, 'branches': branches})

@require_http_methods(["GET", "POST"])
def add_license_view(request):
    if request.method == 'POST':
        name             = request.POST.get('name', '').strip()
        branch_id        = request.POST.get('branch')
        service_pack     = request.POST.get('service_pack', '').strip()
        place            = request.POST.get('place', '').strip()
        type_field       = request.POST.get('type', '').strip()
        number_of_system = request.POST.get('number_of_system', '').strip()
        module           = request.POST.get('module', '').strip()
        notes            = request.POST.get('notes', '').strip()
        uploaded_file    = request.FILES.get('license_file')

        if not (name and branch_id and uploaded_file):
            return render(request, 'add_license.html', {
                'branches': Branch.objects.all(),
                'error': 'Please provide name, branch and a .txt file.'
            })

        if not uploaded_file.name.lower().endswith('.txt'):
            return render(request, 'add_license.html', {
                'branches': Branch.objects.all(),
                'error': 'Only .txt files are allowed.'
            })

        file_bytes = uploaded_file.read()
        b64 = base64.b64encode(file_bytes).decode('ascii')

        License.objects.create(
            name=name, branch_id=branch_id,
            service_pack=service_pack, place=place,
            type=type_field, number_of_system=number_of_system,
            module=module, notes=notes,
            license_key=b64, file_name=uploaded_file.name
        )
        return redirect('license_type')

    return render(request, 'add_license.html', {'branches': Branch.objects.all()})

def license_download(request, license_id):
    lic = get_object_or_404(License, id=license_id)
    data = base64.b64decode(lic.license_key)
    filename = lic.file_name or f"{lic.name}.txt"
    resp = HttpResponse(data, content_type='application/octet-stream')
    resp['Content-Disposition'] = f'attachment; filename="{filename}"'
    return resp

def license_preview(request, license_id):
    lic = get_object_or_404(License, id=license_id)
    content = base64.b64decode(lic.license_key).decode('utf-8', errors='replace')
    return JsonResponse({
        'id': lic.id,
        'name': lic.name,
        'branch': lic.branch.name,
        'service_pack': lic.service_pack or '',
        'place': lic.place or '',
        'type': lic.type or '',
        'number_of_system': lic.number_of_system or '',
        'module': lic.module or '',
        'notes': lic.notes or '',
        'created_at': lic.created_at.strftime('%d-%m-%Y'),
        'file_name': lic.file_name,
        'license_content': content  # Changed from 'content' to 'license_content'
    })

@require_http_methods(["GET", "POST"])
def license_edit(request, license_id):
    lic = get_object_or_404(License, id=license_id)
    if request.method == 'POST':
        lic.name             = request.POST.get('name', lic.name).strip()
        lic.branch_id        = request.POST.get('branch', lic.branch_id)
        lic.service_pack     = request.POST.get('service_pack', '').strip()
        lic.place            = request.POST.get('place', '').strip()
        lic.type             = request.POST.get('type', '').strip()
        lic.number_of_system = request.POST.get('number_of_system', '').strip()
        lic.module           = request.POST.get('module', '').strip()
        lic.notes            = request.POST.get('notes', '').strip()

        uploaded_file = request.FILES.get('license_file')
        if uploaded_file:
            if not uploaded_file.name.lower().endswith('.txt'):
                return render(request, 'license_edit.html', {
                    'license': lic,
                    'branches': Branch.objects.all(),
                    'error': 'Only .txt files allowed.'
                })
            lic.license_key = base64.b64encode(uploaded_file.read()).decode('ascii')
            lic.file_name   = uploaded_file.name

        lic.save()
        return redirect('license_type')

    return render(request, 'license_edit.html', {
        'license': lic,
        'branches': Branch.objects.all()
    })

@require_http_methods(["POST"])
def license_delete(request, license_id):
    get_object_or_404(License, id=license_id).delete()
    return redirect('license_type')




def build_description_from_dynamic_fields(keyType, request_post):
    """Enhanced function to build description from dynamic field data based on key type"""
    description_parts = []
    base_description = request_post.get("description", "").strip()
    if base_description:
        description_parts.append(f"Description: {base_description}")
    
    if keyType == "Seat Upgradation Request":
        current_seats = request_post.get('currentSeats')
        required_seats = request_post.get('requiredSeats')
        if current_seats or required_seats:
            description_parts.append(f"Seats Upgrade: {current_seats or 'N/A'} → {required_seats or 'N/A'}")
            
    elif keyType == "Maturity Upgradation Request":
        current_maturity = request_post.get('currentMaturity')
        required_maturity = request_post.get('requiredMaturity')
        if current_maturity or required_maturity:
            description_parts.append(f"Maturity Upgrade: {current_maturity or 'N/A'} → {required_maturity or 'N/A'}")
            
    elif keyType == "More Module Request":
        module = request_post.get('module')
        if module:
            description_parts.append(f"Requested Module: {module}")
            
    elif keyType == "Software Amount Change Request":
        current_amount = request_post.get('currentAmount')
        required_amount = request_post.get('requiredAmount')
        if current_amount or required_amount:
            description_parts.append(f"Amount Change: ₹{current_amount or 'N/A'} → ₹{required_amount or 'N/A'}")
            
    elif keyType == "Demo Key Request":
        task = request_post.get('task')
        bcare = request_post.get('bcare')
        icare = request_post.get('icare')
        demo_parts = []
        if task: demo_parts.append(f"Task: {task}")
        if bcare: demo_parts.append(f"B-Care: {bcare}")
        if icare: demo_parts.append(f"I-Care: {icare}")
        if demo_parts:
            description_parts.append(" | ".join(demo_parts))
            
    elif keyType == "Hosted Key Request":
        server_details = request_post.get('serverDetails')
        if server_details:
            description_parts.append(f"Server Details: {server_details}")
            
    elif keyType == "Feeder Cancellation Request":
        cancel_reason = request_post.get('cancelReason')
        if cancel_reason:
            description_parts.append(f"Cancellation Reason: {cancel_reason}")
            
    elif keyType == "Key Extension Request":
        extension_period = request_post.get('extensionPeriod')
        if extension_period:
            description_parts.append(f"Extension Period: {extension_period}")
            
    elif keyType == "Trade Name And Address Change Request":
        new_firm_name = request_post.get('newFirmName')
        new_address = request_post.get('newAddress')
        change_parts = []
        if new_firm_name: change_parts.append(f"New Firm: {new_firm_name}")
        if new_address: change_parts.append(f"New Address: {new_address}")
        if change_parts:
            description_parts.append(" | ".join(change_parts))
            
    elif keyType == "Key type Change Request":
        current_key_type = request_post.get('currentKeyType')
        required_key_type = request_post.get('requiredKeyType')
        if current_key_type or required_key_type:
            description_parts.append(f"Key Type Change: {current_key_type or 'N/A'} → {required_key_type or 'N/A'}")
            
    elif keyType == "Enterprises Key Request":
        enterprise_details = request_post.get('enterpriseDetails')
        if enterprise_details:
            description_parts.append(f"Enterprise Details: {enterprise_details}")
            
    elif keyType == "Special Updation Request":
        special_details = request_post.get('specialUpdateDetails')
        if special_details:
            description_parts.append(f"Special Update Details: {special_details}")

    return "\n".join(description_parts)

def get_branch_by_name(branch_name):
    """Helper function to get branch by name with error handling"""
    if not branch_name or not branch_name.strip():
        logger.info("No branch name provided")
        return None
    
    branch_name = branch_name.strip()
    logger.info(f"Looking for branch: '{branch_name}'")
    
    try:
        # List all available branches for debugging
        available_branches = list(Branch.objects.values_list('name', flat=True))
        logger.info(f"Available branches in database: {available_branches}")
        
        # Try exact match first
        branch = Branch.objects.filter(name__iexact=branch_name).first()
        if branch:
            logger.info(f"Found exact match: {branch_name} -> ID: {branch.id}")
            return branch
        
        # Try partial match
        partial_match = Branch.objects.filter(name__icontains=branch_name).first()
        if partial_match:
            logger.info(f"Found partial match: {branch_name} -> {partial_match.name} (ID: {partial_match.id})")
            return partial_match
            
        logger.warning(f"No branch found for: '{branch_name}'")
        return None
        
    except Exception as e:
        logger.error(f"Error finding branch '{branch_name}': {str(e)}")
        return None
import urllib.parse
from datetime import datetime
import requests
import logging

logger = logging.getLogger(__name__)

def send_key_request_whatsapp_notification(client_name, key_type, location, branch_name, amount=None, created_by=None):
    """
    Send WhatsApp notification when a new key request is created.
    'created_by' should be the display name of the user who created the request.
    """
    WHATSAPP_API_URL = "https://app.dxing.in/api/send/whatsapp"
    SECRET = "7b8ae820ecb39f8d173d57b51e1fce4c023e359e"
    ACCOUNT = "1756959119812b4ba287f5ee0bc9d43bbf5bbe87fb68b9118fcf1af"
    RECIPIENT = "9946545535"  

    try:
        amount_text = f"\nAmount: ₹{amount}" if amount and str(amount).strip() else ""
        created_by_text = f"\nRequested By: {created_by}" if created_by else "\nRequested By: -"

        message = (
            f"🔑 NEW KEY REQUEST\n\n"
            f"Client Info: {client_name}\n"
            f"Request Type: {key_type}\n"
            f"Location: {location}\n"
            f"Branch: {branch_name}{amount_text}\n"
            f"{created_by_text}\n\n"
            f"Created at: {datetime.now().strftime('%d-%m-%Y %H:%M')}"
        )

        encoded_message = urllib.parse.quote(message)

        api_url = f"{WHATSAPP_API_URL}?secret={SECRET}&account={ACCOUNT}&recipient={RECIPIENT}&type=text&message={encoded_message}&priority=1"

        resp = requests.get(api_url, timeout=10)
        if resp.status_code == 200:
            logger.info("WhatsApp notification sent successfully for key request: %s", client_name)
            return True
        else:
            logger.error("WhatsApp API returned non-200 for key request: %s - %s", resp.status_code, resp.text)
            return False

    except requests.exceptions.RequestException as e:
        logger.error("Network error sending WhatsApp for key request: %s", e)
        return False
    except Exception as e:
        logger.error("Unexpected error sending WhatsApp for key request: %s", e)
        return False


# Modified key_request view with WhatsApp notification
@login_required
def key_request(request):
    branches = Branch.objects.all()

    if request.method == "POST":
        # Required fields
        clientName   = request.POST.get("clientName")
        location     = request.POST.get("location")   # client's entered location
        keyType      = request.POST.get("keyType")
        requestDate  = request.POST.get("requestDate")

        # Optional fields
        branch_name  = request.POST.get("branch", "").strip()
        amount       = request.POST.get("amount", "").strip()
        requestImage = request.FILES.get("requestImage")

        # GPS fields (only for image requests)
        gps_lat = request.POST.get("gps_lat", "").strip()
        gps_lon = request.POST.get("gps_lon", "").strip()

        # Validation
        if not all([clientName, location, keyType, requestDate]):
            messages.error(request, "Please fill all required fields")
            return render(request, "key_request.html", {"branches": branches})

        try:
            requestDate = datetime.strptime(requestDate, "%Y-%m-%d").date()
        except ValueError:
            messages.error(request, "Invalid date format")
            return render(request, "key_request.html", {"branches": branches})

        # Build description
        final_description = build_description_from_dynamic_fields(keyType, request.POST)

        # Get the logged-in user's name
        requested_by_name = get_user_display_name(request.user) or "System"

        # Create object
        key_request_obj = KeyRequest(
            clientName=clientName,
            location=location,
            description=final_description,
            keyType=keyType,
            requestDate=requestDate,
            status="Pending",
            amount=amount if amount else None,
            branch_name=branch_name,
            requested_by=requested_by_name
        )

        # Handle image
        if requestImage:
            key_request_obj.requestImage = requestImage

        # Handle GPS separately (only if uploaded)
        if gps_lat and gps_lon:
            key_request_obj.gps_location = f"{gps_lat}, {gps_lon}"
            key_request_obj.gps_address = reverse_geocode(gps_lat, gps_lon)

        try:
            key_request_obj.save()
            
            # Send WhatsApp notification after successful save (includes creator name)
            try:
                send_key_request_whatsapp_notification(
                    client_name=clientName,
                    key_type=keyType,
                    location=location,
                    branch_name=branch_name,
                    amount=amount,
                    created_by=requested_by_name
                )
                logger.info("WhatsApp notification attempted for key request: %s (by %s)", clientName, requested_by_name)
            except Exception as e:
                logger.error("WhatsApp notification failed for key request %s: %s", clientName, e)
            
            messages.success(request, "Key request submitted successfully!")
            return redirect("key_request_list")
            
        except Exception as e:
            logger.error("Error saving key request: %s", e)
            messages.error(request, f"Error saving request: {str(e)}")
            return render(request, "key_request.html", {"branches": branches})

    return render(request, "key_request.html", {"branches": branches})




def key_request_list(request):
    # Remove select_related('branch') since branch is now a text field, not a foreign key
    key_requests = KeyRequest.objects.all().order_by('-id')
    branches = Branch.objects.all()
    
    return render(request, "key_request_list.html", {
        "key_requests": key_requests,
        "branches": branches
    })

@login_required
def key_request_edit(request, request_id):
    key_request_obj = get_object_or_404(KeyRequest, id=request_id)
    branches = Branch.objects.all()
    
    if request.method == "POST":
        try:
            # Get basic form data
            clientName = request.POST.get("clientName")
            location = request.POST.get("location")
            keyType = request.POST.get("keyType")
            req_date = request.POST.get("requestDate")
            branch_name = request.POST.get("branch", "").strip()
            amount = request.POST.get("amount", "").strip()
            description = request.POST.get("description", "").strip()

            # Debug logging
            logger.info(f"Editing key request {request_id}")
            logger.info(f"Form data: clientName={clientName}, keyType={keyType}, branch_name={branch_name}")

            # Validate required fields
            if not all([clientName, location, keyType, req_date]):
                messages.error(request, "Please fill all required fields")
                return render(request, "key_request_edit.html", {
                    "key_request": key_request_obj,
                    "branches": branches
                })

            # Validate and convert date
            try:
                parsed_date = datetime.strptime(req_date, "%Y-%m-%d").date()
                key_request_obj.requestDate = parsed_date
            except ValueError:
                messages.error(request, "Invalid date format")
                return render(request, "key_request_edit.html", {
                    "key_request": key_request_obj,
                    "branches": branches
                })

            # Update basic fields
            key_request_obj.clientName = clientName
            key_request_obj.location = location
            key_request_obj.keyType = keyType
            key_request_obj.branch_name = branch_name
            key_request_obj.amount = amount if amount else None
            key_request_obj.description = description

            # IMPORTANT: Don't overwrite the original requested_by field during edit
            # The requested_by should remain as the original user who created the request
            # Only set it if it's currently empty for some reason
            if not key_request_obj.requested_by and request.user.is_authenticated:
                key_request_obj.requested_by = get_user_display_name(request.user)

            # Handle dynamic fields based on keyType
            if keyType == "Seat Upgradation Request":
                key_request_obj.currentSeats = request.POST.get('currentSeats', '')
                key_request_obj.requiredSeats = request.POST.get('requiredSeats', '')
                
            elif keyType == "More Module Request":
                key_request_obj.module = request.POST.get('module', '')
                
            # ... rest of your existing dynamic field handling ...

            # Build final description from dynamic fields
            final_description = build_description_from_dynamic_fields(keyType, request.POST)
            if final_description:
                key_request_obj.description = final_description

            # Save the object
            key_request_obj.save()
            
            logger.info(f"Key request {request_id} updated successfully")
            messages.success(request, "Key request updated successfully!")
            return redirect("key_request_list")
            
        except Exception as e:
            logger.error(f"Error updating key request {request_id}: {str(e)}")
            logger.error(f"Exception details: {type(e).__name__}: {str(e)}")
            messages.error(request, f"Error updating request: {str(e)}")
            return render(request, "key_request_edit.html", {
                "key_request": key_request_obj,
                "branches": branches
            })

    return render(request, "key_request_edit.html", {
        "key_request": key_request_obj,
        "branches": branches
    })
def key_request_delete(request, request_id):
    key_request_obj = get_object_or_404(KeyRequest, id=request_id)
    key_request_obj.delete()
    messages.success(request, "Key request deleted successfully!")
    return redirect("key_request_list")

# ------------------------
# AJAX Status Update Views
# ------------------------

@csrf_exempt
@require_http_methods(["POST"])
def update_key_request_status(request, request_id):
    """Update the admin status of a key request via AJAX"""
    try:
        key_request_obj = get_object_or_404(KeyRequest, id=request_id)
        data = json.loads(request.body)
        new_status = data.get('status')

        # Define valid status choices
        valid_statuses = ['Pending', 'On Process', 'Completed', 'Rejected']

        if new_status not in valid_statuses:
            return JsonResponse({
                'success': False,
                'message': f'Invalid status. Valid options: {", ".join(valid_statuses)}'
            }, status=400)

        key_request_obj.status = new_status
        key_request_obj.save()
        
        logger.info(f"Admin status updated for request {request_id}: {new_status}")
        return JsonResponse({
            'success': True, 
            'message': 'Status updated successfully'
        })

    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error in status update: {str(e)}")
        return JsonResponse({
            'success': False, 
            'message': 'Invalid JSON data'
        }, status=400)

    except Exception as e:
        logger.error(f"Error updating key request status: {str(e)}")
        return JsonResponse({
            'success': False, 
            'message': f'Server error: {str(e)}'
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def update_key_request_requested_status(request, request_id):
    """Update the requested status of a key request via AJAX"""
    try:
        key_request_obj = get_object_or_404(KeyRequest, id=request_id)
        data = json.loads(request.body)
        new_requested_status = data.get('requested_status')

        # Define valid requested status choices
        valid_requested_statuses = [
            'Requested', 
            'Pending',
            'Delayed',
            'Rejected',
            'Working on it', 
            'Work completed/No payment',
            'Work completed/Payment pending', 
            'Work done & Payment collected'
        ]

        if new_requested_status not in valid_requested_statuses:
            return JsonResponse({
                'success': False,
                'message': f'Invalid requested status. Valid options: {", ".join(valid_requested_statuses)}'
            }, status=400)

        key_request_obj.requested_status = new_requested_status
        key_request_obj.save()
        
        logger.info(f"Requested status updated for request {request_id}: {new_requested_status}")
        return JsonResponse({
            'success': True, 
            'message': 'Requested status updated successfully'
        })

    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error in requested status update: {str(e)}")
        return JsonResponse({
            'success': False, 
            'message': 'Invalid JSON data'
        }, status=400)

    except Exception as e:
        logger.error(f"Error updating requested status: {str(e)}")
        return JsonResponse({
            'success': False, 
            'message': f'Server error: {str(e)}'
        }, status=500)


# Helper function to get user display name
def get_user_display_name(user):
    """Get the best display name for a user"""
    if not user.is_authenticated:
        return None
    
    # Try full name first
    if hasattr(user, 'get_full_name'):
        full_name = user.get_full_name().strip()
        if full_name:
            return full_name
    
    # Try first + last name
    if hasattr(user, 'first_name') and user.first_name.strip():
        first_name = user.first_name.strip()
        if hasattr(user, 'last_name') and user.last_name.strip():
            return f"{first_name} {user.last_name.strip()}"
        return first_name
    
    # Fall back to username
    return user.username
# ------------------------
# API Proxy Views
# ------------------------

def clients_proxy(request):
    """Proxy endpoint to fetch clients from external API"""
    try:
        url = "https://accmaster.imcbs.com/api/sync/rrc-clients/"
        response = requests.get(
            url,
            headers={"Accept": "application/json"},
            timeout=10
        )
        response.raise_for_status()
        return JsonResponse(response.json(), safe=False)
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Request error fetching clients: {str(e)}")
        return JsonResponse({"error": f"Request failed: {str(e)}"}, status=500)
    except Exception as e:
        logger.error(f"Unexpected error fetching clients: {str(e)}")
        return JsonResponse({"error": f"Unexpected error: {str(e)}"}, status=500)
    
def reverse_geocode(lat, lon):
    """Convert lat/lon into a readable address using OpenStreetMap"""
    try:
        url = f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lon}&format=json"
        headers = {"User-Agent": "key-request-app"}
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            return data.get("display_name", f"{lat}, {lon}")
    except Exception as e:
        logger.error(f"Reverse geocode failed: {e}")
    return f"{lat}, {lon}"


logger = logging.getLogger(__name__)

# -------------  NEW:  always-fresh client helper  --------------
EXTERNAL_CLIENTS_URL = "https://accmaster.imcbs.com/api/sync/rrc-clients/"

def _load_clients() -> list:
    """Return list[dict] with live client data (cached 5 min)."""
    key = "external_clients"
    cached = cache.get(key)
    if cached is not None:
        return cached
    try:
        r = requests.get(
            EXTERNAL_CLIENTS_URL,
            headers={"Accept": "application/json"},
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()
        cache.set(key, data, 300)          # 5-minute cache
        return data
    except Exception as exc:
        logger.error("Could not load external clients: %s", exc)
        return []                            # empty on failure
# ----------------------------------------------------------------

# --------------  collections_add  (re-written)  -----------------
# -------------------------------------------------
# NEW: WhatsApp helper for COLLECTION added message
# -------------------------------------------------
import urllib.parse
from datetime import datetime
import requests
import logging
logger = logging.getLogger(__name__)

WHATSAPP_API_URL = "https://app.dxing.in/api/send/whatsapp"
WHATSAPP_SECRET   = "7b8ae820ecb39f8d173d57b51e1fce4c023e359e"
WHATSAPP_ACCOUNT  = "1756959119812b4ba287f5ee0bc9d43bbf5bbe87fb68b9118fcf1af"
COLLECTION_RECIPIENTS = ["9061947005", "9946545535","6282351770","7593820007","7593820005","9562477819"]   # hard-coded numbers

def send_collection_whatsapp(client_name, branch, created_by, amount, created_at: datetime):
    """
    Fire identical WhatsApp alert to every number in COLLECTION_RECIPIENTS
    """
    for recipient in COLLECTION_RECIPIENTS:
        try:
            msg = (
                f"💰 NEW COLLECTION ADDED\n\n"
                f"Client Name : {client_name}\n"
                f"Branch      : {branch}\n"
                f"Created By  : {created_by}\n"
                f"Amount      : ₹{amount}\n"
                f"Date Created: {created_at.strftime('%d-%m-%Y %H:%M')}"
            )
            encoded = urllib.parse.quote(msg)
            url = (f"{WHATSAPP_API_URL}?secret={WHATSAPP_SECRET}"
                   f"&account={WHATSAPP_ACCOUNT}&recipient={recipient}"
                   f"&type=text&message={encoded}&priority=1")
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            logger.info("Collection WhatsApp sent to %s", recipient)
        except Exception as e:
            logger.error("WhatsApp failed for %s : %s", recipient, e)
# -------------------------------------------------
# -------------------------------------------------
@login_required
def collections_add(request):
    """Add new collection – client auto-complete + branch auto-fill."""
    clients = _load_clients()
    if request.method == "POST":
        client_name       = request.POST.get("client_name", "").strip()
        branch            = request.POST.get("branch", "").strip()
        amount            = request.POST.get("amount", "").strip()
        paid_for          = request.POST.get("paid_for", "").strip()
        collection_type   = request.POST.get("collection_type", "cash").strip()
        screenshot        = request.FILES.get("payment_screenshot")
        notes             = request.POST.get("notes", "").strip()
        status            = request.POST.get("status", "pending")  # default

        # basic required fields (screenshot NOT included here)
        if not all([client_name, branch, amount, paid_for]):
            return render(request, "collections_add.html", {
                "error": "Please fill all required fields.",
                "clients_json": clients,
            })

        try:
            amount = float(amount)
            if amount <= 0:
                raise ValueError("Amount must be greater than 0")

            # validate file only when needed
            if collection_type in ('online', 'cheque'):
                if not screenshot:
                    raise ValueError(f"Proof image is required for {collection_type.replace('_', ' ').title()}")
                allowed = {"image/jpeg", "image/jpg", "image/png", "image/gif"}
                if screenshot.content_type not in allowed:
                    raise ValueError("Only JPG / PNG / GIF images are allowed.")
                if screenshot.size > 5 * 1024 * 1024:
                    raise ValueError("File size must be less than 5 MB.")

            # create record
            collection = Collection.objects.create(
                client_name=client_name,
                branch=branch,
                amount=amount,
                paid_for=paid_for,
                collection_type=collection_type,
                payment_screenshot=screenshot or None,
                notes=notes or None,
                status=status,
                created_by=get_user_display_name(request.user)
            )

            # WhatsApp alert (unchanged)
            send_collection_whatsapp(
                client_name=collection.client_name,
                branch=collection.branch,
                created_by=collection.created_by,
                amount=collection.amount,
                created_at=collection.created_at
            )

            messages.success(request, f"Collection for {client_name} added successfully!")
            return redirect("collections_list")

        except ValueError as e:
            return render(request, "collections_add.html", {
                "error": str(e),
                "clients_json": clients,
            })
        except Exception as e:
            logger.error("Error saving collection: %s", e)
            return render(request, "collections_add.html", {
                "error": f"Error saving collection: {e}",
                "clients_json": clients,
            })

    return render(request, "collections_add.html", {"clients_json": clients})

def collections_list(request):
    """List all collections with search, filter, and status functionality"""
    # Get filter parameters
    search_query = request.GET.get('search', '').strip()
    branch_filter = request.GET.get('branch', '').strip()
    date_filter = request.GET.get('date_filter', '').strip()
    status_filter = request.GET.get('status_filter', '').strip()

    # Start with all collections
    collections = Collection.objects.all().order_by('-created_at')

    # Apply search filter
    if search_query:
        collections = collections.filter(
            Q(client_name__icontains=search_query) |
            Q(paid_for__icontains=search_query) |
            Q(notes__icontains=search_query)
        )
    
    # Apply branch filter
    if branch_filter:
        collections = collections.filter(branch__icontains=branch_filter)

    # Apply status filter
    if status_filter:
        collections = collections.filter(status=status_filter)

    # Apply date filter
    if date_filter:
        today = timezone.now().date()
        if date_filter == 'today':
            collections = collections.filter(created_at__date=today)
        elif date_filter == 'this_week':
            week_start = today - timedelta(days=today.weekday())
            collections = collections.filter(created_at__date__gte=week_start)
        elif date_filter == 'this_month':
            collections = collections.filter(
                created_at__year=today.year,
                created_at__month=today.month
            )
        elif date_filter == 'last_month':
            if today.month == 1:
                last_month_year = today.year - 1
                last_month_month = 12
            else:
                last_month_year = today.year
                last_month_month = today.month - 1
            collections = collections.filter(
                created_at__year=last_month_year,
                created_at__month=last_month_month
            )

    # Calculate statistics - USE FILTERED COLLECTIONS for accurate counts
    filtered_count = collections.count()
    filtered_total_amount = collections.aggregate(Sum('amount'))['amount__sum'] or 0
    
    # For "This Month" count, use the original unfiltered data but apply month filter
    today = timezone.now().date()
    this_month_count = Collection.objects.filter(
        created_at__year=today.year,
        created_at__month=today.month
    ).count()
    
    # Status statistics - use filtered collections for accuracy
    pending_count = collections.filter(status='pending').count()
    verified_count = collections.filter(status='verified').count()

    # Pagination
    paginator = Paginator(collections, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'collections_list.html', {
        'collections': page_obj,
        'total_amount': filtered_total_amount,
        'total_count': filtered_count,  # Add this for the total count card
        'this_month_count': this_month_count,
        'pending_count': pending_count,
        'verified_count': verified_count,
        'is_paginated': page_obj.has_other_pages(),
        'page_obj': page_obj,
    })

# Update collection_details to include status
def collection_details(request, collection_id):
    """Get collection details via AJAX"""
    try:
        collection = get_object_or_404(Collection, id=collection_id)
        
        return JsonResponse({
            'success': True,
            'id': collection.id,
            'client_name': collection.client_name,
            'branch': collection.branch,
            'amount': str(collection.amount),
            'paid_for': collection.paid_for,
            'notes': collection.notes or '',
            'status': collection.status,  # NEW
            'status_display': collection.get_status_display(),  # NEW
            'created_at': collection.created_at.strftime('%d %B %Y'),
            'created_time': collection.created_at.strftime('%H:%M'),
            'has_screenshot': bool(collection.payment_screenshot),
            'screenshot_url': collection.payment_screenshot.url if collection.payment_screenshot else None
        })
        
    except Exception as e:
        logger.error(f"Error getting collection details: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'Error loading details: {str(e)}'
        }, status=500)


def collection_details(request, collection_id):
    """Get collection details via AJAX"""
    try:
        collection = get_object_or_404(Collection, id=collection_id)
        
        return JsonResponse({
            'success': True,
            'id': collection.id,
            'client_name': collection.client_name,
            'branch': collection.branch,
            'amount': str(collection.amount),
            'paid_for': collection.paid_for,
            'notes': collection.notes or '',
            'created_at': collection.created_at.strftime('%d %B %Y'),
            'created_time': collection.created_at.strftime('%H:%M'),
            'has_screenshot': bool(collection.payment_screenshot),
            'screenshot_url': collection.payment_screenshot.url if collection.payment_screenshot else None
        })
        
    except Exception as e:
        logger.error(f"Error getting collection details: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'Error loading details: {str(e)}'
        }, status=500)

@login_required
@require_http_methods(["GET", "POST"])
def collections_edit(request, collection_id):
    """Edit collection record with client autocomplete functionality"""
    collection = get_object_or_404(Collection, id=collection_id)
    clients = _load_clients()

    if request.method == "POST":
        client_name        = request.POST.get("client_name", "").strip()
        branch             = request.POST.get("branch", "").strip()
        amount             = request.POST.get("amount", "").strip()
        paid_for           = request.POST.get("paid_for", "").strip()
        collection_type    = request.POST.get("collection_type", collection.collection_type).strip()
        payment_screenshot = request.FILES.get("payment_screenshot")
        notes              = request.POST.get("notes", "").strip()
        status             = request.POST.get("status", collection.status)

        # basic required fields (screenshot NOT included)
        if not all([client_name, branch, amount, paid_for]):
            return render(request, "collections_edit.html", {
                "collection": collection,
                "clients_json": clients,
                "error": "Please fill all required fields.",
            })

        try:
            amount = float(amount)
            if amount <= 0:
                raise ValueError("Amount must be greater than 0")

            # validate screenshot only when required
            requires_proof = collection_type in (Collection.TYPE_ONLINE, Collection.TYPE_CHEQUE)
            if requires_proof and not payment_screenshot and not collection.payment_screenshot:
                raise ValueError(f"Proof image is required for {collection_type.replace('_', ' ').title()}")

            if payment_screenshot:
                allowed = {"image/jpeg", "image/jpg", "image/png", "image/gif"}
                if payment_screenshot.content_type not in allowed:
                    raise ValueError("Only image files (JPG, PNG, GIF) are allowed")
                if payment_screenshot.size > 5 * 1024 * 1024:
                    raise ValueError("File size must be less than 5 MB")

                # delete old file if exists
                if collection.payment_screenshot and os.path.isfile(collection.payment_screenshot.path):
                    os.remove(collection.payment_screenshot.path)
                collection.payment_screenshot = payment_screenshot

            # update all fields
            collection.client_name      = client_name
            collection.branch           = branch
            collection.amount           = amount
            collection.paid_for         = paid_for
            collection.collection_type  = collection_type
            collection.notes            = notes or None
            collection.status           = status

            if not collection.created_by:
                collection.created_by = get_user_display_name(request.user)

            collection.save()
            messages.success(request, f"Collection for {client_name} updated successfully!")
            return redirect("collections_list")

        except ValueError as e:
            return render(request, "collections_edit.html", {
                "collection": collection,
                "clients_json": clients,
                "error": str(e),
            })
        except Exception as e:
            logger.error(f"Error updating collection: {str(e)}")
            return render(request, "collections_edit.html", {
                "collection": collection,
                "clients_json": clients,
                "error": f"Error updating collection: {str(e)}",
            })

    return render(request, "collections_edit.html", {
        "collection": collection,
        "clients_json": clients,
    })
@csrf_exempt
@require_http_methods(["POST"])
def collections_delete(request, collection_id):
    """Delete collection record via AJAX"""
    try:
        print(f"Attempting to delete collection ID: {collection_id}")  # Debug line
        logger.info(f"Delete request for collection ID: {collection_id}")
        
        collection = get_object_or_404(Collection, id=collection_id)
        client_name = collection.client_name
        
        # Delete associated file
        if collection.payment_screenshot:
            try:
                if os.path.isfile(collection.payment_screenshot.path):
                    os.remove(collection.payment_screenshot.path)
                    print(f"Deleted screenshot file for collection {collection_id}")
            except Exception as e:
                print(f"Error deleting screenshot file: {str(e)}")
                logger.error(f"Error deleting screenshot file: {str(e)}")
        
        collection.delete()
        print(f"Successfully deleted collection for {client_name}")  # Debug line
        logger.info(f"Successfully deleted collection for {client_name}")
        
        return JsonResponse({
            'success': True,
            'message': f'Collection for {client_name} deleted successfully'
        })
        
    except Exception as e:
        print(f"Error deleting collection: {str(e)}")  # Debug line
        logger.error(f"Error deleting collection: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'Error deleting collection: {str(e)}'
        }, status=500)
    
def collection_receipt(request, collection_id):
    """Generate and download receipt for collection"""
    try:
        collection = get_object_or_404(Collection, id=collection_id)
        
        # Create simple receipt content
        receipt_content = f"""
        =======================================
                    PAYMENT RECEIPT
        =======================================
        
        Receipt No: COL-{collection.id:06d}
        Date: {collection.created_at.strftime('%d %B %Y, %H:%M')}
        
        ---------------------------------------
        CLIENT DETAILS
        ---------------------------------------
        Name: {collection.client_name}
        Branch: {collection.branch}
        
        ---------------------------------------
        PAYMENT DETAILS
        ---------------------------------------
        Amount Paid: ₹{collection.amount}
        Paid For: {collection.paid_for}
        
        {f'Notes: {collection.notes}' if collection.notes else ''}
        
        ---------------------------------------
        
        This is a computer-generated receipt.
        
        Thank you for your payment!
        
        =======================================
        """
        
        response = HttpResponse(receipt_content, content_type='text/plain')
        response['Content-Disposition'] = f'attachment; filename="Receipt-{collection.client_name}-{collection.id}.txt"'
        
        return response
        
    except Exception as e:
        logger.error(f"Error generating receipt: {str(e)}")
        messages.error(request, f'Error generating receipt: {str(e)}')
        return redirect('collections_list')
    
def get_user_display_name(user):
    """Get the best display name for a user"""
    if not user or not user.is_authenticated:
        return "Anonymous User"
    
    # Try full name first
    if hasattr(user, 'get_full_name'):
        full_name = user.get_full_name()
        if full_name and full_name.strip():
            return full_name.strip()
    
    # Try first + last name
    if hasattr(user, 'first_name') and user.first_name:
        first_name = user.first_name.strip()
        if hasattr(user, 'last_name') and user.last_name:
            last_name = user.last_name.strip()
            if last_name:
                return f"{first_name} {last_name}"
        return first_name
    
    # Fall back to username
    if hasattr(user, 'username'):
        return user.username
    
    return "Unknown User"

@csrf_exempt
@require_http_methods(["POST"])
def collection_update_status(request, collection_id):
    """Update collection status (pending/verified)"""
    try:
        collection = get_object_or_404(Collection, id=collection_id)
        
        # Parse JSON data
        data = json.loads(request.body)
        new_status = data.get('status')
        
        if new_status not in ['pending', 'verified']:
            return JsonResponse({'success': False, 'message': 'Invalid status'})
        
        collection.status = new_status
        collection.save()
        
        return JsonResponse({
            'success': True, 
            'message': f'Status updated to {new_status} successfully'
        })
        
    except Collection.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Collection not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Error: {str(e)}'})

from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
import json

# ---------- API: Add new collection (POST) ----------
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from django.conf import settings
import os
import logging

logger = logging.getLogger(__name__)

# ---------- API: Add new collection (POST with image) ----------
@csrf_exempt
@require_http_methods(["POST"])
def api_collections_add(request):
    try:
        client_name = request.POST.get("client_name", "").strip()
        branch      = request.POST.get("branch", "").strip()
        amount      = request.POST.get("amount", "").strip()
        paid_for    = request.POST.get("paid_for", "").strip()
        notes       = request.POST.get("notes", "").strip()
        screenshot  = request.FILES.get("payment_screenshot")

        # --- validation identical to your current code ---
        if not all([client_name, branch, amount, paid_for, screenshot]):
            return JsonResponse(
                {"success": False, "error": "All fields including screenshot are required"},
                status=400
            )
        try:
            amount = float(amount)
            if amount <= 0:
                raise ValueError("Amount must be positive")
        except ValueError as e:
            return JsonResponse({"success": False, "error": str(e)}, status=400)

        allowed = {"image/jpeg", "image/jpg", "image/png", "image/gif"}
        if screenshot.content_type not in allowed:
            return JsonResponse({"success": False, "error": "Only JPG, PNG, GIF images allowed"}, status=400)
        if screenshot.size > 5 * 1024 * 1024:
            return JsonResponse({"success": False, "error": "File size must be < 5 MB"}, status=400)

        # --- save ---
        collection = Collection.objects.create(
            client_name=client_name,
            branch=branch,
            amount=amount,
            paid_for=paid_for,
            payment_screenshot=screenshot,
            notes=notes or None,
            created_by="API"          # mark origin
        )

        # >>>>>>  WhatsApp alert (branch included)  <<<<<<
        send_collection_whatsapp(
            client_name=collection.client_name,
            branch=collection.branch,
            created_by=collection.created_by,
            amount=collection.amount,
            created_at=collection.created_at
        )

        return JsonResponse({
            "success": True,
            "message": "Collection added successfully",
            "data": {
                "id": collection.id,
                "client_name": collection.client_name,
                "branch": collection.branch,
                "amount": str(collection.amount),
                "paid_for": collection.paid_for,
                "notes": collection.notes,
                "created_at": collection.created_at.strftime("%Y-%m-%d %H:%M"),
                "screenshot_url": collection.payment_screenshot.url if collection.payment_screenshot else None,
            }
        }, status=201)

    except Exception as e:
        logger.error(f"API error adding collection: {e}")
        return JsonResponse({"success": False, "error": str(e)}, status=500)


# ---------- API: Get all collections (GET) ----------
@require_http_methods(["GET"])
def api_collections_list(request):
    try:
        collections = Collection.objects.all().order_by("-created_at")
        data = [
            {
                "id": c.id,
                "client_name": c.client_name,
                "branch": c.branch,
                "amount": str(c.amount),
                "paid_for": c.paid_for,
                "notes": c.notes,
                "created_at": c.created_at.strftime("%Y-%m-%d %H:%M"),
                "screenshot_url": c.payment_screenshot.url if c.payment_screenshot else None,
            }
            for c in collections
        ]
        return JsonResponse({"success": True, "count": len(data), "data": data})
    except Exception as e:
        logger.error(f"API error fetching collections: {e}")
        return JsonResponse({"success": False, "error": str(e)}, status=500)





# http://127.0.0.1:8000/app4/api/collections/

#http://127.0.0.1:8000/app4/api/collections/add/


# {
#   "client_name": "John Doe",
#   "branch": "Kochi",
#   "amount": "1200.50",
#   "paid_for": "Annual Subscription",
#   "notes": "First collection entry"
# }