import os
from decimal import Decimal
from datetime import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.db import IntegrityError
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Vehicle, FuelEntry
from app1.models import User

from django.core.paginator import Paginator
from django.db.models import Q
from django.contrib.auth import get_user_model
from django.db.models import Q, F
from django.db.models.functions import Coalesce
from django.core.paginator import Paginator

User = get_user_model()


def vehicle(request):
    """Registration page + handle creation."""
    if request.method == 'POST':
        vehicle_number = request.POST['vehicle_number'].upper().strip()
        vehicle_name = request.POST['vehicle_name'].strip()
        model_number = request.POST['model_number'].strip()
        manufacture_year = request.POST['manufacture_year']
        owner_name = request.POST['owner_name'].strip()
        fuel_type = request.POST.get('fuel_type', 'petrol')
        fuel_rate = request.POST.get('fuel_rate', '0.00')
        avg_mileage = request.POST['avg_mileage']
        rc_copy = request.FILES.get('rc_copy')
        insurance_copy = request.FILES.get('insurance_copy')
        pollution_copy = request.FILES.get('pollution_copy')

        try:
            if not vehicle_number:
                messages.error(request, "Vehicle number is required.")
                return render(request, 'vehicle.html', {
                    'vehicle_number': vehicle_number,
                    'vehicle_name': vehicle_name,
                    'model_number': model_number,
                    'manufacture_year': manufacture_year,
                    'owner_name': owner_name,
                    'fuel_type': fuel_type,
                    'fuel_rate': fuel_rate,
                    'avg_mileage': avg_mileage
                })
            
            if not vehicle_name:
                messages.error(request, "Vehicle name is required.")
                return render(request, 'vehicle.html', {
                    'vehicle_number': vehicle_number,
                    'vehicle_name': vehicle_name,
                    'model_number': model_number,
                    'manufacture_year': manufacture_year,
                    'owner_name': owner_name,
                    'fuel_type': fuel_type,
                    'fuel_rate': fuel_rate,
                    'avg_mileage': avg_mileage
                })
            
            if not model_number:
                messages.error(request, "Model number is required.")
                return render(request, 'vehicle.html', {
                    'vehicle_number': vehicle_number,
                    'vehicle_name': vehicle_name,
                    'model_number': model_number,
                    'manufacture_year': manufacture_year,
                    'owner_name': owner_name,
                    'fuel_type': fuel_type,
                    'fuel_rate': fuel_rate,
                    'avg_mileage': avg_mileage
                })
            
            if not manufacture_year:
                messages.error(request, "Manufacture year is required.")
                return render(request, 'vehicle.html', {
                    'vehicle_number': vehicle_number,
                    'vehicle_name': vehicle_name,
                    'model_number': model_number,
                    'manufacture_year': manufacture_year,
                    'owner_name': owner_name,
                    'fuel_type': fuel_type,
                    'fuel_rate': fuel_rate,
                    'avg_mileage': avg_mileage
                })
            
            if not owner_name:
                messages.error(request, "Owner name is required.")
                return render(request, 'vehicle.html', {
                    'vehicle_number': vehicle_number,
                    'vehicle_name': vehicle_name,
                    'model_number': model_number,
                    'manufacture_year': manufacture_year,
                    'owner_name': owner_name,
                    'fuel_type': fuel_type,
                    'fuel_rate': fuel_rate,
                    'avg_mileage': avg_mileage
                })

            try:
                manufacture_year_int = int(manufacture_year)
                current_year = datetime.now().year
                if manufacture_year_int < 1900 or manufacture_year_int > current_year:
                    messages.error(request, f"Manufacture year must be between 1900 and {current_year}.")
                    return render(request, 'vehicle.html', {
                        'vehicle_number': vehicle_number,
                        'vehicle_name': vehicle_name,
                        'model_number': model_number,
                        'manufacture_year': manufacture_year,
                        'owner_name': owner_name,
                        'fuel_type': fuel_type,
                        'fuel_rate': fuel_rate,
                        'avg_mileage': avg_mileage
                    })
            except ValueError:
                messages.error(request, "Invalid manufacture year.")
                return render(request, 'vehicle.html', {
                    'vehicle_number': vehicle_number,
                    'vehicle_name': vehicle_name,
                    'model_number': model_number,
                    'manufacture_year': manufacture_year,
                    'owner_name': owner_name,
                    'fuel_type': fuel_type,
                    'fuel_rate': fuel_rate,
                    'avg_mileage': avg_mileage
                })

            Vehicle.objects.create(
                vehicle_number=vehicle_number,
                vehicle_name=vehicle_name,
                model_number=model_number,
                manufacture_year=manufacture_year_int,
                owner_name=owner_name,
                fuel_type=fuel_type,
                fuel_rate=fuel_rate,
                avg_mileage=avg_mileage,
                rc_copy=rc_copy,
                insurance_copy=insurance_copy,
                pollution_copy=pollution_copy
            )
            messages.success(request, "Vehicle added successfully.")
            return redirect('vehicle_list')

        except IntegrityError:
            messages.error(request, f"Vehicle number '{vehicle_number}' already exists.")
            return render(request, 'vehicle.html', {
                'vehicle_number': vehicle_number,
                'vehicle_name': vehicle_name,
                'model_number': model_number,
                'manufacture_year': manufacture_year,
                'owner_name': owner_name,
                'fuel_type': fuel_type,
                'fuel_rate': fuel_rate,
                'avg_mileage': avg_mileage
            })
        except Exception as e:
            messages.error(request, f"Error adding vehicle: {str(e)}")
            return render(request, 'vehicle.html', {
                'vehicle_number': vehicle_number,
                'vehicle_name': vehicle_name,
                'model_number': model_number,
                'manufacture_year': manufacture_year,
                'owner_name': owner_name,
                'fuel_type': fuel_type,
                'fuel_rate': fuel_rate,
                'avg_mileage': avg_mileage
            })

    return render(request, 'vehicle.html')


