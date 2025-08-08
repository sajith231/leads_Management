from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from app4.models import Printer, License
from app1.models import Branch


def license_type_view(request):
    licenses = License.objects.all().order_by('-id')
    branches = Branch.objects.all()  # ✅ get all branches
    return render(request, 'license_type.html', {
        'licenses': licenses,
        'branches': branches  # ✅ pass to template
    })


def add_license_view(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        branch_id = request.POST.get('branch')  # this will be a string ID
        file = request.FILES.get('license_file')

        if name and branch_id and file and file.name.endswith('.txt'):
            content = file.read().decode('utf-8')
            License.objects.create(
                name=name,
                branch_id=branch_id,  # ✅ use `_id` to assign ForeignKey directly
                license_key=content
            )
            return redirect('license_type')

    branches = Branch.objects.all()
    return render(request, 'add_license.html', {'branches': branches})

def license_download(request, license_id):
    license_obj = get_object_or_404(License, id=license_id)
    
    # Create HTTP response with the license content
    response = HttpResponse(license_obj.license_key, content_type='text/plain')
    response['Content-Disposition'] = f'attachment; filename="{license_obj.name}.txt"'
    
    return response

def license_view(request, license_id):
    license_obj = get_object_or_404(License, id=license_id)
    return render(request, 'license_view.html', {'license': license_obj})

from django.shortcuts import render, redirect, get_object_or_404
from app1.models import Branch
from .models import License

def license_edit(request, license_id):
    license_obj = get_object_or_404(License, id=license_id)

    if request.method == 'POST':
        name = request.POST.get('name')
        branch_id = request.POST.get('branch')
        file = request.FILES.get('license_file')

        if name:
            license_obj.name = name

        if branch_id:
            license_obj.branch_id = branch_id  # ✅ use branch_id to set the FK directly

        if file and file.name.endswith('.txt'):
            content = file.read().decode('utf-8')
            license_obj.license_key = content

        license_obj.save()
        return redirect('license_type')

    branches = Branch.objects.all()  # ✅ pass branches to populate dropdown
    return render(request, 'license_edit.html', {
        'license': license_obj,
        'branches': branches
    })

def license_delete(request, license_id):
    license_obj = get_object_or_404(License, id=license_id)
    if request.method == 'POST':
        license_obj.delete()
    return redirect('license_type')






# AMAL SHAJI