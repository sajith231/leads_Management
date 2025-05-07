from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from .models import Field,Credentials

def credential_management(request):
    fields = Field.objects.all()
    credentials = Credentials.objects.all()
    return render(request, 'credential_management.html', {
        'fields': fields,
        'credentials': credentials
    })

def add_field(request):
    if request.method == 'POST':
        field_name = request.POST.get('field_name')
        if field_name:
            Field.objects.create(name=field_name)
            return redirect('credential_management')
    return redirect('credential_management')

def edit_field(request, field_id):
    field = get_object_or_404(Field, id=field_id)
    if request.method == 'POST':
        new_name = request.POST.get('field_name')
        if new_name:
            field.name = new_name  # Update field name
            field.save()
        return redirect('credential_management')  # Reload page after editing
    return render(request, 'edit_field_modal.html', {'field': field})  # Open popup for editing

def delete_field(request, field_id):
    field = get_object_or_404(Field, id=field_id)
    field.delete()  # Delete the field
    return redirect('credential_management')  # Reload page after deletion


def add_credential(request):
    if request.method == 'POST':
        credential_name = request.POST.get('credential_name')
        if credential_name:
            Credentials.objects.create(name=credential_name)
            return redirect('credential_management')
    return render(request, 'add_credential.html')

# views.py
from django.shortcuts import get_object_or_404, redirect
from .models import Credentials

def delete_credential(request, id):
    credential = get_object_or_404(Credentials, id=id)
    credential.delete()
    return redirect('credential_management')



from django.shortcuts import render, redirect, get_object_or_404
from .models import Credentials

def edit_credential(request, id):
    credential = get_object_or_404(Credentials, id=id)
    if request.method == 'POST':
        credential_name = request.POST.get('credential_name')
        if credential_name:
            credential.name = credential_name
            credential.save()
            return redirect('credential_management')
    return render(request, 'edit_credential.html', {'credential': credential})







# Add these imports at the top
from django.views.decorators.http import require_POST
from .models import CredentialDetail

# Add these new views
@require_POST
def add_credential_detail(request, credential_id):
    credential = get_object_or_404(Credentials, id=credential_id)
    field_id = request.POST.get('field_id')
    value = request.POST.get('value')
    
    if field_id and value:
        field = get_object_or_404(Field, id=field_id)
        CredentialDetail.objects.create(
            credential=credential,
            field=field,
            value=value
        )
    return redirect('credential_detail', id=credential_id)

def credential_detail(request, id):
    credential = get_object_or_404(Credentials, id=id)
    details = credential.details.all().select_related('field')
    fields = Field.objects.all()
    return render(request, 'credential_detail.html', {
        'credential': credential,
        'details': details,
        'fields': fields
    })




from django.shortcuts import get_object_or_404
from .models import CredentialDetail

def edit_credential_detail(request, detail_id):
    detail = get_object_or_404(CredentialDetail, id=detail_id)
    if request.method == 'POST':
        field_id = request.POST.get('field_id')
        value = request.POST.get('value')
        
        if field_id and value:
            field = get_object_or_404(Field, id=field_id)
            detail.field = field
            detail.value = value
            detail.save()
            
    return redirect('credential_detail', id=detail.credential.id)

def delete_credential_detail(request, detail_id):
    detail = get_object_or_404(CredentialDetail, id=detail_id)
    credential_id = detail.credential.id
    detail.delete()
    return redirect('credential_detail', id=credential_id)