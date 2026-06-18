from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse
import urllib.request
import urllib.parse
import json
import logging

from rest_framework.decorators import api_view, parser_classes, authentication_classes
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response
from rest_framework import status

from .models import Collection
from .forms import CollectionForm
from .serializers import CollectionSerializer
from common.cloudflare_storage import upload_to_cloudflare, delete_from_cloudflare

logger = logging.getLogger(__name__)


# ── Acc-Master client IDs per company ────────────────────────────────────────
ACC_API_URL      = 'https://accmaster.imcbs.com/api/sync/acc-master/'
ACC_DEPT_API_URL = 'https://accmaster.imcbs.com/api/sync/acc-departments/'

COMPANY_CLIENT_IDS = {
    'Sysmac Computers': 'GW9Q6NQQ5ONRU',
    'Sysmac Info':      '69ZHSXOIMFA6T',
    'IMCB LLP':         'G9SYCSM54HR3E',
}

# In-process cache — key '__all__' for dept map, company name for clients
_DEPT_CACHE   = {}
_CLIENT_CACHE = {}


def fetch_departments(force=False):
    """
    Fetch ALL departments from acc-departments API with NO params.
    The API returns a fixed global list (client_id NTS04WC95G3U4 for all rows).

    department_id  ↔  openingdepartment in client API  (e.g. "DF" -> "IMC HO")

    Returns dict: {department_id: department_name}
    """
    if not force and '__all__' in _DEPT_CACHE and _DEPT_CACHE['__all__']:
        return _DEPT_CACHE['__all__']

    try:
        with urllib.request.urlopen(ACC_DEPT_API_URL, timeout=10) as resp:
            data = json.loads(resp.read().decode())

        items = data if isinstance(data, list) else data.get('results', data.get('data', []))
        dept_map = {}
        for d in items:
            dept_id   = str(d.get('department_id', '')).strip()
            dept_name = str(d.get('department',    '')).strip()
            if dept_id and dept_name:
                dept_map[dept_id] = dept_name

        if dept_map:                          # only cache on success
            _DEPT_CACHE['__all__'] = dept_map
        return dept_map
    except Exception as e:
        print(f"Error fetching departments: {e}")
        return _DEPT_CACHE.get('__all__', {})  # return last good cache if any


def fetch_raw_clients(company, force=False):
    """
    Fetch raw client list for a company using that company's client_id.
    openingdepartment in each client = department_id in dept API.
    Returns list of raw client dicts (openingdepartment still as ID e.g. "DF").
    """
    if not force and company in _CLIENT_CACHE and _CLIENT_CACHE[company]:
        return _CLIENT_CACHE[company]

    client_id = COMPANY_CLIENT_IDS.get(company)
    if not client_id:
        return []

    url = f'{ACC_API_URL}?client_id={urllib.parse.quote(client_id)}'
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        clients = data if isinstance(data, list) else data.get('results', data.get('data', []))
        if clients:
            _CLIENT_CACHE[company] = clients
        return clients
    except Exception as e:
        print(f"Error fetching clients for {company}: {e}")
        return _CLIENT_CACHE.get(company, [])


@login_required
def acc_departments_proxy(request):
    """
    GET /acc-dept-proxy/?company=Sysmac+Computers
    Returns ALL departments from the dept API as [{id, name}, ...] sorted by name.
    The dept API is a global list — all departments are valid for any company.
    Client openingdepartment = department_id in dept API.
    """
    company = request.GET.get('company', '').strip()
    if not company:
        return JsonResponse({'error': 'company param required'}, status=400)

    if company not in COMPANY_CLIENT_IDS:
        return JsonResponse({'error': 'Unknown company'}, status=400)

    dept_map = fetch_departments()

    result = sorted(
        [{'id': did, 'name': name} for did, name in dept_map.items()],
        key=lambda x: x['name']
    )
    return JsonResponse(result, safe=False)




@login_required
def acc_master_proxy(request):
    """
    GET /acc-proxy/?company=Sysmac+Computers
    Returns client list with openingdepartment replaced by department name.
    Response: [{name, openingdepartment: "IMC HO", ...}, ...]
    """
    company = request.GET.get('company', '').strip()
    if not company:
        return JsonResponse({'error': 'company param required'}, status=400)

    dept_map = fetch_departments()
    clients  = fetch_raw_clients(company)

    processed = []
    for c in clients:
        row     = dict(c)
        dept_id = str(row.get('openingdepartment', '')).strip()
        row['openingdepartment'] = dept_map.get(dept_id, dept_id)
        processed.append(row)

    return JsonResponse(processed, safe=False)


# Simple data classes to pass company list to template
class SimpleObj:
    def __init__(self, id, name):
        self.id   = id
        self.name = name


COMPANIES = [
    SimpleObj(1, 'Sysmac Computers'),
    SimpleObj(2, 'Sysmac Info'),
    SimpleObj(3, 'IMCB LLP'),
]


# ══════════════════════════════════════════════════════════════════════════════
#  TEMPLATE VIEWS
# ══════════════════════════════════════════════════════════════════════════════

@login_required
def collection_list(request):
    collections = Collection.objects.select_related('created_by').order_by('-created_at')
    return render(request, 'collection_list.html', {'collections': collections})


