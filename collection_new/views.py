from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse
import urllib.request
import urllib.parse
import json

from rest_framework.decorators import api_view, parser_classes, authentication_classes
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response
from rest_framework import status

from .models import Collection
from .forms import CollectionForm
from .serializers import CollectionSerializer


# ── Acc-Master client IDs per company ────────────────────────────────────────
ACC_API_URL      = 'https://accmaster.imcbs.com/api/sync/acc-master/'
ACC_DEPT_API_URL = 'https://accmaster.imcbs.com/api/sync/acc-departments/'

COMPANY_CLIENT_IDS = {
    'Sysmac Computers': 'GW9Q6NQQ5ONRU',
    'Sysmac Info':      '69ZHSXOIMFA6T',
    'IMCB LLP':         'G9SYCSM54HR3Ev',
}

# In-process cache — key '__all__' for dept map, company name for clients
_DEPT_CACHE   = {}
_CLIENT_CACHE = {}


def fetch_departments(force=False):
    if not force and '__all__' in _DEPT_CACHE and _DEPT_CACHE['__all__']:
        return _DEPT_CACHE['__all__']

    try:
        with urllib.request.urlopen(ACC_DEPT_API_URL, timeout=10) as resp:
            data = json.loads(resp.read().decode())

        items = data if isinstance(data, list) else data.get('results', data.get('data', []))

        if items:
            _DEPT_CACHE['__all__'] = items
        return items
    except Exception as e:
        print(f"Error fetching departments: {e}")
        return _DEPT_CACHE.get('__all__', [])


def fetch_raw_clients(company, force=False):
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
    company = request.GET.get('company', '').strip()
    if not company:
        return JsonResponse({'error': 'company param required'}, status=400)

    if company not in COMPANY_CLIENT_IDS:
        return JsonResponse({'error': 'Unknown company'}, status=400)

    company_client_id = COMPANY_CLIENT_IDS[company]
    all_depts = fetch_departments()

    result = sorted(
        [
            {'id': d['department_id'], 'name': d['department']}
            for d in all_depts
            if str(d.get('client_id', '')).strip() == company_client_id
               and d.get('department_id') and d.get('department')
        ],
        key=lambda x: x['name']
    )
    return JsonResponse(result, safe=False)


@login_required
def acc_master_proxy(request):
    company = request.GET.get('company', '').strip()
    if not company:
        return JsonResponse({'error': 'company param required'}, status=400)

    all_depts = fetch_departments()
    dept_map  = {
        str(d.get('department_id', '')).strip(): str(d.get('department', '')).strip()
        for d in all_depts
        if d.get('department_id') and d.get('department')
    }

    clients = fetch_raw_clients(company)

    processed = []
    for c in clients:
        row     = dict(c)
        dept_id = str(row.get('openingdepartment', '')).strip()
        row['openingdepartment'] = dept_map.get(dept_id, dept_id)
        processed.append(row)

    return JsonResponse(processed, safe=False)


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