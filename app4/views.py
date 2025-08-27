import base64
import requests  # ADD THIS IMPORT
import logging
import json
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



def key_request(request):
    branches = Branch.objects.all()
    
    if request.method == "POST":
        clientName  = request.POST.get("clientName")
        location    = request.POST.get("location")
        keyType     = request.POST.get("keyType")
        requestDate = request.POST.get("requestDate")
        description = request.POST.get("description", "")
        branch_id   = request.POST.get("branch")
        amount      = request.POST.get("amount", "").strip()
        requestImage = request.FILES.get("requestImage")

        # Convert requestDate safely
        try:
            if requestDate:
                requestDate = datetime.strptime(requestDate, "%Y-%m-%d").date()
            else:
                requestDate = date.today()
        except ValueError:
            messages.error(request, "Invalid date format")
            return render(request, "key_request.html", {"branches": branches})

        if not (clientName and location and keyType and requestDate):
            messages.error(request, "Please fill all required fields")
            return render(request, "key_request.html", {"branches": branches})

        # Build description with dynamic field data
        description_parts = [description] if description else []
        
        if keyType == "Seat Upgradation Request":
            current_seats = request.POST.get('currentSeats')
            required_seats = request.POST.get('requiredSeats')
            if current_seats or required_seats:
                description_parts.append(f"Seats: {current_seats or 'N/A'} → {required_seats or 'N/A'}")
                
        elif keyType == "Maturity Upgradation Request":
            current_maturity = request.POST.get('currentMaturity')
            required_maturity = request.POST.get('requiredMaturity')
            if current_maturity or required_maturity:
                description_parts.append(f"Maturity: {current_maturity or 'N/A'} → {required_maturity or 'N/A'}")
                
        elif keyType == "More Module Request":
            module = request.POST.get('module')
            if module:
                description_parts.append(f"Module: {module}")
                
        elif keyType == "Software Amount Change Request":
            current_amount = request.POST.get('currentAmount')
            required_amount = request.POST.get('requiredAmount')
            if current_amount or required_amount:
                description_parts.append(f"Amount Change: ₹{current_amount or 'N/A'} → ₹{required_amount or 'N/A'}")
                
        elif keyType == "Demo Key Request":
            task = request.POST.get('task')
            bcare = request.POST.get('bcare')
            icare = request.POST.get('icare')
            demo_parts = []
            if task: demo_parts.append(f"Task: {task}")
            if bcare: demo_parts.append(f"B-Care: {bcare}")
            if icare: demo_parts.append(f"I-Care: {icare}")
            if demo_parts:
                description_parts.append(" | ".join(demo_parts))
                
        elif keyType == "Hosted Key Request":
            server_details = request.POST.get('serverDetails')
            if server_details:
                description_parts.append(f"Server Details: {server_details}")
                
        elif keyType == "Feeder Cancellation Request":
            cancel_reason = request.POST.get('cancelReason')
            if cancel_reason:
                description_parts.append(f"Cancellation Reason: {cancel_reason}")
                
        elif keyType == "Key Extension Request":
            extension_period = request.POST.get('extensionPeriod')
            if extension_period:
                description_parts.append(f"Extension Period: {extension_period}")
                
        elif keyType == "Trade Name And Address Change Request":
            new_firm_name = request.POST.get('newFirmName')
            new_address = request.POST.get('newAddress')
            change_parts = []
            if new_firm_name: change_parts.append(f"New Firm: {new_firm_name}")
            if new_address: change_parts.append(f"New Address: {new_address}")
            if change_parts:
                description_parts.append(" | ".join(change_parts))
                
        elif keyType == "Key type Change Request":
            current_key_type = request.POST.get('currentKeyType')
            required_key_type = request.POST.get('requiredKeyType')
            if current_key_type or required_key_type:
                description_parts.append(f"Key Type: {current_key_type or 'N/A'} → {required_key_type or 'N/A'}")
                
        elif keyType == "Enterprises Key Request":
            enterprise_details = request.POST.get('enterpriseDetails')
            if enterprise_details:
                description_parts.append(f"Enterprise Details: {enterprise_details}")

        final_description = "\n".join(description_parts)

        # Create KeyRequest object
        key_request_obj = KeyRequest(
            clientName=clientName,
            location=location,
            description=final_description,
            keyType=keyType,
            requestDate=requestDate,
            status="Pending",
            amount=amount if amount else None
        )
        
        # Set branch if provided
        if branch_id:
            try:
                branch = Branch.objects.get(id=branch_id)
                key_request_obj.branch = branch
            except Branch.DoesNotExist:
                pass

        # Handle image upload
        if requestImage:
            key_request_obj.requestImage = requestImage

        try:
            key_request_obj.save()
            messages.success(request, "Key request submitted successfully!")
            return redirect("key_request_list")
        except Exception as e:
            messages.error(request, f"Error saving request: {str(e)}")
            return render(request, "key_request.html", {"branches": branches})

    return render(request, "key_request.html", {"branches": branches})

