import json
from datetime import datetime

from django.db import models as db_models
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .models import Asset, Assignment

# ── app1 custom User model ────────────────────────────────────────────────────
from app1.models import User
# ─────────────────────────────────────────────────────────────────────────────


# ══════════════════════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def parse_date(value):
    """
    Safely parse an ISO date string (YYYY-MM-DD) into a date object.
    Returns None for blank / invalid / None values instead of raising.
    """
    if not value or not str(value).strip():
        return None
    try:
        return datetime.strptime(str(value).strip(), '%Y-%m-%d').date()
    except (ValueError, TypeError):
        return None


def parse_decimal(value, default=0):
    """Safely parse a numeric value, returning default on failure."""
    try:
        return float(value) if value not in (None, '', 'null') else default
    except (ValueError, TypeError):
        return default


def _get_users_context():
    """
    Returns active app1 Users for the Employee and Returned-By dropdowns.
    app1 User fields: .id  .name  .branch (FK → Branch)
    """
    return (
        User.objects
        .filter(status='active')
        .select_related('branch')
        .order_by('name')
    )


# ══════════════════════════════════════════════════════════════════════════════
#  ASSET MASTER & ASSET MANAGEMENT — Pages
# ══════════════════════════════════════════════════════════════════════════════

def asset_management(request):
    """Asset Management menu → renders asset_list.html."""
    context = {
        'users':            _get_users_context(),
        'available_assets': Asset.objects.filter(status='available'),
    }
    return render(request, 'asset_list.html', context)


def assets_master(request):
    """Asset Master menu → renders assets_master.html."""
    return render(request, 'assets_master.html')


# ══════════════════════════════════════════════════════════════════════════════
#  ASSET — JSON API
# ══════════════════════════════════════════════════════════════════════════════

@require_http_methods(["GET"])
def asset_list(request):
    """
    Return all assets as JSON.
    Optional query params:
      ?search=<term>   – filter by name / asset_id / serial_number
      ?status=<value>  – filter by status (available | assigned | returned)
    """
    qs = Asset.objects.all()

    search = request.GET.get('search', '').strip()
    if search:
        qs = qs.filter(
            db_models.Q(name__icontains=search)
            | db_models.Q(asset_id__icontains=search)
            | db_models.Q(serial_number__icontains=search)
        )

    status = request.GET.get('status', '').strip()
    if status:
        qs = qs.filter(status=status)

    return JsonResponse({'assets': [a.to_dict() for a in qs]})