def vehicle_list(request):
    """List all vehicles with edit/delete actions."""
    ctx = {'vehicles': Vehicle.objects.all()}
    return render(request, 'vehicle_list.html', ctx)


def vehicle_edit(request, vehicle_id):
    """Edit existing vehicle details."""
    vehicle = get_object_or_404(Vehicle, id=vehicle_id)

    if request.method == 'POST':
        try:
            vehicle_number = request.POST.get('vehicle_number', '').upper().strip()
            vehicle_name = request.POST.get('vehicle_name', '').strip()
            model_number = request.POST.get('model_number', '').strip()
            manufacture_year = request.POST.get('manufacture_year', '').strip()
            owner_name = request.POST.get('owner_name', '').strip()
            avg_mileage = request.POST.get('avg_mileage', '').strip()
            fuel_type = request.POST.get('fuel_type', 'petrol')

            if not vehicle_number:
                messages.error(request, "Vehicle number is required.")
                return render(request, 'vehicle_edit.html', {'vehicle': vehicle})

            if Vehicle.objects.exclude(id=vehicle.id).filter(vehicle_number=vehicle_number).exists():
                messages.error(request, f"Vehicle number '{vehicle_number}' already exists.")
                return render(request, 'vehicle_edit.html', {'vehicle': vehicle})

            if not vehicle_name:
                messages.error(request, "Vehicle name is required.")
                return render(request, 'vehicle_edit.html', {'vehicle': vehicle})

            if not model_number:
                messages.error(request, "Model number is required.")
                return render(request, 'vehicle_edit.html', {'vehicle': vehicle})

            if not manufacture_year:
                messages.error(request, "Manufacture year is required.")
                return render(request, 'vehicle_edit.html', {'vehicle': vehicle})

            if not owner_name:
                messages.error(request, "Owner name is required.")
                return render(request, 'vehicle_edit.html', {'vehicle': vehicle})

            if not avg_mileage:
                messages.error(request, "Average mileage is required.")
                return render(request, 'vehicle_edit.html', {'vehicle': vehicle})

            try:
                manufacture_year_int = int(manufacture_year)
                current_year = datetime.now().year
                if manufacture_year_int < 1900 or manufacture_year_int > current_year:
                    messages.error(request, f"Manufacture year must be between 1900 and {current_year}.")
                    return render(request, 'vehicle_edit.html', {'vehicle': vehicle})
            except ValueError:
                messages.error(request, "Invalid manufacture year.")
                return render(request, 'vehicle_edit.html', {'vehicle': vehicle})

            try:
                avg_mileage_float = float(avg_mileage)
                if avg_mileage_float <= 0:
                    messages.error(request, "Average mileage must be greater than 0.")
                    return render(request, 'vehicle_edit.html', {'vehicle': vehicle})
            except ValueError:
                messages.error(request, "Invalid average mileage value.")
                return render(request, 'vehicle_edit.html', {'vehicle': vehicle})

            vehicle.vehicle_number = vehicle_number
            vehicle.vehicle_name = vehicle_name
            vehicle.model_number = model_number
            vehicle.manufacture_year = manufacture_year_int
            vehicle.owner_name = owner_name
            vehicle.avg_mileage = avg_mileage_float
            vehicle.fuel_type = fuel_type

            if request.POST.get('remove_rc_copy') == 'on':
                if vehicle.rc_copy:
                    vehicle.rc_copy.delete(save=False)
                    vehicle.rc_copy = None

            if request.POST.get('remove_insurance_copy') == 'on':
                if vehicle.insurance_copy:
                    vehicle.insurance_copy.delete(save=False)
                    vehicle.insurance_copy = None

            if request.POST.get('remove_pollution_copy') == 'on':
                if vehicle.pollution_copy:
                    vehicle.pollution_copy.delete(save=False)
                    vehicle.pollution_copy = None

            if 'rc_copy' in request.FILES and request.FILES['rc_copy']:
                if vehicle.rc_copy:
                    vehicle.rc_copy.delete(save=False)
                vehicle.rc_copy = request.FILES['rc_copy']

            if 'insurance_copy' in request.FILES and request.FILES['insurance_copy']:
                if vehicle.insurance_copy:
                    vehicle.insurance_copy.delete(save=False)
                vehicle.insurance_copy = request.FILES['insurance_copy']

            if 'pollution_copy' in request.FILES and request.FILES['pollution_copy']:
                if vehicle.pollution_copy:
                    vehicle.pollution_copy.delete(save=False)
                vehicle.pollution_copy = request.FILES['pollution_copy']

            vehicle.save()
            messages.success(request, "Vehicle updated successfully.")
            return redirect('vehicle_list')

        except IntegrityError:
            messages.error(request, "A vehicle with this number already exists.")
        except Exception as e:
            messages.error(request, f"An error occurred: {str(e)}")

    context = {
        'vehicle': vehicle,
    }
    return render(request, 'vehicle_edit.html', context)

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


