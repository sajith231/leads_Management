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
    if request.method == 'POST':
        challan = get_object_or_404(Challan, id=challan_id)
        status = request.POST.get('status')
        payment_date = request.POST.get('payment_date')
        if status in ['paid', 'pending', 'disputed']:
            challan.status = status
            if status == 'paid' and payment_date:
                challan.payment_date = payment_date
            challan.save()
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': True})
            messages.success(request, f"Challan status updated to {status}.")
        else:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': 'Invalid status'}, status=400)
            messages.error(request, "Invalid status.")
        return redirect('vehicle_challan_activity', vehicle_id=challan.vehicle.id)
    return redirect('vehicle_details')


@require_http_methods(["POST"])
def challan_delete(request, challan_id):
    try:
        challan = get_object_or_404(Challan, id=challan_id)
        vehicle_id = challan.vehicle.id
        challan_number = challan.challan_number
        challan.delete()
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': True})
        messages.success(request, f"Challan {challan_number} deleted successfully.")
    except Exception as e:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
        messages.error(request, f"Error deleting challan: {str(e)}")
        return redirect('vehicle_details')
    return redirect('vehicle_challan_activity', vehicle_id=vehicle_id)








# vehicle_challan/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Max, Count, Q
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.http import require_http_methods
from django.urls import reverse
from datetime import date, datetime
import logging
from urllib.parse import quote_plus, unquote_plus

from fuel_management.models import Vehicle
from .models import VehicleDetail, Challan

logger = logging.getLogger(__name__)


def _ensure_temp_checks_session(request):
    """Ensure session key exists and is a list."""
    temp_checks = request.session.get('temp_checks')
    if not isinstance(temp_checks, list):
        request.session['temp_checks'] = []
        temp_checks = request.session['temp_checks']
    return temp_checks


def add_check(request):
    """
    Add a temporary (non-persisted) check stored in session.
    Each POST will append a new temporary check so the same vehicle can appear multiple times.
    """
    try:
        vehicles = Vehicle.objects.all().order_by('vehicle_number')
    except Exception as e:
        logger.exception("Error loading vehicles for add_check: %s", e)
        vehicles = []
        messages.error(request, "Error loading vehicles list.")

    if request.method == 'POST':
        vehicle_id = request.POST.get('vehicle_id', '').strip()
        remarks = request.POST.get('remarks', '').strip()
        detail_date = request.POST.get('detail_date') or date.today().isoformat()

        if not vehicle_id:
            messages.error(request, "Please select a vehicle before submitting.")
            return render(request, 'add_check.html', {
                'vehicles': vehicles,
                'form_data': request.POST,
                'current_date': date.today().strftime('%Y-%m-%d'),
            })

        # validate vehicle exists
        try:
            vehicle = Vehicle.objects.get(id=int(vehicle_id))
        except (ValueError, Vehicle.DoesNotExist):
            messages.error(request, "Selected vehicle is invalid.")
            return render(request, 'add_check.html', {
                'vehicles': vehicles,
                'form_data': request.POST,
                'current_date': date.today().strftime('%Y-%m-%d'),
            })

        # Build the temp-check dictionary
        temp_check = {
            'vehicle_id': vehicle.id,
            'vehicle_number': vehicle.vehicle_number,
            'vehicle_name': getattr(vehicle, 'vehicle_name', None),
            'date': detail_date,       # store as ISO string; we'll parse later
            'remarks': remarks or '',
            'created_at': datetime.now().isoformat()
        }

        # Save into session list (append)
        temp_checks = _ensure_temp_checks_session(request)
        temp_checks.append(temp_check)
        request.session.modified = True  # mark session changed

        messages.success(request, f"Temporary check added for {vehicle.vehicle_number} ({detail_date}).")
        # Redirect to the report list (no query params needed; report reads session)
        try:
            return redirect('report_list')
        except Exception:
            return redirect('/vehicle/report/')

    # GET: show the add_check form
    return render(request, 'add_check.html', {
        'vehicles': vehicles,
        'current_date': date.today().strftime('%Y-%m-%d'),
    })


def vehicle_info_json(request, vehicle_id):
    try:
        vehicle = get_object_or_404(Vehicle, id=vehicle_id)
        last_check = VehicleDetail.objects.filter(vehicle=vehicle).aggregate(last=Max('detail_date'))['last']
        pending = Challan.objects.filter(vehicle=vehicle, status='pending').count()
        paid = Challan.objects.filter(vehicle=vehicle, status='paid').count()
        total = Challan.objects.filter(vehicle=vehicle).count()
        last_check_str = last_check.isoformat() if last_check else None
        data = {
            'last_check_date': last_check_str,
            'pending_challans': pending,
            'paid_challans': paid,
            'total_challans': total,
        }
        return JsonResponse({'success': True, 'data': data})
    except Exception as e:
        logger.exception("Error in vehicle_info_json for id %s: %s", vehicle_id, e)
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


