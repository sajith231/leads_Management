import os
from django.shortcuts import render, redirect, get_object_or_404
from django.db import IntegrityError
from django.contrib import messages
from .models import Vehicle, FuelEntry

def vehicle(request):
    """Registration page + handle creation."""
    if request.method == 'POST':
        vehicle_number = request.POST['vehicle_number'].upper().strip()
        owner_name = request.POST['owner_name'].strip()
        avg_mileage = request.POST['avg_mileage']
        rc_copy = request.FILES.get('rc_copy')
        insurance_copy = request.FILES.get('insurance_copy')
        pollution_copy = request.FILES.get('pollution_copy')

        try:
            Vehicle.objects.create(
                vehicle_number=vehicle_number,
                owner_name=owner_name,
                avg_mileage=avg_mileage,
                rc_copy=rc_copy,
                insurance_copy=insurance_copy,
                pollution_copy=pollution_copy
            )
            messages.success(request, "Vehicle added successfully.")
            return redirect('vehicle_list')

        except IntegrityError:
            messages.error(request, f"Vehicle number '{vehicle_number}' already exists.")
            return redirect('vehicle')

    return render(request, 'vehicle.html')

def vehicle_list(request):
    """List all vehicles with edit/delete actions."""
    ctx = {'vehicles': Vehicle.objects.all()}
    return render(request, 'vehicle_list.html', ctx)

def vehicle_edit(request, vehicle_id):
    """Edit existing vehicle."""
    vehicle = get_object_or_404(Vehicle, id=vehicle_id)

    if request.method == 'POST':
        try:
            vehicle.vehicle_number = request.POST['vehicle_number'].upper().strip()
            vehicle.owner_name = request.POST['owner_name'].strip()
            vehicle.avg_mileage = request.POST['avg_mileage']
            
            # Handle file updates - only update if new file is provided
            if 'rc_copy' in request.FILES:
                vehicle.rc_copy = request.FILES['rc_copy']
            if 'insurance_copy' in request.FILES:
                vehicle.insurance_copy = request.FILES['insurance_copy']
            if 'pollution_copy' in request.FILES:
                vehicle.pollution_copy = request.FILES['pollution_copy']
            
            vehicle.save()
            messages.success(request, "Vehicle updated successfully.")
            return redirect('vehicle_list')

        except IntegrityError:
            messages.error(request, f"Vehicle number '{request.POST['vehicle_number']}' already exists.")
        except Exception as e:
            messages.error(request, f"Error updating vehicle: {str(e)}")

    return render(request, 'vehicle_edit.html', {'vehicle': vehicle})

def vehicle_delete(request, vehicle_id):
    """Delete vehicle."""
    if request.method == 'POST':
        try:
            vehicle = get_object_or_404(Vehicle, id=vehicle_id)
            vehicle_number = vehicle.vehicle_number
            vehicle.delete()
            messages.success(request, f"Vehicle '{vehicle_number}' deleted successfully.")
        except Exception as e:
            messages.error(request, f"Error deleting vehicle: {str(e)}")
    
    return redirect('vehicle_list')






# Fuel managements
def fuel_management(request):
    """Display list of all fuel entries."""
    fuel_entries = FuelEntry.objects.all().order_by('-date', '-id')  # Recent first
    ctx = {'fuel_entries': fuel_entries}
    return render(request, 'fuel_management.html', ctx)

def fuel_enter(request):
    """Handle fuel entry form submission."""
    if request.method == 'POST':
        try:
            FuelEntry.objects.create(
                vehicle_type=request.POST['vehicle_type'],
                staff_name=request.POST['staff_name'],
                date=request.POST['date'],
                odo_start=request.POST['odo_start'],
                odo_end=request.POST['odo_end'],
                trip_from=request.POST['trip_from'].strip(),
                trip_to=request.POST['trip_to'].strip(),
                fuel_cost=request.POST['fuel_cost']
            )
            messages.success(request, "Fuel entry added successfully.")
            return redirect('fuel_management')
        
        except Exception as e:
            messages.error(request, f"Error adding fuel entry: {str(e)}")
            return redirect('fuel_enter')
    
    return render(request, 'fuel_entre.html')

