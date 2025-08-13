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