@csrf_exempt
@require_http_methods(["POST"])
def asset_add(request):
    """
    Create a new asset.
    Expects a JSON body matching the frontend payload.
    Returns { success, asset } or { success, error }.
    """
    try:
        data = json.loads(request.body)

        asset_id = str(data.get('id', '')).strip()
        name     = str(data.get('name', '')).strip()
        category = str(data.get('category', '')).strip()

        if not asset_id or not name or not category:
            return JsonResponse(
                {'success': False, 'error': 'Asset ID, Name and Category are required.'},
                status=400,
            )

        if Asset.objects.filter(asset_id=asset_id).exists():
            return JsonResponse(
                {'success': False, 'error': 'Asset ID already exists. Use a unique ID.'},
                status=400,
            )

        specs = data.get('specs', {}) or {}
        asset = Asset.objects.create(
            asset_id        = asset_id,
            name            = name,
            category        = category,
            brand           = str(data.get('brand', '') or '').strip(),
            model_number    = str(data.get('model', '') or '').strip(),
            serial_number   = str(data.get('serial', '') or '').strip(),
            purchase_date   = parse_date(data.get('purchaseDate')),
            purchase_value  = parse_decimal(data.get('value')),
            warranty_expiry = parse_date(data.get('warranty')),
            spec_cpu        = str(specs.get('cpu', '') or '').strip(),
            spec_ram        = str(specs.get('ram', '') or '').strip(),
            spec_storage    = str(specs.get('storage', '') or '').strip(),
            spec_display    = str(specs.get('display', '') or '').strip(),
            spec_os         = str(specs.get('os', '') or '').strip(),
            spec_color      = str(specs.get('color', '') or '').strip(),
            notes           = str(data.get('notes', '') or '').strip(),
            status          = 'available',
        )
        return JsonResponse({'success': True, 'asset': asset.to_dict()}, status=201)

    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON body.'}, status=400)
    except Exception as exc:
        return JsonResponse({'success': False, 'error': str(exc)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def asset_edit(request, asset_id):
    """
    Update an existing asset identified by asset_id (e.g. AST-2025-001).
    Status is preserved from the existing record; all other fields are updated.
    """
    asset = get_object_or_404(Asset, asset_id=asset_id)
    try:
        data = json.loads(request.body)

        name     = str(data.get('name', '')).strip()
        category = str(data.get('category', '')).strip()

        if not name or not category:
            return JsonResponse(
                {'success': False, 'error': 'Name and Category are required.'},
                status=400,
            )

        new_id = str(data.get('id', asset_id)).strip() or asset_id
        if new_id != asset_id and Asset.objects.filter(asset_id=new_id).exists():
            return JsonResponse(
                {'success': False, 'error': 'Another asset already has that ID.'},
                status=400,
            )

        specs = data.get('specs', {}) or {}
        asset.asset_id        = new_id
        asset.name            = name
        asset.category        = category
        asset.brand           = str(data.get('brand', '') or '').strip()
        asset.model_number    = str(data.get('model', '') or '').strip()
        asset.serial_number   = str(data.get('serial', '') or '').strip()
        asset.purchase_date   = parse_date(data.get('purchaseDate'))
        asset.purchase_value  = parse_decimal(data.get('value'))
        asset.warranty_expiry = parse_date(data.get('warranty'))
        asset.spec_cpu        = str(specs.get('cpu', '') or '').strip()
        asset.spec_ram        = str(specs.get('ram', '') or '').strip()
        asset.spec_storage    = str(specs.get('storage', '') or '').strip()
        asset.spec_display    = str(specs.get('display', '') or '').strip()
        asset.spec_os         = str(specs.get('os', '') or '').strip()
        asset.spec_color      = str(specs.get('color', '') or '').strip()
        asset.notes           = str(data.get('notes', '') or '').strip()
        # status intentionally NOT overwritten – preserve existing lifecycle state
        asset.save()

        return JsonResponse({'success': True, 'asset': asset.to_dict()})

    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON body.'}, status=400)
    except Exception as exc:
        return JsonResponse({'success': False, 'error': str(exc)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def asset_delete(request, asset_id):
    """Permanently delete an asset by its asset_id code."""
    asset = get_object_or_404(Asset, asset_id=asset_id)
    asset_name = asset.name
    asset.delete()
    return JsonResponse({'success': True, 'message': f'"{asset_name}" deleted.'})


@require_http_methods(["GET"])
def asset_detail(request, asset_id):
    """Return a single asset as JSON (used by the view-detail modal)."""
    asset = get_object_or_404(Asset, asset_id=asset_id)
    return JsonResponse({'asset': asset.to_dict()})


# ══════════════════════════════════════════════════════════════════════════════
#  ASSIGNMENT — Pages
# ══════════════════════════════════════════════════════════════════════════════

def assignment_add_page(request):
    """
    Render asset_add.html.
    Passes `users` and `available_assets` to the template.
    Includes both 'available' and 'returned' assets so that
    returned assets can be re-assigned.
    """
    context = {
        'users':            _get_users_context(),
        'available_assets': Asset.objects.filter(
            status__in=['available', 'returned']
        ).order_by('name'),
    }
    return render(request, 'asset_add.html', context)


def assignment_list_page(request):
    context = {
        'users': _get_users_context(),
    }
    return render(request, 'asset_list.html', context)


def assignment_detail_page(request, assignment_id):
    """Render asset_details.html — full read-only view of an assignment."""
    assignment = get_object_or_404(Assignment, pk=assignment_id)
    return render(request, 'asset_details.html', {'assignment': assignment})


def assignment_edit_page(request, assignment_id):
    """Render asset_edit.html for editing an existing assignment."""
    assignment = get_object_or_404(Assignment, pk=assignment_id)
    available_assets = Asset.objects.filter(
        db_models.Q(status='available') | db_models.Q(pk=assignment.asset.pk)
    ).order_by('name')
    context = {
        'assignment':       assignment,
        'users':            _get_users_context(),
        'available_assets': available_assets,
    }
    return render(request, 'asset_edit.html', context)


def assignment_return_page(request, assignment_id):
    """
    Render asset_return.html for recording an asset return.
    Passes the assignment, all users, and the assigned asset
    (plus any available ones) so spec tags can be rendered.
    """
    assignment = get_object_or_404(Assignment, pk=assignment_id)
    # Include the currently-assigned asset so ASSET_DATA is populated
    available_assets = Asset.objects.filter(
        db_models.Q(status='available') | db_models.Q(pk=assignment.asset.pk)
    ).order_by('name')
    context = {
        'assignment':       assignment,
        'users':            _get_users_context(),
        'available_assets': available_assets,
    }
    return render(request, 'asset_return.html', context)


# ══════════════════════════════════════════════════════════════════════════════
#  ASSIGNMENT — JSON API
# ══════════════════════════════════════════════════════════════════════════════

@require_http_methods(["GET"])
def assignment_list(request):
    """
    Return all assignments as JSON.
    Optional query params:
      ?search=<term>  – filter by employee name, asset name or asset_id
    """
    qs = Assignment.objects.select_related('asset').all()

    search = request.GET.get('search', '').strip()
    if search:
        qs = qs.filter(
            db_models.Q(employee_name__icontains=search)
            | db_models.Q(asset__name__icontains=search)
            | db_models.Q(asset__asset_id__icontains=search)
        )

    return JsonResponse({'assignments': [a.to_dict() for a in qs]})


@csrf_exempt
def assignment_add(request):
    """
    Create a new assignment.
    Accepts multipart/form-data (because the frontend sends a file via FormData).
    Fields come from request.POST; the asset image from request.FILES['image'].
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required'}, status=405)

    try:
        # ── Read fields from FormData (request.POST) ──────────────────
        emp_pk       = request.POST.get('employee_id', '').strip()
        asset_id     = request.POST.get('asset_id', '').strip()
        spec_details = request.POST.get('spec_details', '').strip()
        notes        = request.POST.get('notes', '').strip()
        image_file   = request.FILES.get('image')   # optional image upload

        # ── Resolve employee ──────────────────────────────────────────
        if not emp_pk:
            return JsonResponse({'success': False, 'error': 'Employee is required.'}, status=400)
        try:
            emp_user = User.objects.select_related('branch').get(pk=emp_pk)
        except User.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Employee not found.'}, status=404)

        # ── Resolve asset ─────────────────────────────────────────────
        if not asset_id:
            return JsonResponse({'success': False, 'error': 'Asset is required.'}, status=400)
        try:
            asset = Asset.objects.get(asset_id=asset_id, status__in=['available', 'returned'])
        except Asset.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Asset not available.'}, status=400)

        # ── Save image onto the Asset record if provided ──────────────
        if image_file:
            asset.image = image_file
            asset.save(update_fields=['image'])

        # ── Create Assignment ─────────────────────────────────────────
        assignment = Assignment.objects.create(
            asset            = asset,
            employee_id      = str(emp_user.id),
            employee_name    = emp_user.name or '',
            department       = str(emp_user.branch) if emp_user.branch else '',
            spec_details     = spec_details,
            notes            = notes,
        )

        # ── Mark asset as assigned ────────────────────────────────────
        asset.status = 'assigned'
        asset.save(update_fields=['status'])

        return JsonResponse({'success': True, 'id': assignment.pk}, status=201)

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def assignment_edit(request, assignment_id):
    """
    Update an existing assignment.
    Accepts multipart/form-data so the frontend can attach a return_document file.
    Falls back to JSON if Content-Type is application/json (e.g. non-file edits).
    """
    assignment = get_object_or_404(Assignment, pk=assignment_id)

    try:
        content_type = request.content_type or ''

        # ── Detect multipart vs JSON ──────────────────────────────────
        if 'multipart/form-data' in content_type:
            data            = request.POST
            return_doc_file = request.FILES.get('return_document')
            asset_image     = request.FILES.get('asset_image')
        else:
            data            = json.loads(request.body)
            return_doc_file = None
            asset_image     = None

        # ── Update employee if provided ───────────────────────────────
        employee_id = str(data.get('employee_id', '') or '').strip()
        if employee_id:
            try:
                user = User.objects.select_related('branch').get(pk=employee_id)
                assignment.employee_id   = employee_id
                assignment.employee_name = user.name or ''
                assignment.department    = str(user.branch) if user.branch else ''
            except User.DoesNotExist:
                return JsonResponse(
                    {'success': False, 'error': 'Employee not found.'},
                    status=404,
                )

        # ── Update returned_by ────────────────────────────────────────
        returned_by_id = str(data.get('returned_by_id') or '').strip()
        if returned_by_id:
            try:
                rb = User.objects.get(pk=returned_by_id)
                assignment.returned_by_id   = returned_by_id
                assignment.returned_by_name = rb.name or ''
            except User.DoesNotExist:
                assignment.returned_by_id   = ''
                assignment.returned_by_name = ''
        else:
            assignment.returned_by_id   = ''
            assignment.returned_by_name = ''

        # ── Update scalar fields ──────────────────────────────────────
        if 'spec_details' in data:
            assignment.spec_details = str(data['spec_details'] or '').strip()
        if 'return_date' in data:
            assignment.return_date = parse_date(data['return_date'])
        if 'notes' in data:
            assignment.notes = str(data['notes'] or '').strip()

        # ── Save return document if uploaded ──────────────────────────
        if return_doc_file:
            assignment.return_document = return_doc_file

        # ── Save new asset image if uploaded during edit ──────────────
        if asset_image:
            asset = assignment.asset
            asset.image = asset_image
            asset.save(update_fields=['image'])

        # ── If a return_date is now set, mark asset as returned ───────
        if assignment.return_date:
            asset = assignment.asset
            asset.status = 'returned'
            asset.save(update_fields=['status'])

        assignment.save()
        return JsonResponse({'success': True, 'assignment': assignment.to_dict()})

    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON body.'}, status=400)
    except Exception as exc:
        return JsonResponse({'success': False, 'error': str(exc)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def assignment_delete(request, assignment_id):
    """
    Permanently delete an assignment.
    Side-effect: resets Asset.status back to 'available'
    if no other assignments remain for that asset.
    """
    assignment = get_object_or_404(Assignment, pk=assignment_id)
    asset = assignment.asset
    assignment.delete()

    # Revert asset status if no remaining assignments exist
    if not Assignment.objects.filter(asset=asset).exists():
        asset.status = 'available'
        asset.save(update_fields=['status'])

    return JsonResponse({'success': True, 'message': 'Assignment deleted.'})


@require_http_methods(["GET"])
def assignment_detail(request, assignment_id):
    """Return a single assignment as JSON."""
    assignment = get_object_or_404(Assignment, pk=assignment_id)
    return JsonResponse({'assignment': assignment.to_dict()})