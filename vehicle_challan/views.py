from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Count, Q
from django.views.decorators.http import require_http_methods
from fuel_management.models import Vehicle, FuelEntry
from app1.models import User
from .models import VehicleDetail, Challan
from datetime import date
import logging

logger = logging.getLogger(__name__)

def vehicle_details(request):
    try:
        details = VehicleDetail.objects.select_related('vehicle').all().order_by('-detail_date')
        return render(request, 'vehicle_details.html', {'details': details})
    except Exception as e:
        logger.error(f"Error loading vehicle details: {str(e)}")
        messages.error(request, f"Error loading vehicle details: {str(e)}")
        return render(request, 'vehicle_details.html', {'details': []})

def details_add(request):
    current_date = date.today().strftime('%Y-%m-%d')
    
    try:
        vehicles = Vehicle.objects.all().order_by('vehicle_number')
        logger.info(f"Available vehicles: {[(v.id, v.vehicle_number) for v in vehicles]}")
    except Exception as e:
        logger.error(f"Error loading vehicles: {str(e)}")
        vehicles = []
        messages.error(request, "Error loading vehicles list.")

    if request.method == 'POST':
        vehicle_id = request.POST.get('vehicle_id', '').strip()
        detail_date = request.POST.get('detail_date', '').strip()
        remarks = request.POST.get('remarks', '').strip()

        logger.info(f"POST data - vehicle_id: {vehicle_id}, detail_date: {detail_date}")

        form_data = {
            'vehicle_id': vehicle_id,
            'detail_date': detail_date,
            'remarks': remarks,
        }

        if not vehicle_id:
            messages.error(request, "Please select a vehicle.")
            return render(request, 'details_add.html', {
                'vehicles': vehicles,
                'form_data': form_data,
                'current_date': current_date
            })

        if not detail_date:
            messages.error(request, "Detail date is required.")
            return render(request, 'details_add.html', {
                'vehicles': vehicles,
                'form_data': form_data,
                'current_date': current_date
            })

        try:
            vehicle = Vehicle.objects.get(id=int(vehicle_id))
        except ValueError:
            messages.error(request, "Invalid vehicle ID format.")
            return render(request, 'details_add.html', {
                'vehicles': vehicles,
                'form_data': form_data,
                'current_date': current_date
            })
        except Vehicle.DoesNotExist:
            messages.error(request, f"Vehicle with ID {vehicle_id} does not exist.")
            return render(request, 'details_add.html', {
                'vehicles': vehicles,
                'form_data': form_data,
                'current_date': current_date
            })

        try:
            vehicle_detail = VehicleDetail(
                vehicle=vehicle,
                detail_date=detail_date,
                description='',  # Empty string or you can remove this field from model
                remarks=remarks if remarks else None
            )
            vehicle_detail.save()
            
            messages.success(request, f"Vehicle detail added successfully for {vehicle.vehicle_number}.")
            return redirect('vehicle_details')
        except Exception as e:
            logger.exception(f"Error saving vehicle detail: {str(e)}")
            messages.error(request, f"Error saving detail: {str(e)}")
            return render(request, 'details_add.html', {
                'vehicles': vehicles,
                'form_data': form_data,
                'current_date': current_date
            })

    return render(request, 'details_add.html', {
        'vehicles': vehicles,
        'current_date': current_date
    })


@require_http_methods(["POST"])
def details_delete(request, detail_id):
    """Delete a vehicle detail entry"""
    try:
        detail = get_object_or_404(VehicleDetail, id=detail_id)
        vehicle_number = detail.vehicle.vehicle_number
        detail_date = detail.detail_date
        
        # Delete the detail
        detail.delete()
        
        messages.success(request, f"Vehicle detail for {vehicle_number} (Date: {detail_date.strftime('%d %b %Y')}) deleted successfully.")
        logger.info(f"Deleted vehicle detail ID {detail_id} for vehicle {vehicle_number}")
    except VehicleDetail.DoesNotExist:
        messages.error(request, "Vehicle detail not found.")
        logger.error(f"Attempted to delete non-existent vehicle detail ID {detail_id}")
    except Exception as e:
        logger.error(f"Error deleting vehicle detail {detail_id}: {str(e)}")
        messages.error(request, f"Error deleting vehicle detail: {str(e)}")
    
    return redirect('vehicle_details')


def get_user_display_name(user):
    """Helper function to get user display name"""
    if not user:
        return "Unknown User"
    
    # Try different possible name fields
    if hasattr(user, 'name') and user.name:
        return user.name
    elif hasattr(user, 'username') and user.username:
        return user.username
    elif hasattr(user, 'first_name') and user.first_name:
        full_name = f"{user.first_name} {user.last_name}".strip() if hasattr(user, 'last_name') else user.first_name
        return full_name
    elif hasattr(user, 'email') and user.email:
        return user.email
    else:
        return f"User #{user.id}"


