"""
Assets app views.
Changes vs original:
  - assets_master() passes 'departments' queryset to template
  - asset_add() and asset_edit() read 'department_id' from JSON payload
    and set asset.department accordingly
  - asset_list() includes departmentId / departmentName via to_dict()
    (no view change needed; model.to_dict(request) already emits these fields)
  - assignment_edit() now saves multiple return images to AssignmentReturnImage
    (field name: 'return_images'; first image also stored in return_document
     for backward-compatibility)
"""

import json

from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.utils.dateparse import parse_date
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .models import Asset, Assignment, AssignmentImage, AssignmentReturnImage

# Import Department from the purchase_order app.
from purchase_order.models import Department


# ─────────────────────────────────────────────────────────────────────────────
#  Page views
# ─────────────────────────────────────────────────────────────────────────────

def assets_master(request):
    departments = Department.objects.filter(is_active=True).order_by('name')
    departments_json = json.dumps([
        {'id': d.pk, 'name': d.name}
        for d in departments
    ])
    return render(request, 'assets_master.html', {
        'departments': departments,
        'departments_json': departments_json,
    })


def asset_management(request):
    return render(request, 'asset_list.html')


# ─────────────────────────────────────────────────────────────────────────────
#  Asset REST-ish API
# ─────────────────────────────────────────────────────────────────────────────

def asset_list(request):
    assets = Asset.objects.select_related('department').all()
    return JsonResponse({'assets': [a.to_dict(request) for a in assets]})


