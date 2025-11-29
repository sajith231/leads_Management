# public_folder/views.py
import os
import requests
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from django.http import FileResponse, HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q
from datetime import datetime

from .models import PublicUpload

# Setup logging
logger = logging.getLogger(__name__)

# Decorator for public views
def public_view(view_func):
    view_func.is_public = True
    return view_func

# ---------------------------
# Public upload (no login required)
# ---------------------------
@public_view
@csrf_protect
def public_upload(request):
    """
    GET: show form
    POST: accept single file, plus optional fields: provided_name, description, client_name
    """
    message = None
    errors = []

    if request.method == "POST":
        uploaded = request.FILES.get("file")
        client_name = (request.POST.get("client_name") or "").strip()
        provided_name = (request.POST.get("provided_name") or "").strip()
        description = (request.POST.get("description") or "").strip()

        if not uploaded:
            errors.append("No file selected.")
        else:
            # Save model instance
            inst = PublicUpload.objects.create(
                file=uploaded,
                provided_name=provided_name,
                original_name=getattr(uploaded, "name", ""),
                description=description,
                client_name=client_name,
            )
            message = "Upload successful."
            return render(request, "public_upload.html", {"message": message})

    return render(request, "public_upload.html", {"message": message, "errors": errors})


# ---------------------------
# Public list (public view with filters and pagination)
# ---------------------------
@public_view
def public_list(request):
    # Get all files
    files = PublicUpload.objects.all()
    
    # Get filter parameters
    search_query = request.GET.get('search', '').strip()
    date_from = request.GET.get('date_from', '').strip()
    date_to = request.GET.get('date_to', '').strip()
    
    # Apply search filter
    if search_query:
        files = files.filter(
            Q(client_name__icontains=search_query) |
            Q(provided_name__icontains=search_query) |
            Q(original_name__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    
    # Apply date filters
    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d')
            files = files.filter(uploaded_at__gte=date_from_obj)
        except ValueError:
            pass
    
    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d')
            # Add one day to include the entire end date
            from datetime import timedelta
            date_to_obj = date_to_obj + timedelta(days=1)
            files = files.filter(uploaded_at__lt=date_to_obj)
        except ValueError:
            pass
    
    # Order by latest first
    files = files.order_by('-uploaded_at')
    
    # Pagination
    page = request.GET.get('page', 1)
    paginator = Paginator(files, 10)  # Show 10 files per page
    
    try:
        files_page = paginator.page(page)
    except PageNotAnInteger:
        files_page = paginator.page(1)
    except EmptyPage:
        files_page = paginator.page(paginator.num_pages)
    
    context = {
        'files': files_page,
        'search_query': search_query,
        'date_from': date_from,
        'date_to': date_to,
        'total_count': paginator.count,
    }
    
    return render(request, "public_list.html", context)


# ---------------------------
# Download file
# ---------------------------
@public_view
def download_file(request, file_id):
    inst = get_object_or_404(PublicUpload, id=file_id)
    file_path = inst.file.path
    if not os.path.exists(file_path):
        return HttpResponse("File not found.", status=404)
    suggested = inst.provided_name or inst.original_name or os.path.basename(inst.file.name)
    response = FileResponse(open(file_path, "rb"), as_attachment=True, filename=suggested)
    return response


# ---------------------------
# Delete file (POST only)
# ---------------------------
@require_POST
@public_view
@csrf_protect
def delete_file(request, file_id):
    inst = get_object_or_404(PublicUpload, id=file_id)
    try:
        inst.file.delete(save=False)
    except Exception as e:
        logger.error(f"Error deleting file: {e}")
    inst.delete()
    return redirect("public_list")


# ---------------------------
# Send WhatsApp Message (AJAX endpoint)
# ---------------------------
@public_view
@csrf_protect
@require_POST
def send_whatsapp(request):
    """
    Sends upload link via WhatsApp API
    Expects: phone_number in POST data
    """
    try:
        phone_number = request.POST.get('phone_number', '').strip()
        
        if not phone_number:
            return JsonResponse({
                'success': False, 
                'error': 'Phone number is required'
            }, status=400)
        
        # Clean phone number - remove spaces, dashes, parentheses
        phone_number = ''.join(filter(str.isdigit, phone_number))
        
        if not phone_number:
            return JsonResponse({
                'success': False, 
                'error': 'Invalid phone number format'
            }, status=400)
        
        # WhatsApp API Configuration
        WHATSAPP_API_URL = 'https://app.dxing.in/api/send/whatsapp'
        SECRET = '7b8ae820ecb39f8d173d57b51e1fce4c023e359e'
        ACCOUNT = '1761365422812b4ba287f5ee0bc9d43bbf5bbe87fb68fc4daea92d8'
        
        # Get upload URL
        upload_url = request.build_absolute_uri('/public_folder/public-upload/')
        
        # Message content
        message = (
            f"📤 Upload Your Files Here\n\n"
            f"Please use this link to upload your documents:\n"
            f"{upload_url}\n\n"
            f"Thank you!"
        )
        
        # Prepare API parameters
        params = {
            'secret': SECRET,
            'account': ACCOUNT,
            'recipient': phone_number,
            'type': 'text',
            'message': message,
            'priority': '1'
        }
        
        # Log the request
        logger.info(f"Sending WhatsApp message to {phone_number}")
        
        # Send POST request to WhatsApp API
        response = requests.post(
            WHATSAPP_API_URL, 
            params=params, 
            timeout=15
        )
        
        # Log response
        logger.info(f"WhatsApp API Response Status: {response.status_code}")
        logger.info(f"WhatsApp API Response: {response.text}")
        
        if response.status_code == 200:
            return JsonResponse({
                'success': True,
                'message': f'Link sent successfully to {phone_number}'
            })
        else:
            error_message = f'Failed to send. Status: {response.status_code}'
            try:
                error_data = response.json()
                error_message = error_data.get('message', error_message)
            except:
                pass
            
            return JsonResponse({
                'success': False,
                'error': error_message
            }, status=response.status_code)
            
    except requests.Timeout:
        logger.error("WhatsApp API request timeout")
        return JsonResponse({
            'success': False,
            'error': 'Request timeout. Please try again.'
        }, status=408)
        
    except requests.RequestException as e:
        logger.error(f"WhatsApp API request error: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'Network error: Unable to reach WhatsApp service'
        }, status=503)
        
    except Exception as e:
        logger.error(f"Unexpected error in send_whatsapp: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'An unexpected error occurred. Please try again.'
        }, status=500)