def vehicle_challan_activity(request, vehicle_id):
    """Display challan and fuel entry activities for a specific vehicle"""
    vehicle = get_object_or_404(Vehicle, id=vehicle_id)
    
    # Get fuel entries with user information
    fuel_entries = FuelEntry.objects.filter(
        vehicle=vehicle
    ).select_related('travelled_by').order_by('-date', '-start_time')
    
    # Process fuel entries to add display names
    processed_entries = []
    for entry in fuel_entries:
        entry.user_display_name = get_user_display_name(entry.travelled_by)
        entry.user_phone = getattr(entry.travelled_by, 'phone_number', None) if entry.travelled_by else None
        processed_entries.append(entry)
    
    # Get all challans for this vehicle
    challans = Challan.objects.filter(
        vehicle=vehicle
    ).select_related('fuel_entry__travelled_by').order_by('-challan_date')
    
    # Process challans to add display names
    processed_challans = []
    for challan in challans:
        if challan.fuel_entry and challan.fuel_entry.travelled_by:
            challan.user_display_name = get_user_display_name(challan.fuel_entry.travelled_by)
        else:
            challan.user_display_name = None
        processed_challans.append(challan)
    
    # Calculate statistics
    total_users = fuel_entries.values('travelled_by').distinct().count()
    total_entries = fuel_entries.count()
    pending_challans = challans.filter(status='pending').count()
    paid_challans = challans.filter(status='paid').count()
    total_fine_amount = sum(c.fine_amount for c in challans if c.status == 'pending')
    
    context = {
        'vehicle': vehicle,
        'fuel_entries': processed_entries,
        'challans': processed_challans,
        'stats': {
            'total_users': total_users,
            'total_fuel_entries': total_entries,
            'pending_challans': pending_challans,
            'paid_challans': paid_challans,
            'total_challans': challans.count(),
            'total_fine_amount': total_fine_amount,
        }
    }
    
    return render(request, 'challan.html', context)


def challan_add(request, vehicle_id):
    """Add new challan for a vehicle"""
    vehicle = get_object_or_404(Vehicle, id=vehicle_id)
    
    # Get fuel entries with user information
    fuel_entries = FuelEntry.objects.filter(
        vehicle=vehicle
    ).select_related('travelled_by').order_by('-date', '-start_time')
    
    # Process fuel entries to add display names and proper date field
    processed_entries = []
    for entry in fuel_entries:
        # Add user display name
        entry.user_display_name = get_user_display_name(entry.travelled_by)
        
        # Add entry_date attribute (mapping from 'date' field)
        entry.entry_date = entry.date
        
        # Ensure fuel_type is available
        if not hasattr(entry, 'fuel_type') or not entry.fuel_type:
            entry.fuel_type = 'N/A'
        
        # Ensure quantity is available
        if not hasattr(entry, 'quantity'):
            entry.quantity = 0
            
        # Ensure purpose field exists
        if not hasattr(entry, 'purpose'):
            entry.purpose = None
            
        processed_entries.append(entry)
    
    if request.method == 'POST':
        challan_number = request.POST.get('challan_number', '').strip()
        challan_date = request.POST.get('challan_date')
        offense_type = request.POST.get('offense_type', '').strip()
        offense_location = request.POST.get('offense_location', '').strip()
        fine_amount = request.POST.get('fine_amount', '').strip()
        fuel_entry_id = request.POST.get('fuel_entry_id')
        remarks = request.POST.get('remarks', '').strip()
        
        if not all([challan_number, challan_date, offense_type, fine_amount]):
            messages.error(request, "Required fields: Challan Number, Date, Offense Type, and Fine Amount.")
            return render(request, 'challan_add.html', {
                'vehicle': vehicle,
                'fuel_entries': processed_entries,
                'current_date': date.today().strftime('%Y-%m-%d'),
                'form_data': {
                    'challan_number': challan_number,
                    'challan_date': challan_date,
                    'offense_type': offense_type,
                    'offense_location': offense_location,
                    'fine_amount': fine_amount,
                    'fuel_entry_id': fuel_entry_id,
                    'remarks': remarks
                }
            })
        
        try:
            fuel_entry = None
            if fuel_entry_id:  
                fuel_entry = FuelEntry.objects.get(id=fuel_entry_id)
            
            challan = Challan(
                vehicle=vehicle,
                fuel_entry=fuel_entry,
                challan_number=challan_number,
                challan_date=challan_date,
                offense_type=offense_type,
                offense_location=offense_location if offense_location else None,
                fine_amount=fine_amount,
                remarks=remarks if remarks else None,
                status='pending'
            )
            challan.save()
            
            user_info = ""
            if fuel_entry and fuel_entry.travelled_by:
                user_name = get_user_display_name(fuel_entry.travelled_by)
                user_info = f" (Associated with user: {user_name})"
            
            messages.success(request, f"Challan {challan_number} added successfully{user_info}.")
            return redirect('vehicle_challan_activity', vehicle_id=vehicle_id)
        except FuelEntry.DoesNotExist:
            logger.error(f"Fuel entry with ID {fuel_entry_id} does not exist")
            messages.error(request, "Selected fuel entry does not exist.")
            return render(request, 'challan_add.html', {
                'vehicle': vehicle,
                'fuel_entries': processed_entries,
                'current_date': date.today().strftime('%Y-%m-%d')
            })
        except Exception as e:
            logger.error(f"Error adding challan: {str(e)}")
            messages.error(request, f"Error adding challan: {str(e)}")
            return render(request, 'challan_add.html', {
                'vehicle': vehicle,
                'fuel_entries': processed_entries,
                'current_date': date.today().strftime('%Y-%m-%d')
            })
    
    return render(request, 'challan_add.html', {
        'vehicle': vehicle,
        'fuel_entries': processed_entries,
        'current_date': date.today().strftime('%Y-%m-%d')
    })

def challan_update_status(request, challan_id):
    """Update challan payment status"""
    if request.method == 'POST':
        challan = get_object_or_404(Challan, id=challan_id)
        status = request.POST.get('status')
        payment_date = request.POST.get('payment_date')
        
        if status in ['paid', 'pending', 'disputed']:
            challan.status = status
            if status == 'paid' and payment_date:
                challan.payment_date = payment_date
            challan.save()
            messages.success(request, f"Challan status updated to {status}.")
        else:
            messages.error(request, "Invalid status.")
        
        return redirect('vehicle_challan_activity', vehicle_id=challan.vehicle.id)
    
    return redirect('vehicle_details')