def asset_add(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required'}, status=405)

    try:
        if request.content_type and 'multipart' in request.content_type:
            data = request.POST
            def get(key, default=''):
                return data.get(key, default)
            specs = {
                'cpu':     get('spec_cpu'),
                'ram':     get('spec_ram'),
                'storage': get('spec_storage'),
                'display': get('spec_display'),
                'os':      get('spec_os'),
                'color':   get('spec_color'),
            }
        else:
            data  = json.loads(request.body)
            get   = lambda key, default='': data.get(key, default)
            specs = data.get('specs', {})

        dept_id = get('department_id') or get('departmentId')
        department = None
        if dept_id:
            try:
                department = Department.objects.get(pk=int(dept_id))
            except (Department.DoesNotExist, ValueError):
                return JsonResponse(
                    {'success': False, 'error': f'Department with id {dept_id} not found'},
                    status=400,
                )

        asset = Asset(
            asset_id        = get('id'),
            name            = get('name'),
            category        = get('category'),
            department      = department,
            brand           = get('brand'),
            model_number    = get('model'),
            serial_number   = get('serial'),
            purchase_date   = parse_date(get('purchaseDate')) if get('purchaseDate') else None,
            purchase_value  = get('value') or 0,
            warranty_expiry = parse_date(get('warranty')) if get('warranty') else None,
            spec_cpu        = specs.get('cpu', ''),
            spec_ram        = specs.get('ram', ''),
            spec_storage    = specs.get('storage', ''),
            spec_display    = specs.get('display', ''),
            spec_os         = specs.get('os', ''),
            spec_color      = specs.get('color', ''),
            notes           = get('notes'),
        )

        if 'image' in request.FILES:
            asset.image = request.FILES['image']

        if not asset.asset_id or not asset.name or not asset.category:
            return JsonResponse({'success': False, 'error': 'Missing field: id, name or category'}, status=400)

        asset.save()
        return JsonResponse({'success': True, 'asset': asset.to_dict(request)})

    except KeyError as e:
        return JsonResponse({'success': False, 'error': f'Missing field: {e}'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


def asset_detail(request, asset_id):
    asset = get_object_or_404(Asset.objects.select_related('department'), asset_id=asset_id)
    return JsonResponse({'asset': asset.to_dict(request)})


def asset_edit(request, asset_id):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required'}, status=405)

    asset = get_object_or_404(Asset.objects.select_related('department'), asset_id=asset_id)

    try:
        if request.content_type and 'multipart' in request.content_type:
            data = request.POST
            def get(key, fallback=None):
                return data.get(key, fallback)
            specs = {
                'cpu':     get('spec_cpu', asset.spec_cpu),
                'ram':     get('spec_ram', asset.spec_ram),
                'storage': get('spec_storage', asset.spec_storage),
                'display': get('spec_display', asset.spec_display),
                'os':      get('spec_os', asset.spec_os),
                'color':   get('spec_color', asset.spec_color),
            }
        else:
            data  = json.loads(request.body)
            get   = lambda key, fallback=None: data.get(key, fallback)
            specs = data.get('specs', {})

        dept_id = get('department_id') or get('departmentId')
        if dept_id:
            try:
                asset.department = Department.objects.get(pk=int(dept_id))
            except (Department.DoesNotExist, ValueError):
                return JsonResponse(
                    {'success': False, 'error': f'Department with id {dept_id} not found'},
                    status=400,
                )
        else:
            asset.department = None

        asset.name           = get('name')            or asset.name
        asset.category       = get('category')        or asset.category
        asset.brand          = get('brand',           asset.brand)
        asset.model_number   = get('model',           asset.model_number)
        asset.serial_number  = get('serial',          asset.serial_number)
        asset.purchase_date  = parse_date(get('purchaseDate')) if get('purchaseDate') else None
        asset.purchase_value = get('value',           asset.purchase_value)
        asset.warranty_expiry = parse_date(get('warranty')) if get('warranty') else None
        asset.spec_cpu     = specs.get('cpu',     asset.spec_cpu)
        asset.spec_ram     = specs.get('ram',     asset.spec_ram)
        asset.spec_storage = specs.get('storage', asset.spec_storage)
        asset.spec_display = specs.get('display', asset.spec_display)
        asset.spec_os      = specs.get('os',      asset.spec_os)
        asset.spec_color   = specs.get('color',   asset.spec_color)
        asset.notes        = get('notes',         asset.notes)

        if 'image' in request.FILES:
            asset.image = request.FILES['image']

        asset.save()
        return JsonResponse({'success': True, 'asset': asset.to_dict(request)})

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


def asset_delete(request, asset_id):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required'}, status=405)

    asset = get_object_or_404(Asset, asset_id=asset_id)
    asset.delete()
    return JsonResponse({'success': True})


# ─────────────────────────────────────────────────────────────────────────────
#  Assignment page views
# ─────────────────────────────────────────────────────────────────────────────

def assignment_list_page(request):
    return render(request, 'asset_list.html')

def assignment_add_page(request):
    from app1.models import User as AppUser
    users = AppUser.objects.filter(status='active').order_by('name')
    available_assets = Asset.objects.filter(
        status__in=['available', 'returned']
    ).select_related('department').order_by('name')
    return render(request, 'asset_add.html', {
        'users':            users,
        'available_assets': available_assets,
    })

def assignment_detail_page(request, assignment_id):
    assignment = get_object_or_404(Assignment, pk=assignment_id)
    return render(request, 'asset_details.html', {'assignment': assignment})

def assignment_edit_page(request, assignment_id):
    from app1.models import User as AppUser
    assignment = get_object_or_404(Assignment, pk=assignment_id)
    users = AppUser.objects.filter(status='active').order_by('name')
    available_assets = Asset.objects.filter(
        status__in=['available', 'returned', 'assigned']
    ).select_related('department').order_by('name')
    return render(request, 'asset_edit.html', {
        'assignment':       assignment,
        'users':            users,
        'available_assets': available_assets,
    })

def assignment_return_page(request, assignment_id):
    from app1.models import User as AppUser
    assignment = get_object_or_404(Assignment, pk=assignment_id)
    users = AppUser.objects.filter(status='active').order_by('name')
    available_assets = Asset.objects.all().select_related('department').order_by('name')
    return render(request, 'asset_return.html', {
        'assignment':       assignment,
        'users':            users,
        'available_assets': available_assets,
    })


# ─────────────────────────────────────────────────────────────────────────────
#  Assignment API
# ─────────────────────────────────────────────────────────────────────────────

def assignment_list(request):
    assignments = Assignment.objects.select_related('asset').all()
    return JsonResponse({'assignments': [a.to_dict(request) for a in assignments]})


def assignment_add(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required'}, status=405)
    try:
        is_multipart = request.content_type and 'multipart' in request.content_type

        if is_multipart:
            from app1.models import User as AppUser

            employee_id = request.POST.get('employee_id', '').strip()
            asset_id    = request.POST.get('asset_id', '').strip()
            spec_raw    = request.POST.get('spec_details', '')
            notes       = request.POST.get('notes', '')

            if not asset_id:
                return JsonResponse({'success': False, 'error': 'asset_id is required'}, status=400)

            employee_name = ''
            department    = ''
            if employee_id:
                try:
                    user = AppUser.objects.get(pk=employee_id)
                    employee_name = (
                        getattr(user, 'name', '')
                        or getattr(user, 'full_name', '')
                        or getattr(user, 'get_full_name', lambda: '')()
                        or getattr(user, 'username', '')
                        or str(user)
                    )
                    dept_raw = (
                        getattr(user, 'branch', None)
                        or getattr(user, 'department', None)
                    )
                    if dept_raw is None:
                        department = ''
                    elif hasattr(dept_raw, 'name'):
                        department = dept_raw.name or ''
                    else:
                        department = str(dept_raw)
                except Exception:
                    pass

            asset = get_object_or_404(Asset, asset_id=asset_id)

            assignment = Assignment(
                asset         = asset,
                employee_id   = employee_id,
                employee_name = employee_name,
                department    = department,
                spec_details  = spec_raw,
                notes         = notes,
            )

            primary_file = request.FILES.get('image') or request.FILES.get('image_0')
            if primary_file:
                assignment.attachment = primary_file

            assignment.save()

            # Save all uploaded images to AssignmentImage
            uploaded_images = request.FILES.getlist('images')
            for f in uploaded_images:
                AssignmentImage.objects.create(assignment=assignment, image=f)
            # Backward-compat: also store first image in attachment
            if uploaded_images and not assignment.attachment:
                assignment.attachment = uploaded_images[0]
                assignment.save(update_fields=['attachment'])

        else:
            data = json.loads(request.body)
            asset = get_object_or_404(Asset, asset_id=data['assetId'])
            assignment = Assignment(
                asset         = asset,
                employee_id   = data.get('emp_id', ''),
                employee_name = data.get('emp', ''),
                department    = data.get('dept', ''),
                spec_details  = ','.join(data.get('specs', [])) if isinstance(data.get('specs'), list) else data.get('specs', ''),
                return_date   = parse_date(data['returnDate']) if data.get('returnDate') else None,
                notes         = data.get('notes', ''),
            )
            assignment.save()

        asset.status = 'assigned'
        asset.save(update_fields=['status'])
        return JsonResponse({'success': True, 'assignment': assignment.to_dict(request)})

    except Exception as e:
        import traceback
        return JsonResponse({'success': False, 'error': str(e), 'trace': traceback.format_exc()}, status=500)


def assignment_detail(request, assignment_id):
    assignment = get_object_or_404(Assignment.objects.select_related('asset'), pk=assignment_id)
    return JsonResponse({'assignment': assignment.to_dict(request)})


def assignment_edit(request, assignment_id):
    """
    POST /api/assignments/<id>/edit/
    Accepts multipart/form-data (from asset_return.html, with file uploads)
    and application/json (from asset_list.html edit modal).

    multipart field map (return flow)
    ----------------------------------
    return_date       → assignment.return_date
    returned_by_id    → assignment.returned_by_id / returned_by_name
    return_condition  → prepended to assignment.notes
    notes             → assignment.notes
    return_images     → AssignmentReturnImage rows (multiple files allowed)
                        The first file is also stored in assignment.return_document
                        for backward-compatibility with existing queries.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required'}, status=405)

    assignment = get_object_or_404(Assignment, pk=assignment_id)

    try:
        is_multipart = request.content_type and 'multipart' in request.content_type

        if is_multipart:
            # ── multipart (from asset_return.html) ───────────────────────────
            from app1.models import User as AppUser

            return_date_str  = request.POST.get('return_date', '')
            returned_by_id   = request.POST.get('returned_by_id', '')
            return_condition = request.POST.get('return_condition', '').strip()
            notes            = request.POST.get('notes', assignment.notes)

            if return_date_str:
                assignment.return_date = parse_date(return_date_str)

            if returned_by_id:
                assignment.returned_by_id = returned_by_id
                try:
                    user = AppUser.objects.get(pk=returned_by_id)
                    assignment.returned_by_name = (
                        getattr(user, 'name', '')
                        or getattr(user, 'full_name', '')
                        or getattr(user, 'get_full_name', lambda: '')()
                        or getattr(user, 'username', '')
                        or str(user)
                    )
                except Exception:
                    assignment.returned_by_name = returned_by_id

            # Merge condition note into general notes
            if return_condition:
                assignment.return_condition = return_condition
            assignment.notes = notes

            # ── Multiple return images ────────────────────────────────────────
            # Frontend sends files as return_images (multiple).
            # Also accept legacy single-file field names for backward-compat.
            return_files = (
                request.FILES.getlist('return_images')
                or [f for key in ('return_document', 'return_document_0')
                    if (f := request.FILES.get(key))]
            )

            if return_files:
                # First file → assignment.return_document (backward-compat)
                assignment.return_document = return_files[0]

                # All files → AssignmentReturnImage rows
                # Clear previous return images before adding new ones so a
                # re-submission doesn't accumulate duplicates.
                assignment.return_images.all().delete()
                for uploaded_file in return_files:
                    AssignmentReturnImage.objects.create(
                        assignment=assignment,
                        image=uploaded_file,
                    )

            # ── Multiple asset images (uploaded at edit time) ─────────────
            asset_images = request.FILES.getlist('asset_image')
            if asset_images:
                assignment.assignment_images.all().delete()
                for f in asset_images:
                    AssignmentImage.objects.create(assignment=assignment, image=f)
                assignment.attachment = asset_images[0]

            # Mark asset as returned
            assignment.asset.status = 'returned'
            assignment.asset.save(update_fields=['status'])

        else:
            # ── JSON (from asset_list.html edit modal) ────────────────────────
            data = json.loads(request.body)
            assignment.employee_id   = data.get('emp_id',       assignment.employee_id)
            assignment.employee_name = data.get('emp',          assignment.employee_name)
            assignment.department    = data.get('dept',         assignment.department)
            if 'specs' in data:
                specs = data['specs']
                assignment.spec_details = ','.join(specs) if isinstance(specs, list) else specs
            if data.get('returnDate'):
                assignment.return_date = parse_date(data['returnDate'])
            if data.get('return_date'):
                assignment.return_date = parse_date(data['return_date'])
            if data.get('returned_by_id') is not None:
                assignment.returned_by_id = data['returned_by_id'] or ''
            assignment.notes = data.get('notes', assignment.notes)

        assignment.save()
        return JsonResponse({'success': True, 'assignment': assignment.to_dict(request)})

    except Exception as e:
        import traceback
        return JsonResponse({'success': False, 'error': str(e), 'trace': traceback.format_exc()}, status=500)


def assignment_delete(request, assignment_id):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required'}, status=405)
    assignment = get_object_or_404(Assignment, pk=assignment_id)
    assignment.delete()
    return JsonResponse({'success': True})