def fuel_management(request):
    """
    List trips with filtering + stable 'most recent first' ordering.
    """
    fuel_entries = FuelEntry.objects.all()

    search_text = request.GET.get('search', '').strip()
    if search_text:
        text_q = Q(vehicle__vehicle_number__icontains=search_text)
        try:
            val = float(search_text)
            text_q |= Q(distance_traveled=val) | Q(fuel_cost=val)
        except ValueError:
            pass
        fuel_entries = fuel_entries.filter(text_q)

    traveler = request.GET.get('traveler', '').strip()
    if traveler:
        fuel_entries = fuel_entries.filter(travelled_by__username__icontains=traveler)

    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    if date_from:
        fuel_entries = fuel_entries.filter(date__gte=date_from)
    if date_to:
        fuel_entries = fuel_entries.filter(date__lte=date_to)

    fuel_entries = fuel_entries.annotate(
        sort_time=Coalesce('end_time', 'start_time')
    ).order_by('-date', F('sort_time').desc(nulls_last=True), '-id')

    paginator = Paginator(fuel_entries, 10)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    return render(request, 'fuel_management.html', {'page_obj': page_obj})

@login_required
def fuel_enter(request):
    """
    Start a trip and return to the listing.
    """
    if request.method == 'POST':
        try:
            vehicle = get_object_or_404(Vehicle, id=request.POST['vehicle'])
            user = request.user
            purpose = request.POST.get('purpose', '').strip()
            
            FuelEntry.objects.create(
                vehicle=vehicle,
                travelled_by=user if user.is_authenticated else None,
                date=request.POST['date'],
                start_time=request.POST['start_time'],
                purpose=purpose,
                trip_from="Trip Started",
                trip_to="In Progress",
                fuel_cost=request.POST.get('fuel_cost', 0) or 0,
                odo_start_image=request.FILES['odo_start_image'],
                odo_start_reading=request.POST['odo_start_reading'],
                odo_end_reading=request.POST['odo_start_reading'],
            )
            messages.success(request, "Trip started. You can end it later from Fuel Management → End Trip.")
            return redirect('fuel_management')
        except Exception as e:
            messages.error(request, f"Error starting trip: {str(e)}")
            return redirect('fuel_enter')

    vehicles = Vehicle.objects.all()
    return render(request, 'fuel_entre.html', {'vehicles': vehicles})