@login_required
def collection_add(request):
    if request.method == 'POST':
        form = CollectionForm(request.POST, request.FILES)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.created_by = request.user
            
            # Upload file to Cloudflare R2 if provided
            if request.FILES.get('payment_proof'):
                file_obj = request.FILES['payment_proof']
                result = upload_to_cloudflare(file_obj, folder_name='collection_proofs')
                if result['success']:
                    obj.cloudflare_r2_url = result['r2_url']
                    obj.cloudflare_r2_key = result['file_key']
                    obj.payment_proof = None  # Don't save locally, only in R2
                    logger.info(f"File uploaded to R2: {result['file_key']}")
                else:
                    logger.warning(f"Failed to upload to R2: {result['error']}")
                    messages.warning(request, 'Failed to upload to Cloudflare R2.')
            
            obj.save()
            messages.success(request, 'Collection added successfully.')
            return redirect('collection_new:collection_list')
    else:
        form = CollectionForm()

    return render(request, 'collection_add.html', {
        'form':         form,
        'companies':    COMPANIES,
        'departments':  [],
        'current_user': request.user,
    })


@login_required
def collection_edit(request, pk):
    obj = get_object_or_404(Collection, pk=pk)

    if request.method == 'POST':
        form = CollectionForm(request.POST, request.FILES, instance=obj)
        if form.is_valid():
            # Handle Cloudflare R2 file upload/replacement
            if request.FILES.get('payment_proof'):
                # Delete old R2 file if exists
                if obj.cloudflare_r2_key:
                    delete_result = delete_from_cloudflare(obj.cloudflare_r2_key)
                    if delete_result['success']:
                        logger.info(f"Old R2 file deleted: {obj.cloudflare_r2_key}")
                    else:
                        logger.warning(f"Failed to delete old R2 file: {delete_result['message']}")
                
                # Upload new file to Cloudflare R2
                file_obj = request.FILES['payment_proof']
                result = upload_to_cloudflare(file_obj, folder_name='collection_proofs')
                if result['success']:
                    obj.cloudflare_r2_url = result['r2_url']
                    obj.cloudflare_r2_key = result['file_key']
                    obj.payment_proof = None  # Don't save locally, only in R2
                    logger.info(f"New file uploaded to R2: {result['file_key']}")
                else:
                    logger.warning(f"Failed to upload new file to R2: {result['error']}")
                    messages.warning(request, 'Failed to upload to Cloudflare R2.')
            
            form.save()
            messages.success(request, 'Collection updated successfully.')
            return redirect('collection_new:collection_list')
    else:
        form = CollectionForm(instance=obj)

    return render(request, 'collection_add.html', {
        'form':         form,
        'companies':    COMPANIES,
        'departments':  [],
        'edit_mode':    True,
        'object':       obj,
        'current_user': obj.created_by if obj.created_by else request.user,
    })


@login_required
def collection_delete(request, pk):
    obj = get_object_or_404(Collection, pk=pk)
    obj.delete()
    messages.success(request, 'Collection deleted.')
    return redirect('collection_new:collection_list')


@login_required
def collection_toggle_status(request, pk):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    obj = get_object_or_404(Collection, pk=pk)
    new_status = request.POST.get('status')
    if new_status not in ('pending', 'verified'):
        return JsonResponse({'error': 'Invalid status'}, status=400)
    obj.status = new_status
    obj.save(update_fields=['status'])
    return JsonResponse({'status': obj.status})


# ══════════════════════════════════════════════════════════════════════════════
#  REST API VIEWS (mobile app)
# ══════════════════════════════════════════════════════════════════════════════

@api_view(['GET'])
@authentication_classes([])
def api_collection_list(request):
    qs = Collection.objects.select_related('created_by').order_by('-created_at')
    status_filter = request.query_params.get('status')
    if status_filter in ('pending', 'verified'):
        qs = qs.filter(status=status_filter)
    company_filter = request.query_params.get('company')
    if company_filter:
        qs = qs.filter(company=company_filter)
    serializer = CollectionSerializer(qs, many=True, context={'request': request})
    return Response({'count': qs.count(), 'results': serializer.data})


@api_view(['POST'])
@authentication_classes([])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def api_collection_add(request):
    created_by = None
    if request.user.is_authenticated:
        created_by = request.user
    else:
        username = request.data.get('created_by', '').strip()
        if username:
            created_by = User.objects.filter(username__iexact=username).first()
            if not created_by:
                parts = username.split()
                if len(parts) >= 2:
                    created_by = User.objects.filter(
                        first_name__iexact=parts[0],
                        last_name__iexact=parts[-1]
                    ).first()

    serializer = CollectionSerializer(data=request.data, context={'request': request})
    if serializer.is_valid():
        instance = serializer.save(created_by=created_by)
        out = CollectionSerializer(instance, context={'request': request})
        return Response({'message': 'Collection added successfully.', 'data': out.data},
                        status=status.HTTP_201_CREATED)
    return Response({'message': 'Validation failed.', 'errors': serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@authentication_classes([])
def api_collection_detail(request, pk):
    obj = get_object_or_404(Collection, pk=pk)
    serializer = CollectionSerializer(obj, context={'request': request})
    return Response(serializer.data)


@api_view(['POST'])
@authentication_classes([])
def api_collection_toggle_status(request, pk):
    obj = get_object_or_404(Collection, pk=pk)
    new_status = request.data.get('status')
    if new_status not in ('pending', 'verified'):
        return Response({'error': 'status must be "pending" or "verified".'},
                        status=status.HTTP_400_BAD_REQUEST)
    obj.status = new_status
    obj.save(update_fields=['status'])
    return Response({'id': obj.pk, 'status': obj.status})