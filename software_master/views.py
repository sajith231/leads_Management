from django.shortcuts import render

# Create your views here.
from django.shortcuts import render, redirect, get_object_or_404
from .models import Software

def software_table(request):
    softwares = Software.objects.all()
    return render(request, 'software_table.html', {'softwares': softwares})

def add_software(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        if name:
            Software.objects.create(name=name)
            return redirect('software_table')
    return render(request, 'add_software.html')

def edit_software(request, id):
    software = get_object_or_404(Software, id=id)
    if request.method == 'POST':
        software.name = request.POST.get('name')
        software.save()
        return redirect('software_table')
    return render(request, 'add_software.html', {'software': software})

def delete_software(request, id):
    software = get_object_or_404(Software, id=id)
    software.delete()
    return redirect('software_table')
