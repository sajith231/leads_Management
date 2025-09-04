import base64
import requests  # ADD THIS IMPORT
import logging
import json
import requests
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.core.exceptions import ValidationError
from app1.models import Branch
from datetime import datetime, date
from datetime import datetime, date
from .models import License, KeyRequest 
from django.views.decorators.csrf import csrf_exempt

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

def key_request(request):
    branches = Branch.objects.all()

    if request.method == "POST":
        # Required fields
        clientName   = request.POST.get("clientName")
        location     = request.POST.get("location")   # client's entered location
        keyType      = request.POST.get("keyType")
        requestDate  = request.POST.get("requestDate")

        # Optional fields
        branch_name  = request.POST.get("branch", "").strip()  # Now just store as text
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

        # Create object
        key_request_obj = KeyRequest(
            clientName=clientName,
            location=location,  # client-entered value
            description=final_description,
            keyType=keyType,
            requestDate=requestDate,
            status="Pending",
            amount=amount if amount else None,
            branch_name=branch_name  # Store branch name as text
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
            messages.success(request, "Key request submitted successfully!")
            return redirect("key_request_list")
        except Exception as e:
            logger.error(f"Error saving key request: {str(e)}")
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

            # Handle dynamic fields based on keyType
            if keyType == "Seat Upgradation Request":
                key_request_obj.currentSeats = request.POST.get('currentSeats', '')
                key_request_obj.requiredSeats = request.POST.get('requiredSeats', '')
                
            elif keyType == "More Module Request":
                key_request_obj.module = request.POST.get('module', '')
                
            elif keyType == "Trade Name And Address Change Request":
                key_request_obj.newFirmName = request.POST.get('newFirmName', '')
                key_request_obj.newAddress = request.POST.get('newAddress', '')
                
            elif keyType == "Key type Change Request":
                key_request_obj.currentKeyType = request.POST.get('currentKeyType', '')
                key_request_obj.requiredKeyType = request.POST.get('requiredKeyType', '')
                
            elif keyType == "Key Extension Request":
                key_request_obj.extensionPeriod = request.POST.get('extensionPeriod', '')
                
            elif keyType == "Hosted Key Request":
                key_request_obj.serverDetails = request.POST.get('serverDetails', '')
                
            elif keyType == "Feeder Cancellation Request":
                key_request_obj.cancelReason = request.POST.get('cancelReason', '')
                
            elif keyType == "Demo Key Request":
                key_request_obj.task = request.POST.get('task', '')
                key_request_obj.bcare = request.POST.get('bcare', '')
                key_request_obj.icare = request.POST.get('icare', '')
                
            elif keyType == "Software Amount Change Request":
                key_request_obj.currentAmount = request.POST.get('currentAmount', '')
                key_request_obj.requiredAmount = request.POST.get('requiredAmount', '')
                # Handle software amount image
                if 'softwareAmountImage' in request.FILES:
                    key_request_obj.softwareAmountImage = request.FILES['softwareAmountImage']
                    
            elif keyType == "Maturity Upgradation Request":
                key_request_obj.currentMaturity = request.POST.get('currentMaturity', '')
                key_request_obj.requiredMaturity = request.POST.get('requiredMaturity', '')
                
            elif keyType == "Enterprises Key Request":
                key_request_obj.enterpriseDetails = request.POST.get('enterpriseDetails', '')
                
            elif keyType == "Special Updation Request":
                key_request_obj.specialUpdateDetails = request.POST.get('specialUpdateDetails', '')

            # Handle image upload for Image Request
            if keyType == "Image Request":
                if 'requestImage' in request.FILES:
                    key_request_obj.requestImage = request.FILES['requestImage']
                    
                # Handle GPS data
                gps_lat = request.POST.get("gps_lat", "").strip()
                gps_lon = request.POST.get("gps_lon", "").strip()
                if gps_lat and gps_lon:
                    key_request_obj.gps_lat = gps_lat
                    key_request_obj.gps_lon = gps_lon
                    key_request_obj.gps_location = f"{gps_lat}, {gps_lon}"
                    key_request_obj.gps_address = reverse_geocode(gps_lat, gps_lon)

            # Handle general request image
            elif 'requestImage' in request.FILES:
                key_request_obj.requestImage = request.FILES['requestImage']

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
            'Rejected',
            'Working on it', 
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