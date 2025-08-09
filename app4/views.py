import base64
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.urls import reverse
from app1.models import Branch
from .models import License
from django.views.decorators.http import require_http_methods

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
            # you can add messages or error display in template
            return render(request, 'add_license.html', {
                'branches': Branch.objects.all(),
                'error': 'Please provide name, branch and a .txt file.'
            })

        # Optional: restrict extension to .txt
        # But if you want to accept other types, remove this check.
        if not uploaded_file.name.lower().endswith('.txt'):
            return render(request, 'add_license.html', {
                'branches': Branch.objects.all(),
                'error': 'Only .txt files are allowed.'
            })

        # Read original bytes and store base64 encoded string
        file_bytes = uploaded_file.read()  # bytes
        b64 = base64.b64encode(file_bytes).decode('ascii')

        License.objects.create(
            name=name,
            branch_id=branch_id,
            license_key=b64,
            file_name=uploaded_file.name
        )
        return redirect('license_type')

    branches = Branch.objects.all()
    return render(request, 'add_license.html', {'branches': branches})


def _get_bytes_from_stored(license_obj):
    """
    Helper: try to base64-decode stored string. If it fails,
    assume stored string is plain text and return its utf-8 bytes.
    This makes the view tolerant to older entries already stored as text.
    """
    stored = license_obj.license_key or ''
    try:
        return base64.b64decode(stored)
    except Exception:
        # fallback: treat as plain text string saved earlier
        return stored.encode('utf-8', errors='replace')


def license_download(request, license_id):
    license_obj = get_object_or_404(License, id=license_id)
    file_bytes = _get_bytes_from_stored(license_obj)

    # Set Content-Type as octet-stream to force download
    response = HttpResponse(file_bytes, content_type='application/octet-stream')
    # use original filename if present; else fallback to name + .txt
    filename = license_obj.file_name or f"{license_obj.name}.txt"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    response['Content-Length'] = str(len(file_bytes))
    return response


def license_preview(request, license_id):
    """
    Return decoded textual preview (JSON). Non-decodable bytes will be replaced.
    This endpoint is used by the frontend to fetch the license content on demand.
    """
    license_obj = get_object_or_404(License, id=license_id)
    file_bytes = _get_bytes_from_stored(license_obj)

    # Try decode as utf-8; replace errors so JSON is safe
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

    branches = Branch.objects.all()
    return render(request, 'license_edit.html', {
        'license': license_obj,
        'branches': branches
    })


@require_http_methods(["POST"])
def license_delete(request, license_id):
    license_obj = get_object_or_404(License, id=license_id)
    license_obj.delete()
    return redirect('license_type')



import base64
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from .models import License

def license_preview(request, license_id):
    license_obj = get_object_or_404(License, id=license_id)
    try:
        # Decode Base64 back to bytes
        file_bytes = base64.b64decode(license_obj.license_key)
        # Try converting to UTF-8 text, replacing bad chars
        text_content = file_bytes.decode('utf-8', errors='replace')
    except Exception:
        text_content = "[Unable to preview this file]"
    
    return JsonResponse({
        'name': license_obj.name,
        'branch': license_obj.branch.name,
        'created_at': license_obj.created_at.strftime('%d-%m-%Y'),
        'content': text_content
    })
