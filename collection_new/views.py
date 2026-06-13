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
ACC_API_URL = 'https://accmaster.imcbs.com/api/sync/acc-master/'

COMPANY_CLIENT_IDS = {
    'Sysmac Computers': 'GW9Q6NQQ5ONRU',
    'Sysmac Info':      '69ZHSXOIMFA6T',
    'IMCB LLP':         'G9SYCSM54HR3E',
}


@login_required
def acc_master_proxy(request):
    """
    Server-side proxy to avoid CORS when the browser calls the Acc-Master API.
    Usage: /collection/acc-proxy/?company=Sysmac+Computers
    """
    company = request.GET.get('company', '')
    client_id = COMPANY_CLIENT_IDS.get(company)

    if not client_id:
        return JsonResponse({'error': 'Unknown company'}, status=400)

    url = f'{ACC_API_URL}?client_id={urllib.parse.quote(client_id)}'
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        return JsonResponse(data, safe=False)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=502)


# Simple data classes to pass company/department to template
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
#  TEMPLATE VIEWS (existing — unchanged)
# ══════════════════════════════════════════════════════════════════════════════

@login_required
def collection_list(request):
    collections = Collection.objects.select_related(
        'created_by'
    ).order_by('-created_at')
    return render(request, 'collection_list.html', {
        'collections': collections,
    })


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
    """AJAX endpoint: toggle status between pending ↔ verified."""
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
#  REST API VIEWS (for mobile app)
# ══════════════════════════════════════════════════════════════════════════════

@api_view(['GET'])
@authentication_classes([])
def api_collection_list(request):
    """
    GET /collections/api/list/
    Returns all collections ordered by newest first.

    Optional query filters:
      ?status=pending|verified
      ?company=Sysmac+Computers
    """
    qs = Collection.objects.select_related('created_by').order_by('-created_at')

    status_filter = request.query_params.get('status')
    if status_filter in ('pending', 'verified'):
        qs = qs.filter(status=status_filter)

    company_filter = request.query_params.get('company')
    if company_filter:
        qs = qs.filter(company=company_filter)

    serializer = CollectionSerializer(qs, many=True, context={'request': request})
    return Response({
        'count':   qs.count(),
        'results': serializer.data,
    })


@api_view(['POST'])
@authentication_classes([])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def api_collection_add(request):
    """
    POST /collections/api/add/
    Accepts multipart/form-data (required when uploading payment_proof).

    Required fields:
      company          — "Sysmac Computers" | "Sysmac Info" | "IMCB LLP"
      department       — department name (string)
      client_name      — client name (string)
      collection_type  — cash | cheque | bank_transfer | upi | other
      amount           — decimal number
      paid_for         — string (e.g. "Invoice #1023")

    Conditional fields:
      payment_proof    — file (required when collection_type is cheque/upi/bank_transfer)

    Optional fields:
      notes            — text
      created_by       — username string — mobile app passes logged-in user's username
    """
    # ── Resolve created_by ────────────────────────────────────────────────────
    # Priority 1: session/token authenticated user (web browser)
    # Priority 2: username string passed in the form-data body (mobile app)
    created_by = None
    if request.user.is_authenticated:
        created_by = request.user
    else:
        username = request.data.get('created_by', '').strip()
        if username:
            # Case-insensitive username match (handles "veena" == "Veena")
            created_by = User.objects.filter(username__iexact=username).first()
            if not created_by:
                # Fallback: try matching by full name e.g. "Veena K"
                parts = username.split()
                if len(parts) >= 2:
                    created_by = User.objects.filter(
                        first_name__iexact=parts[0],
                        last_name__iexact=parts[-1]
                    ).first()

    serializer = CollectionSerializer(data=request.data, context={'request': request})
    if serializer.is_valid():
        instance = serializer.save(created_by=created_by)
        # Re-serialize the saved instance so payment_proof_url and
        # created_by_name reflect the fully saved state
        out = CollectionSerializer(instance, context={'request': request})
        return Response({
            'message': 'Collection added successfully.',
            'data':    out.data,
        }, status=status.HTTP_201_CREATED)

    return Response({
        'message': 'Validation failed.',
        'errors':  serializer.errors,
    }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@authentication_classes([])
def api_collection_detail(request, pk):
    """
    GET /collections/api/<pk>/
    Returns a single collection record.
    """
    obj = get_object_or_404(Collection, pk=pk)
    serializer = CollectionSerializer(obj, context={'request': request})
    return Response(serializer.data)


@api_view(['POST'])
@authentication_classes([])
def api_collection_toggle_status(request, pk):
    """
    POST /collections/api/<pk>/toggle-status/
    Body: { "status": "pending" | "verified" }
    """
    obj = get_object_or_404(Collection, pk=pk)
    new_status = request.data.get('status')

    if new_status not in ('pending', 'verified'):
        return Response(
            {'error': 'status must be "pending" or "verified".'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    obj.status = new_status
    obj.save(update_fields=['status'])
    return Response({'id': obj.pk, 'status': obj.status})