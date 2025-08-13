import base64
import requests  # ADD THIS IMPORT
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.core.exceptions import ValidationError
from app1.models import Branch
from .models import License, KeyRequest

# Set up logging
logger = logging.getLogger(__name__)

# ------------------------
# License Views
# ------------------------

def license_type_view(request):
    licenses = License.objects.select_related('branch').all().order_by('-id')
    branches = Branch.objects.all()
    return render(request, 'license_type.html', {
        'licenses': licenses,
        'branches': branches
    })


@require_http_methods(["GET", "POST"])
def add_license_view(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        branch_id = request.POST.get('branch')
        uploaded_file = request.FILES.get('license_file')

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
            name=name,
            branch_id=branch_id,
            license_key=b64,
            file_name=uploaded_file.name
        )
        return redirect('license_type')

    return render(request, 'add_license.html', {'branches': Branch.objects.all()})


def _get_bytes_from_stored(license_obj):
    stored = license_obj.license_key or ''
    try:
        return base64.b64decode(stored)
    except Exception:
        return stored.encode('utf-8', errors='replace')


def license_download(request, license_id):
    license_obj = get_object_or_404(License, id=license_id)
    file_bytes = _get_bytes_from_stored(license_obj)

    response = HttpResponse(file_bytes, content_type='application/octet-stream')
    filename = license_obj.file_name or f"{license_obj.name}.txt"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    response['Content-Length'] = str(len(file_bytes))
    return response


def license_preview(request, license_id):
    license_obj = get_object_or_404(License, id=license_id)
    file_bytes = _get_bytes_from_stored(license_obj)
    decoded_text = file_bytes.decode('utf-8', errors='replace')

    payload = {
        'id': license_obj.id,
        'name': license_obj.name,
        'branch': license_obj.branch.name,
        'created_at': license_obj.created_at.strftime('%d-%m-%Y'),
        'file_name': license_obj.file_name,
        'content': decoded_text
    }
    return JsonResponse(payload)


@require_http_methods(["GET", "POST"])
def license_edit(request, license_id):
    license_obj = get_object_or_404(License, id=license_id)

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        branch_id = request.POST.get('branch')
        uploaded_file = request.FILES.get('license_file')

        if name:
            license_obj.name = name

        if branch_id:
            license_obj.branch_id = branch_id

        if uploaded_file:
            if not uploaded_file.name.lower().endswith('.txt'):
                return render(request, 'license_edit.html', {
                    'license': license_obj,
                    'branches': Branch.objects.all(),
                    'error': 'Only .txt files allowed for replacement.'
                })
            file_bytes = uploaded_file.read()
            license_obj.license_key = base64.b64encode(file_bytes).decode('ascii')
            license_obj.file_name = uploaded_file.name

        license_obj.save()
        return redirect('license_type')

    return render(request, 'license_edit.html', {
        'license': license_obj,
        'branches': Branch.objects.all()
    })


@require_http_methods(["POST"])
def license_delete(request, license_id):
    license_obj = get_object_or_404(License, id=license_id)
    license_obj.delete()
    return redirect('license_type')


# ------------------------
# Key Request Views (FIXED)
# ------------------------