def fuel_edit(request, entry_id):
    """Edit existing fuel entry."""
    fuel_entry = get_object_or_404(FuelEntry, id=entry_id)

    if request.method == 'POST':
        try:
            fuel_entry.vehicle_type = request.POST['vehicle_type']
            fuel_entry.staff_name   = request.POST['staff_name']
            fuel_entry.date         = request.POST['date']
            fuel_entry.odo_start    = request.POST['odo_start']
            fuel_entry.odo_end      = request.POST['odo_end']
            fuel_entry.trip_from    = request.POST['trip_from'].strip()
            fuel_entry.trip_to      = request.POST['trip_to'].strip()
            fuel_entry.fuel_cost    = request.POST['fuel_cost']
            fuel_entry.save()

            messages.success(request, "Fuel entry updated successfully.")
            return redirect('fuel_management')

        except Exception as e:
            messages.error(request, f"Error updating fuel entry: {str(e)}")

    # -------------  automatic dropdown data  -------------
    staff_list = ["Rajesh Kumar", "Suresh Menon", "Anil Varghese",
                  "Mohammed Ali", "Vinod Thomas"]
    return render(request, 'fuel_edit.html', {'record': fuel_entry, 'staff_list': staff_list})

def fuel_delete(request, entry_id):
    """Delete fuel entry."""
    if request.method == 'POST':
        try:
            fuel_entry = get_object_or_404(FuelEntry, id=entry_id)
            fuel_entry.delete()
            messages.success(request, "Fuel entry deleted successfully.")
        except Exception as e:
            messages.error(request, f"Error deleting fuel entry: {str(e)}")
    
    return redirect('fuel_management')

def fuel_monitoring(request):
    """
    Monitoring dashboard showing staff-wise fuel analytics:
    - Average mileage
    - Total expenses
    - Fuel consumption per km
    - Trip history
    """
    
    # Get all unique staff names
    staff_names = FuelEntry.objects.values_list('staff_name', flat=True).distinct()
    
    staff_analytics = []
    
    # Assumed average fuel prices (you can adjust these or make them dynamic)
    FUEL_PRICE_TWO_WHEELER = 100  # ₹ per liter (petrol)
    FUEL_PRICE_FOUR_WHEELER = 100  # ₹ per liter (diesel/petrol)
    
    for staff_name in staff_names:
        # Get all entries for this staff member
        staff_entries = FuelEntry.objects.filter(staff_name=staff_name)
        
        # Calculate totals
        total_trips = staff_entries.count()
        total_distance = sum(entry.distance_traveled() for entry in staff_entries)
        total_cost = sum(float(entry.fuel_cost) for entry in staff_entries)
        
        # Calculate fuel consumption based on vehicle type
        # Estimate fuel used for each trip
        trips_with_details = []
        total_fuel_used = 0
        
        for entry in staff_entries:
            distance = entry.distance_traveled()
            
            # Estimate fuel price based on vehicle type
            if entry.vehicle_type == 'two wheeler':
                fuel_price = FUEL_PRICE_TWO_WHEELER
            else:
                fuel_price = FUEL_PRICE_FOUR_WHEELER
            
            # Calculate fuel used (liters) = fuel_cost / price_per_liter
            fuel_used = float(entry.fuel_cost) / fuel_price if fuel_price > 0 else 0
            total_fuel_used += fuel_used
            
            # Calculate mileage for this trip
            mileage = float(distance) / fuel_used if fuel_used > 0 else 0
            
            trips_with_details.append({
                'date': entry.date,
                'vehicle_type': entry.vehicle_type,
                'get_vehicle_type_display': entry.get_vehicle_type_display(),
                'trip_from': entry.trip_from,
                'trip_to': entry.trip_to,
                'distance_traveled': distance,
                'fuel_cost': entry.fuel_cost,
                'fuel_used': fuel_used,
                'mileage': mileage
            })
        
        # Calculate average mileage (km per liter)
        avg_mileage = float(total_distance) / total_fuel_used if total_fuel_used > 0 else 0
        
        # Calculate cost per km
        cost_per_km = float(total_cost) / float(total_distance) if total_distance > 0 else 0
        
        staff_analytics.append({
            'staff_name': staff_name,
            'total_trips': total_trips,
            'total_distance': total_distance,
            'total_cost': total_cost,
            'avg_mileage': avg_mileage,
            'cost_per_km': cost_per_km,
            'estimated_fuel': total_fuel_used,
            'trips': trips_with_details
        })
    
    # Sort by total trips (descending)
    staff_analytics.sort(key=lambda x: x['total_trips'], reverse=True)
    
    ctx = {'staff_analytics': staff_analytics}
    return render(request, 'monitoring.html', ctx)