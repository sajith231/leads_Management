import os
from django.shortcuts import render
from django.shortcuts import render, redirect, get_object_or_404
from .models import Vehicle
# Create your views here.
#vehicle masters
def vehicle(request):
    """Registration page + handle creation."""
    if request.method == 'POST':
        v = Vehicle.objects.create(
            vehicle_number=request.POST['vehicle_number'].upper().strip(),
            owner_name=request.POST['owner_name'].strip(),
            rc_copy=request.FILES['rc_copy'],
            insurance_copy=request.FILES['insurance_copy'],
            pollution_copy=request.FILES['pollution_copy']
        )
        return redirect('vehicle_list')          # after save go to list
    return render(request, 'vehicle.html')

def vehicle_list(request):
    """Plain list without actions column."""
    ctx = {'vehicles': Vehicle.objects.all()}
    return render(request, 'vehicle_list.html', ctx)

def vehicle_viewer(request, pk):
    """Full-size viewer for the 3 uploaded files."""
    v = get_object_or_404(Vehicle, pk=pk)
    return render(request, 'vehicle_viewer.html', {'v': v})





#fuel managements

def fuel_management(request):
    return render(request, 'fuel_management.html') 


def fuel_enter(request):
    return render(request, 'fuel_entre.html')