def key_request_list(request):
    key_requests = KeyRequest.objects.select_related('branch').all().order_by('-id')
    branches = Branch.objects.all()
    return render(request, "key_request_list.html", {
        "key_requests": key_requests,
        "branches": branches
    })

def key_request_edit(request, request_id):
    key_request_obj = get_object_or_404(KeyRequest, id=request_id)
    branches = Branch.objects.all()
    
    if request.method == "POST":
        clientName = request.POST.get("clientName")
        location = request.POST.get("location")
        keyType = request.POST.get("keyType")
        req_date = request.POST.get("requestDate")
        branch_id = request.POST.get("branch")
        amount = request.POST.get("amount", "").strip()

        if req_date:
            try:
                key_request_obj.requestDate = datetime.strptime(req_date, "%Y-%m-%d").date()
            except ValueError:
                messages.error(request, "Invalid date format")
                return render(request, "key_request_edit.html", {
                    "key_request": key_request_obj,
                    "branches": branches
                })

        if 'requestImage' in request.FILES:
            key_request_obj.requestImage = request.FILES['requestImage']

        # Build description with dynamic field data (same logic as create)
        description = request.POST.get("description", "")
        description_parts = [description] if description else []
        
        # ... (same dynamic field logic as in create view)
        
        key_request_obj.clientName = clientName
        key_request_obj.location = location
        key_request_obj.keyType = keyType
        key_request_obj.description = "\n".join(description_parts)
        key_request_obj.amount = amount if amount else None
        
        # Set branch
        if branch_id:
            try:
                branch = Branch.objects.get(id=branch_id)
                key_request_obj.branch = branch
            except Branch.DoesNotExist:
                key_request_obj.branch = None
        else:
            key_request_obj.branch = None
        
        key_request_obj.save()
        messages.success(request, "Key request updated successfully!")
        return redirect("key_request_list")

    return render(request, "key_request_edit.html", {
        "key_request": key_request_obj,
        "branches": branches
    })

def key_request_delete(request, request_id):
    key_request_obj = get_object_or_404(KeyRequest, id=request_id)
    key_request_obj.delete()
    messages.success(request, "Key request deleted successfully!")
    return redirect("key_request_list")

@csrf_exempt
@require_http_methods(["POST"])
def update_key_request_status(request, request_id):
    """Update the status of a key request via AJAX"""
    try:
        key_request_obj = get_object_or_404(KeyRequest, id=request_id)
        data = json.loads(request.body)
        new_status = data.get('status')
        
        # Define valid status choices if not in model
        valid_statuses = ['Pending', 'On Process', 'Accepted', 'Rejected']
        
        if new_status in valid_statuses:
            key_request_obj.status = new_status
            key_request_obj.save()
            logger.info(f"Status updated for request {request_id}: {new_status}")
            return JsonResponse({'success': True, 'message': 'Status updated successfully'})
        else:
            logger.warning(f"Invalid status attempted for request {request_id}: {new_status}")
            return JsonResponse({'success': False, 'message': f'Invalid status: {new_status}. Valid options: {", ".join(valid_statuses)}'}, status=400)
            
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error in status update: {str(e)}")
        return JsonResponse({'success': False, 'message': 'Invalid JSON data'}, status=400)
    except Exception as e:
        logger.error(f"Error updating key request status: {str(e)}")
        return JsonResponse({'success': False, 'message': f'Server error: {str(e)}'}, status=500)

def clients_proxy(request):
    """Proxy endpoint to fetch clients from external API"""
    url = "https://accmaster.imcbs.com/api/sync/rrc-clients/"
    try:
        resp = requests.get(
            url,
            headers={"Accept": "application/json"},
            timeout=10
        )
        resp.raise_for_status()
        return JsonResponse(resp.json(), safe=False)
    except Exception as e:
        logger.error(f"Error fetching clients: {str(e)}")
        return JsonResponse({"error": str(e)}, status=500)
