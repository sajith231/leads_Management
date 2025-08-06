from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from app4.models import Printer, License

def license_type_view(request):
    licenses = License.objects.all()
    licenses = License.objects.all().order_by('-id')  # Or '-created_at' if that field exists
  # Fetch all licenses from database
    return render(request, 'license_type.html', {'licenses': licenses})

def add_license_view(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        branch = request.POST.get('branch')
        file = request.FILES.get('license_file')

        if name and branch and file and file.name.endswith('.txt'):
            content = file.read().decode('utf-8')
            License.objects.create(
                name=name,
                branch=branch,
                license_key=content
            )
            return redirect('license_type')

    return render(request, 'add_license.html')

def license_download(request, license_id):
    license_obj = get_object_or_404(License, id=license_id)
    
    # Create HTTP response with the license content
    response = HttpResponse(license_obj.license_key, content_type='text/plain')
    response['Content-Disposition'] = f'attachment; filename="{license_obj.name}.txt"'
    
    return response

def license_view(request, license_id):
    license_obj = get_object_or_404(License, id=license_id)
    return render(request, 'license_view.html', {'license': license_obj})

def license_edit(request, license_id):
    license_obj = get_object_or_404(License, id=license_id)
    
    if request.method == 'POST':
        name = request.POST.get('name')
        branch = request.POST.get('branch')
        file = request.FILES.get('license_file')
        
        # Update name and branch (required fields)
        if name:
            license_obj.name = name
        if branch:
            license_obj.branch = branch
            
        # Update license content only if new file is uploaded
        if file and file.name.endswith('.txt'):
            content = file.read().decode('utf-8')
            license_obj.license_key = content
            
        license_obj.save()
        return redirect('license_type')
    
    return render(request, 'license_edit.html', {'license': license_obj})

def license_delete(request, license_id):
    license_obj = get_object_or_404(License, id=license_id)
    if request.method == 'POST':
        license_obj.delete()
    return redirect('license_type')