@login_required
def fuel_complete_trip(request, entry_id):
    """
    Finish a previously-started trip.
    """
    entry = get_object_or_404(FuelEntry, id=entry_id)

    if request.method == 'POST':
        try:
            entry.trip_from = request.POST.get('trip_from', entry.trip_from).strip()
            entry.trip_to = request.POST.get('trip_to', entry.trip_to).strip()
            entry.odo_end_reading = request.POST.get('odo_end_reading')
            entry.end_time = request.POST.get('end_time')

            if 'odo_end_image' in request.FILES and request.FILES['odo_end_image']:
                entry.odo_end_image = request.FILES['odo_end_image']

            entry.save()
            messages.success(request, "Trip completed successfully!")
            return redirect('fuel_management')
        except Exception as e:
            messages.error(request, f"Error completing trip: {str(e)}")

    return render(request, 'fuel_complete.html', {'entry': entry})


def fuel_edit(request, entry_id):
    """Edit existing fuel entry with all trip details."""
    fuel_entry = get_object_or_404(FuelEntry, id=entry_id)

    if request.method == 'POST':
        try:
            vehicle_id = request.POST.get('vehicle')
            if vehicle_id:
                fuel_entry.vehicle = get_object_or_404(Vehicle, id=vehicle_id)

            travelled_by_id = request.POST.get('travelled_by')
            if travelled_by_id:
                fuel_entry.travelled_by = get_object_or_404(User, id=travelled_by_id)

            date = request.POST.get('date')
            if date:
                fuel_entry.date = date
            
            start_time = request.POST.get('start_time')
            if start_time:
                fuel_entry.start_time = start_time
            
            end_time = request.POST.get('end_time')
            if end_time:
                fuel_entry.end_time = end_time

            trip_from = request.POST.get('trip_from', '').strip()
            if trip_from:
                fuel_entry.trip_from = trip_from
            
            trip_to = request.POST.get('trip_to', '').strip()
            if trip_to:
                fuel_entry.trip_to = trip_to

            purpose = request.POST.get('purpose', '').strip()
            fuel_entry.purpose = purpose

            odo_start = request.POST.get('odo_start_reading')
            if odo_start:
                fuel_entry.odo_start_reading = odo_start

            odo_end = request.POST.get('odo_end_reading')
            if odo_end:
                fuel_entry.odo_end_reading = odo_end

            fuel_cost = request.POST.get('fuel_cost')
            if fuel_cost:
                fuel_entry.fuel_cost = fuel_cost

            if 'odo_start_image' in request.FILES:
                if fuel_entry.odo_start_image:
                    try:
                        if os.path.isfile(fuel_entry.odo_start_image.path):
                            os.remove(fuel_entry.odo_start_image.path)
                    except Exception:
                        pass
                fuel_entry.odo_start_image = request.FILES['odo_start_image']
            
            if 'odo_end_image' in request.FILES:
                if fuel_entry.odo_end_image:
                    try:
                        if os.path.isfile(fuel_entry.odo_end_image.path):
                            os.remove(fuel_entry.odo_end_image.path)
                    except Exception:
                        pass
                fuel_entry.odo_end_image = request.FILES['odo_end_image']

            fuel_entry.save()
            messages.success(request, "Trip updated successfully!")
            return redirect('fuel_management')

        except ValueError as e:
            messages.error(request, f"Invalid value provided: {str(e)}")
        except Exception as e:
            messages.error(request, f"Error updating trip: {str(e)}")

    vehicles = Vehicle.objects.all()
    users = User.objects.filter(is_active=True)

    return render(request, 'fuel_edit.html', {
        'entry': fuel_entry,
        'vehicles': vehicles,
        'users': users
    })