@require_http_methods(["GET", "POST"])
def key_request_view(request):
    if request.method == "POST":
        try:
            # Collect POST data with debug logging
            client_id = request.POST.get('client_id', '').strip()
            client_name = request.POST.get('client_name', '').strip()
            request_title = request.POST.get('request_title', '').strip()
            image_file = request.FILES.get('image_file')
            additional_requests = request.POST.get('additional_requests', '').strip()
            comments = request.POST.get('comments', '').strip()

            # Debug logging
            logger.info(f"Key Request Submission Data:")
            logger.info(f"client_id: '{client_id}'")
            logger.info(f"client_name: '{client_name}'")
            logger.info(f"request_title: '{request_title}'")
            logger.info(f"image_file: {image_file}")
            logger.info(f"additional_requests: '{additional_requests}'")
            logger.info(f"comments: '{comments}'")

            # Validate required fields
            if not request_title:
                messages.error(request, 'Request title is required.')
                return render(request, 'key_request.html')

            # Convert client_id to integer if it's not empty
            client_id_int = 0
            if client_id:
                try:
                    client_id_int = int(client_id)
                except (ValueError, TypeError):
                    logger.warning(f"Invalid client_id: {client_id}, using 0")
                    client_id_int = 0

            # Create Key Request entry
            key_request = KeyRequest.objects.create(
                client_id=client_id_int,
                client_name=client_name,
                request_title=request_title,
                image_file=image_file,
                additional_requests=additional_requests,
                comments=comments
            )

            logger.info(f"Key request created successfully with ID: {key_request.id}")
            messages.success(request, f'Key request "{request_title}" submitted successfully!')

        except Exception as e:
            logger.error(f'Error creating key request: {str(e)}', exc_info=True)
            messages.error(request, f'Error submitting request: {str(e)}')
            return render(request, 'key_request.html')

        # Always redirect to list after successful POST
        return redirect('key_request_list')

    # GET request - show the form
    return render(request, 'key_request.html')


def key_request_list_view(request):
    key_requests = []
    try:
        # Fetch all requests with debug info
        all_requests = KeyRequest.objects.all().order_by('-created_at')
        logger.info(f"Found {all_requests.count()} key requests in database")

        for req in all_requests:
            try:
                # Safely split additional requests
                if req.additional_requests:
                    req.additional_requests_list = [
                        r.strip() for r in req.additional_requests.split(',') 
                        if r.strip()
                    ]
                else:
                    req.additional_requests_list = []
                
                logger.debug(f"Processing request ID {req.id}: {req.request_title}")
                
            except Exception as e:
                logger.warning(f'Error processing additional_requests for ID {req.id}: {e}')
                req.additional_requests_list = []
            
            key_requests.append(req)

        logger.info(f"Successfully processed {len(key_requests)} key requests for display")

    except Exception as e:
        logger.error(f'Error fetching key requests list: {e}', exc_info=True)
        messages.error(request, 'An error occurred while loading key requests.')

    return render(request, 'key_request_list.html', {
        'key_requests': key_requests
    })

@require_http_methods(["GET"])
def get_clients(request):
    """
    Proxy endpoint to fetch clients from external API
    Returns properly formatted client data for the dropdown
    """
    try:
        # Make request to external API
        response = requests.get(
            'https://accmaster.imcbs.com/api/sync/rrc-clients/',
            timeout=30
        )
        response.raise_for_status()
        
        # Parse JSON response
        clients_data = response.json()
        
        # The API directly returns a list of clients
        if isinstance(clients_data, list):
            # Return the data as-is since it's already in the correct format
            # Each client has 'code' as ID and 'name' as display name
            return JsonResponse(clients_data, safe=False)
        
        # Handle case if data is wrapped in an object
        elif isinstance(clients_data, dict):
            # Check if data is in a 'data' or 'clients' field
            if 'data' in clients_data and isinstance(clients_data['data'], list):
                return JsonResponse(clients_data['data'], safe=False)
            elif 'clients' in clients_data and isinstance(clients_data['clients'], list):
                return JsonResponse(clients_data['clients'], safe=False)
            else:
                return JsonResponse({'error': 'Unexpected API response format'}, status=500)
        
        else:
            return JsonResponse({'error': 'Invalid API response format'}, status=500)
            
    except requests.Timeout:
        return JsonResponse({'error': 'Request timeout'}, status=504)
    except requests.ConnectionError:
        return JsonResponse({'error': 'Unable to connect to API'}, status=503)
    except Exception as e:
        logger.error(f'Error fetching clients: {str(e)}')
        return JsonResponse({'error': 'Failed to fetch clients'}, status=500)