def vehicle_challans_json(request, vehicle_id):
    if request.method != 'GET':
        return HttpResponseBadRequest("Only GET allowed")
    try:
        vehicle = get_object_or_404(Vehicle, id=vehicle_id)
        challans = Challan.objects.filter(vehicle=vehicle).order_by('-challan_date')
        data = []
        for c in challans:
            data.append({
                'id': c.id,
                'challan_number': getattr(c, 'challan_number', f'#{c.id}'),
                'challan_date': c.challan_date.isoformat() if getattr(c, 'challan_date', None) else None,
                'offense_type': getattr(c, 'offense_type', '') or '',
                'fine_amount': str(getattr(c, 'fine_amount', '') or ''),
                'status': getattr(c, 'status', '') or '',
                'payment_date': c.payment_date.isoformat() if getattr(c, 'payment_date', None) else None,
                'remarks': getattr(c, 'remarks', '') or '',
            })
        return JsonResponse({'success': True, 'data': data})
    except Exception as exc:
        logger.exception("vehicle_challans_json error for vehicle %s: %s", vehicle_id, exc)
        return JsonResponse({'success': False, 'error': str(exc)}, status=500)


def report_list(request):
    """
    Build rows for the report list with filtering support:
     - Filter by vehicle
     - Filter by date range (from/to)
     - include one row per saved VehicleDetail
     - include session temporary checks as separate rows
    """
    try:
        # Get filter parameters from GET request
        selected_vehicle = request.GET.get('vehicle', '')
        date_from = request.GET.get('date_from', '')
        date_to = request.GET.get('date_to', '')
        
        # Parse dates if provided
        date_from_obj = None
        date_to_obj = None
        if date_from:
            try:
                date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
            except ValueError:
                messages.warning(request, "Invalid 'from' date format.")
        
        if date_to:
            try:
                date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
            except ValueError:
                messages.warning(request, "Invalid 'to' date format.")
        
        # Get all vehicles for the dropdown
        all_vehicles = Vehicle.objects.all().order_by('vehicle_number')
        
        # Build base queryset for VehicleDetail
        details_qs = VehicleDetail.objects.select_related('vehicle')
        
        # Apply vehicle filter
        if selected_vehicle:
            try:
                vehicle_id = int(selected_vehicle)
                details_qs = details_qs.filter(vehicle_id=vehicle_id)
            except ValueError:
                pass
        
        # Apply date range filter
        if date_from_obj:
            details_qs = details_qs.filter(detail_date__gte=date_from_obj)
        if date_to_obj:
            details_qs = details_qs.filter(detail_date__lte=date_to_obj)
        
        details_qs = details_qs.order_by('-detail_date', 'vehicle__vehicle_number')
        
        # Precompute challan counts per vehicle
        challan_qs = Challan.objects.all()
        if selected_vehicle:
            try:
                vehicle_id = int(selected_vehicle)
                challan_qs = challan_qs.filter(vehicle_id=vehicle_id)
            except ValueError:
                pass
        
        counts = challan_qs.values('vehicle').annotate(
            pending_ch=Count('id', filter=Q(status='pending')),
            paid_ch=Count('id', filter=Q(status='paid')),
            total_ch=Count('id')
        )
        counts_map = {c['vehicle']: c for c in counts}
        
        # Cache latest challan info per vehicle
        last_challan_cache = {}
        
        vehicles_rows = []
        
        class RowObj:
            pass
        
        # Add persisted rows (one per saved check)
        for d in details_qs:
            v = d.vehicle
            vid = v.id
            c = counts_map.get(vid, {})
            pending = c.get('pending_ch', 0)
            paid = c.get('paid_ch', 0)
            total = c.get('total_ch', 0)
            
            if vid not in last_challan_cache:
                latest = Challan.objects.filter(vehicle=v).order_by('-challan_date').first()
                if latest:
                    last_challan_cache[vid] = {
                        'last_challan_date': latest.challan_date,
                        'last_challan_status': latest.status,
                        'last_challan_payment_date': latest.payment_date
                    }
                else:
                    last_challan_cache[vid] = {
                        'last_challan_date': None,
                        'last_challan_status': None,
                        'last_challan_payment_date': None
                    }
            
            last_info = last_challan_cache[vid]
            
            row = RowObj()
            row.id = vid
            row.vehicle_number = v.vehicle_number
            row.vehicle_name = getattr(v, 'vehicle_name', None)
            row.last_check = d.detail_date
            row.pending_challans = pending
            row.paid_challans = paid
            row.total_challans = total
            row.last_challan_date = last_info['last_challan_date']
            row.last_challan_status = last_info['last_challan_status']
            row.last_challan_payment_date = last_info['last_challan_payment_date']
            row.remarks = d.remarks
            row.is_persisted = True
            vehicles_rows.append(row)
        
        # If no vehicle filter is applied, add vehicles with NO details
        if not selected_vehicle:
            detailed_vehicle_ids = set(d.vehicle_id for d in details_qs)
            remaining_vehicles = Vehicle.objects.exclude(id__in=detailed_vehicle_ids).order_by('vehicle_number')
            
            for v in remaining_vehicles:
                vid = v.id
                c = counts_map.get(vid, {})
                pending = c.get('pending_ch', 0)
                paid = c.get('paid_ch', 0)
                total = c.get('total_ch', 0)
                
                if vid not in last_challan_cache:
                    latest = Challan.objects.filter(vehicle=v).order_by('-challan_date').first()
                    if latest:
                        last_challan_cache[vid] = {
                            'last_challan_date': latest.challan_date,
                            'last_challan_status': latest.status,
                            'last_challan_payment_date': latest.payment_date
                        }
                    else:
                        last_challan_cache[vid] = {
                            'last_challan_date': None,
                            'last_challan_status': None,
                            'last_challan_payment_date': None
                        }
                
                last_info = last_challan_cache[vid]
                
                row = RowObj()
                row.id = vid
                row.vehicle_number = v.vehicle_number
                row.vehicle_name = getattr(v, 'vehicle_name', None)
                row.last_check = None
                row.pending_challans = pending
                row.paid_challans = paid
                row.total_challans = total
                row.last_challan_date = last_info['last_challan_date']
                row.last_challan_status = last_info['last_challan_status']
                row.last_challan_payment_date = last_info['last_challan_payment_date']
                row.remarks = None
                row.is_persisted = True
                vehicles_rows.append(row)
        
        # Process session temporary checks
        temp_checks = request.session.get('temp_checks') or []
        for tmp in reversed(temp_checks):
            try:
                temp_vid = int(tmp.get('vehicle_id') or 0)
            except Exception:
                temp_vid = 0
            
            # Apply vehicle filter to temp checks
            if selected_vehicle:
                try:
                    if temp_vid != int(selected_vehicle):
                        continue
                except ValueError:
                    continue
            
            temp_vehicle_number = tmp.get('vehicle_number') or f"Vehicle #{temp_vid}"
            temp_vehicle_name = tmp.get('vehicle_name')
            temp_date_raw = tmp.get('date')
            temp_remarks = tmp.get('remarks', '')
            
            # Parse date
            temp_last_check = None
            if temp_date_raw:
                try:
                    temp_last_check = date.fromisoformat(temp_date_raw)
                except Exception:
                    try:
                        temp_last_check = datetime.fromisoformat(temp_date_raw).date()
                    except Exception:
                        temp_last_check = None
            
            # Apply date range filter to temp checks
            if date_from_obj and temp_last_check and temp_last_check < date_from_obj:
                continue
            if date_to_obj and temp_last_check and temp_last_check > date_to_obj:
                continue
            
            c = counts_map.get(temp_vid, {})
            last_info = last_challan_cache.get(temp_vid, {
                'last_challan_date': None,
                'last_challan_status': None,
                'last_challan_payment_date': None
            })
            
            row = RowObj()
            row.id = temp_vid
            row.vehicle_number = temp_vehicle_number
            row.vehicle_name = temp_vehicle_name
            row.last_check = temp_last_check
            row.pending_challans = c.get('pending_ch', 0)
            row.paid_challans = c.get('paid_ch', 0)
            row.total_challans = c.get('total_ch', 0)
            row.last_challan_date = last_info['last_challan_date']
            row.last_challan_status = last_info['last_challan_status']
            row.last_challan_payment_date = last_info['last_challan_payment_date']
            row.remarks = temp_remarks
            row.is_persisted = False
            vehicles_rows.insert(0, row)
        
        # Get selected vehicle name for display
        selected_vehicle_name = None
        if selected_vehicle:
            try:
                selected_veh = Vehicle.objects.filter(id=int(selected_vehicle)).first()
                if selected_veh:
                    selected_vehicle_name = f"{selected_veh.vehicle_number}"
                    if selected_veh.vehicle_name:
                        selected_vehicle_name += f" - {selected_veh.vehicle_name}"
            except ValueError:
                pass
        
        return render(request, 'report_list.html', {
            'vehicles': vehicles_rows,
            'all_vehicles': all_vehicles,
            'selected_vehicle': selected_vehicle,
            'selected_vehicle_name': selected_vehicle_name,
            'date_from': date_from,
            'date_to': date_to,
        })
    
    except Exception as e:
        logger.exception("Error loading report list: %s", e)
        messages.error(request, f"Error loading report: {str(e)}")
        return render(request, 'report_list.html', {
            'vehicles': [],
            'all_vehicles': Vehicle.objects.all().order_by('vehicle_number'),
            'selected_vehicle': '',
            'date_from': '',
            'date_to': '',
        })