def fuel_delete(request, entry_id):
    entry = get_object_or_404(FuelEntry, id=entry_id)
    if request.method == 'POST':
        entry.delete()
        messages.success(request, "Trip deleted.")
    return redirect('fuel_management')


def fuel_monitoring(request):
    """
    Monitoring view with date filters.
    """
    vehicles = Vehicle.objects.all()
    users    = User.objects.all()
    selected_id      = request.GET.get('vid')
    selected_user_id = request.GET.get('user_id')
    date_from        = request.GET.get('date_from')
    date_to          = request.GET.get('date_to')

    try:
        global_rate_override = float(request.GET.get('rate', 109.0))
    except (TypeError, ValueError):
        global_rate_override = 109.0

    selected_vehicle   = None
    summary            = {}
    trips              = []
    vehicle_travelers  = []

    def _entry_distance(e):
        try:
            if hasattr(e, 'distance_traveled') and callable(getattr(e, 'distance_traveled')):
                d = e.distance_traveled()
                if d is not None:
                    return float(d)
        except Exception:
            pass
        for fld in ('distance_traveled', 'distance', 'distance_km', 'km'):
            if hasattr(e, fld) and getattr(e, fld) is not None:
                try:
                    return float(getattr(e, fld))
                except Exception:
                    pass
        if (hasattr(e, 'odo_end_reading') and hasattr(e, 'odo_start_reading')
                and getattr(e, 'odo_end_reading', None) is not None
                and getattr(e, 'odo_start_reading', None) is not None):
            try:
                return float(e.odo_end_reading) - float(e.odo_start_reading)
            except Exception:
                pass
        return 0.0

    def _entry_travellers(e):
        names = []
        try:
            tb = getattr(e, 'travelled_by', None)
            if tb is None:
                return names
            try:
                iterable = tb.all()
            except Exception:
                iterable = None
            if iterable is not None:
                for u in iterable:
                    if not u:
                        continue
                    try:
                        name = u.get_full_name() if callable(getattr(u, 'get_full_name', None)) else None
                    except Exception:
                        name = None
                    if not name:
                        name = getattr(u, 'username', None) or getattr(u, 'name', None) or str(u)
                    names.append(name)
                return names
            u = tb
            if u:
                try:
                    name = u.get_full_name() if callable(getattr(u, 'get_full_name', None)) else None
                except Exception:
                    name = None
                if not name:
                    name = getattr(u, 'username', None) or getattr(u, 'name', None) or str(u)
                names.append(name)
                return names
        except Exception:
            pass
        return names

    def _entry_litres(e, distance, rate_to_use):
        for fld in ('fuel_used', 'litres', 'liters', 'litre'):
            if hasattr(e, fld) and getattr(e, fld) is not None:
                try:
                    val = float(getattr(e, fld))
                    if val >= 0:
                        return val
                except Exception:
                    pass

        try:
            cost = float(getattr(e, 'fuel_cost', None) or getattr(e, 'cost', None) or getattr(e, 'amount', None) or 0.0)
        except Exception:
            cost = 0.0

        for price_field in ('price_per_litre', 'fuel_price_per_litre', 'rate_per_litre', 'price_per_liter'):
            if hasattr(e, price_field) and getattr(e, price_field) is not None:
                try:
                    entry_rate = float(getattr(e, price_field))
                    if entry_rate > 0 and cost:
                        return cost / entry_rate
                except Exception:
                    pass

        try:
            if rate_to_use and rate_to_use > 0 and cost:
                return cost / float(rate_to_use)
        except Exception:
            pass

        return None

    if selected_id:
        selected_vehicle = get_object_or_404(Vehicle, id=selected_id)

        entries = (selected_vehicle.fuel_entries
                   .exclude(odo_end_reading__isnull=True)
                   .order_by('-date', '-start_time'))

        if selected_user_id:
            try:
                uid = int(selected_user_id)
                entries = entries.filter(travelled_by__id=uid)
            except (TypeError, ValueError):
                pass

        if date_from:
            entries = entries.filter(date__gte=date_from)
        if date_to:
            entries = entries.filter(date__lte=date_to)

        total_distance       = 0.0
        total_cost           = 0.0
        total_expected_cost  = 0.0
        total_litres         = 0.0
        total_km_from_fuel   = 0.0

        all_entries = selected_vehicle.fuel_entries.exclude(odo_end_reading__isnull=True)
        traveller_ids = set(all_entries.filter(travelled_by__isnull=False)
                                   .values_list('travelled_by__id', flat=True))
        if traveller_ids:
            vehicle_travelers = list(User.objects.filter(id__in=traveller_ids))

        if request.user.is_authenticated:
            if not any(u.id == request.user.id for u in vehicle_travelers):
                vehicle_travelers.append(request.user)

        vehicle_mileage = getattr(selected_vehicle, 'avg_mileage', None) or getattr(selected_vehicle, 'mileage', None)
        try:
            vehicle_mileage = float(vehicle_mileage) if vehicle_mileage else None
        except Exception:
            vehicle_mileage = None

        try:
            vehicle_rate_field = getattr(selected_vehicle, 'fuel_rate', None)
            if vehicle_rate_field is not None and str(vehicle_rate_field).strip() != '':
                rate_for_vehicle = float(vehicle_rate_field)
            else:
                rate_for_vehicle = float(global_rate_override)
        except Exception:
            rate_for_vehicle = float(global_rate_override)

        for e in entries:
            distance = _entry_distance(e)
            try:
                cost = float(getattr(e, 'fuel_cost', None) or getattr(e, 'cost', None) or getattr(e, 'amount', None) or 0.0)
            except Exception:
                cost = 0.0

            litres = _entry_litres(e, distance, rate_for_vehicle)
            if litres is None:
                if vehicle_mileage and vehicle_mileage > 0 and distance:
                    litres = distance / vehicle_mileage
                else:
                    litres = 0.0

            if vehicle_mileage and vehicle_mileage > 0:
                fuel_needed_for_distance = (distance / vehicle_mileage) if distance else 0.0
            else:
                fuel_needed_for_distance = None

            if fuel_needed_for_distance is not None and rate_for_vehicle is not None:
                cost_for_distance = fuel_needed_for_distance * rate_for_vehicle
            else:
                cost_for_distance = None

            if vehicle_mileage and vehicle_mileage > 0:
                km_from_fuel = litres * vehicle_mileage
            else:
                km_from_fuel = None

            allowance = litres * float(rate_for_vehicle) if rate_for_vehicle and litres else 0.0

            names = _entry_travellers(e)

            fuel_balance = (litres or 0.0) - (fuel_needed_for_distance or 0.0)

            trips.append({
                'date': getattr(e, 'date', None),
                'start_time': getattr(e, 'start_time', None),
                'end_time': getattr(e, 'end_time', None),
                'distance': distance,
                'cost': cost,
                'fuel_used': litres,
                'fuel_consumed_for_distance': fuel_needed_for_distance,
                'cost_for_distance': cost_for_distance,
                'travelled_by': ', '.join(names) if names else '—',
                'fuel_balance': fuel_balance,
            })

            total_distance += (distance or 0.0)
            total_cost += (cost or 0.0)
            total_expected_cost += (allowance or 0.0)
            total_litres += (litres or 0.0)
            total_km_from_fuel += (km_from_fuel or 0.0)

        summary = {
            'trips': entries.count(),
            'distance': total_distance,
            'cost': total_cost,
            'expected_cost': total_expected_cost,
            'total_litres': total_litres,
            'total_km_from_fuel': total_km_from_fuel,
        }

    ctx = {
        'vehicles': vehicles,
        'users': users,
        'selected_id': int(selected_id) if selected_id and str(selected_id).isdigit() else None,
        'selected_user_id': int(selected_user_id) if selected_user_id and str(selected_user_id).isdigit() else None,
        'selected_vehicle': selected_vehicle,
        'summary': summary,
        'trips': trips,
        'vehicle_travelers': vehicle_travelers,
        'date_from': date_from,
        'date_to': date_to,
    }
    return render(request, 'monitoring.html', ctx)

