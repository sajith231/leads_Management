from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from .models import Claim
import requests
import json

def claims_list(request):
    claims = Claim.objects.all().order_by('-created_at')

    client = request.GET.get('client', '').strip()
    created_by = request.GET.get('created_by', '').strip()
    status = request.GET.get('status', '').strip()
    expense_type = request.GET.get('expense_type', '').strip()
    date_from = request.GET.get('date_from', '').strip()
    date_to = request.GET.get('date_to', '').strip()

    if client:
        claims = claims.filter(client_name__icontains=client)

    if created_by:
        claims = claims.filter(
            Q(created_by__username__icontains=created_by) |
            Q(created_by__first_name__icontains=created_by) |
            Q(created_by__last_name__icontains=created_by)
        )

    if status:
        claims = claims.filter(status=status)

    if expense_type:
        claims = claims.filter(expense_type=expense_type)

    if date_from:
        claims = claims.filter(created_at__date__gte=date_from)

    if date_to:
        claims = claims.filter(created_at__date__lte=date_to)

    paginator = Paginator(claims, 10)
    page_number = request.GET.get('page', 1)
    claims_page = paginator.get_page(page_number)

    return render(request, 'claims_list.html', {'claims': claims_page})

@login_required
def claims_add(request):
    if request.method == 'POST':
        client = request.POST.get('client')
        client_name = request.POST.get('client_name')
        expense_type = request.POST.get('expense_type')
        amount = request.POST.get('amount')
        description = request.POST.get('description', '').strip()
        receipt = request.FILES.get('receipt')

        # Default description for food if empty
        if expense_type == 'food' and not description:
            description = 'Food/Meal Expense'

        # ✅ Receipt required unless it's a "self" expense
        receipt_is_required = expense_type != 'self'

        missing = []
        if not client: missing.append('client')
        if not expense_type: missing.append('expense type')
        if not amount: missing.append('amount')
        if not description: missing.append('description')
        if receipt_is_required and not receipt: missing.append('receipt')

        if missing:
            messages.error(request, f'Please provide: {", ".join(missing)}.')
        else:
            Claim.objects.create(
                client=client,
                client_name=client_name,
                expense_type=expense_type,
                amount=amount,
                description=description,
                receipt=receipt if receipt else None,
                status='claimed',
                created_by=request.user,
                updated_by=request.user,  # initial updater = creator
            )
            messages.success(request, 'Claim added successfully!')
            return redirect('claims_list')

    return render(request, 'claims_add.html')

@login_required
def claims_edit(request, pk):
    claim = get_object_or_404(Claim, pk=pk)

    if request.method == 'POST':
        client = request.POST.get('client')
        client_name = request.POST.get('client_name')
        expense_type = request.POST.get('expense_type')
        amount = request.POST.get('amount')
        description = request.POST.get('description', '').strip()
        receipt = request.FILES.get('receipt')

        if expense_type == 'food' and not description:
            description = 'Food/Meal Expense'

        receipt_is_required = expense_type != 'self'

        missing = []
        if not client: missing.append('client')
        if not expense_type: missing.append('expense type')
        if not amount: missing.append('amount')
        if not description: missing.append('description')
        # ✅ No receipt needed for "self"
        if receipt_is_required and not (receipt or claim.receipt):
            missing.append('receipt')

        if missing:
            messages.error(request, f'Please provide: {", ".join(missing)}.')
        else:
            claim.client = client
            claim.client_name = client_name
            claim.expense_type = expense_type
            claim.amount = amount
            claim.description = description

            if receipt:
                claim.receipt = receipt  # keep existing if none uploaded

            claim.updated_by = request.user
            claim.save()
            messages.success(request, 'Claim updated successfully!')
            return redirect('claims_list')

    return render(request, 'claims_edit.html', {'claim': claim})

@csrf_exempt
def claims_delete(request, pk):
    if request.method == 'POST':
        claim = get_object_or_404(Claim, pk=pk)
        claim.delete()
        return JsonResponse({'success': True, 'message': 'Claim deleted successfully!'})
    return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=400)

@csrf_exempt
def update_claim_status(request, pk):
    if request.method == 'POST':
        try:
            claim = get_object_or_404(Claim, pk=pk)
            data = json.loads(request.body)
            new_status = data.get('status')

            if new_status in ['claimed', 'approved', 'rejected']:
                claim.status = new_status
                claim.save()
                return JsonResponse({
                    'success': True,
                    'status': claim.status,
                    'status_display': claim.get_status_display()
                })
            else:
                return JsonResponse({'success': False, 'error': 'Invalid status'}, status=400)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)

    return JsonResponse({'success': False, 'error': 'Invalid request'}, status=400)

def get_clients(request):
    try:
        response = requests.get('https://accmaster.imcbs.com/api/sync/rrc-clients/', timeout=10)
        response.raise_for_status()
        clients_data = response.json()
        return JsonResponse({'success': True, 'data': clients_data})
    except requests.exceptions.RequestException as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