def total_summary(request):
    """
    Global summary across ALL vehicles with detailed table view.
    """
    qs = FuelEntry.objects.exclude(odo_end_reading__isnull=True).select_related('vehicle').order_by('-date', '-start_time')

    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    if date_from:
        qs = qs.filter(date__gte=date_from)
    if date_to:
        qs = qs.filter(date__lte=date_to)

    traveller = request.GET.get('traveler', '').strip()
    if traveller:
        qs = qs.filter(travelled_by__username__icontains=traveller)

    def _entry_distance(e):
        try:
            if hasattr(e, 'distance_traveled') and callable(getattr(e, 'distance_traveled')):
                d = e.distance_traveled()
                if d is not None:
                    return float(d)
        except Exception:
            pass
        for fld in ('distance_traveled', 'distance', 'distance_km', 'km'):
            if hasattr(e, fld) and getattr(e, fld) is not None:
                try:
                    return float(getattr(e, fld))
                except Exception:
                    pass
        if (hasattr(e, 'odo_end_reading') and hasattr(e, 'odo_start_reading')
                and getattr(e, 'odo_end_reading', None) is not None
                and getattr(e, 'odo_start_reading', None) is not None):
            try:
                return float(e.odo_end_reading) - float(e.odo_start_reading)
            except Exception:
                pass
        return 0.0

    def _entry_litres(e, distance, rate_to_use):
        for fld in ('fuel_used', 'litres', 'liters', 'litre'):
            if hasattr(e, fld) and getattr(e, fld) is not None:
                try:
                    val = float(getattr(e, fld))
                    if val >= 0:
                        return val
                except Exception:
                    pass
        try:
            cost = float(getattr(e, 'fuel_cost', None) or getattr(e, 'cost', None) or getattr(e, 'amount', None) or 0.0)
        except Exception:
            cost = 0.0
        for price_field in ('price_per_litre', 'fuel_price_per_litre', 'rate_per_litre', 'price_per_liter'):
            if hasattr(e, price_field) and getattr(e, price_field) is not None:
                try:
                    entry_rate = float(getattr(e, price_field))
                    if entry_rate > 0 and cost:
                        return cost / entry_rate
                except Exception:
                    pass
        try:
            if rate_to_use and rate_to_use > 0 and cost:
                return cost / float(rate_to_use)
        except Exception:
            pass
        mileage = getattr(e.vehicle, 'avg_mileage', None)
        try:
            mileage = float(mileage) if mileage else None
        except Exception:
            mileage = None
        if mileage and mileage > 0 and distance:
            return distance / mileage
        return 0.0

    def _entry_travellers(e):
        names = []
        try:
            tb = getattr(e, 'travelled_by', None)
            if tb is None:
                return names
            try:
                iterable = tb.all()
            except Exception:
                iterable = None
            if iterable is not None:
                for u in iterable:
                    if not u:
                        continue
                    try:
                        name = u.get_full_name() if callable(getattr(u, 'get_full_name', None)) else None
                    except Exception:
                        name = None
                    if not name:
                        name = getattr(u, 'username', None) or getattr(u, 'name', None) or str(u)
                    names.append(name)
                return names
            u = tb
            if u:
                try:
                    name = u.get_full_name() if callable(getattr(u, 'get_full_name', None)) else None
                except Exception:
                    name = None
                if not name:
                    name = getattr(u, 'username', None) or getattr(u, 'name', None) or str(u)
                names.append(name)
                return names
        except Exception:
            pass
        return names

    try:
        global_rate = float(request.GET.get('rate', 109.0))
    except (TypeError, ValueError):
        global_rate = 109.0

    vehicle_data = {}
    grand_totals = {
        'trips': 0,
        'distance': 0.0,
        'cost': 0.0,
        'litres': 0.0,
        'km_from_fuel': 0.0,
        'expected_cost': 0.0,
    }

    for e in qs:
        vehicle = e.vehicle
        vehicle_id = vehicle.id
        
        if vehicle_id not in vehicle_data:
            vehicle_data[vehicle_id] = {
                'vehicle': vehicle,
                'vehicle_number': vehicle.vehicle_number,
                'owner_name': vehicle.owner_name,
                'fuel_type': vehicle.fuel_type,
                'avg_mileage': vehicle.avg_mileage,
                'trips': 0,
                'distance': 0.0,
                'cost': 0.0,
                'litres': 0.0,
                'km_from_fuel': 0.0,
                'expected_cost': 0.0,
                'entries': []
            }

        distance = _entry_distance(e)
        cost = float(getattr(e, 'fuel_cost', None) or 0.0)
        
        try:
            v_rate = float(getattr(vehicle, 'fuel_rate', global_rate))
        except Exception:
            v_rate = global_rate

        litres = _entry_litres(e, distance, v_rate)
        
        mileage = getattr(vehicle, 'avg_mileage', None)
        try:
            mileage = float(mileage) if mileage else None
        except Exception:
            mileage = None

        km_from_fuel = (litres * mileage) if mileage else 0.0
        expected_cost = litres * v_rate
        
        fuel_consumed = (distance / mileage) if mileage and mileage > 0 else 0.0
        fuel_balance = litres - fuel_consumed

        travellers = _entry_travellers(e)

        vehicle_data[vehicle_id]['trips'] += 1
        vehicle_data[vehicle_id]['distance'] += distance
        vehicle_data[vehicle_id]['cost'] += cost
        vehicle_data[vehicle_id]['litres'] += litres
        vehicle_data[vehicle_id]['km_from_fuel'] += km_from_fuel
        vehicle_data[vehicle_id]['expected_cost'] += expected_cost
        
        vehicle_data[vehicle_id]['entries'].append({
            'date': e.date,
            'start_time': e.start_time,
            'end_time': e.end_time,
            'trip_from': e.trip_from,
            'trip_to': e.trip_to,
            'distance': distance,
            'cost': cost,
            'litres': litres,
            'fuel_consumed': fuel_consumed,
            'fuel_balance': fuel_balance,
            'km_from_fuel': km_from_fuel,
            'expected_cost': expected_cost,
            'travelled_by': ', '.join(travellers) if travellers else '—',
        })

        grand_totals['trips'] += 1
        grand_totals['distance'] += distance
        grand_totals['cost'] += cost
        grand_totals['litres'] += litres
        grand_totals['km_from_fuel'] += km_from_fuel
        grand_totals['expected_cost'] += expected_cost

    vehicles_list = sorted(vehicle_data.values(), key=lambda x: x['vehicle_number'])

    context = {
        'vehicles_data': vehicles_list,
        'grand_totals': grand_totals,
        'date_from': date_from,
        'date_to': date_to,
        'traveler': traveller,
    }
    return render(request, 'total_summary.html', context)