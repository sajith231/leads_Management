import os
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.db import IntegrityError
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Vehicle, FuelEntry
from app1.models import User

from django.core.paginator import Paginator
from django.db.models import Q
from django.contrib.auth import get_user_model

User = get_user_model()


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
    """Display list of all fuel entries with search/filter support."""
    fuel_entries = FuelEntry.objects.all().order_by('-date', '-id')

    # --- 1. text search ------------------------------------------------------
    search_text = request.GET.get('search', '').strip()
    if search_text:
        # vehicle number (text)
        text_q = Q(vehicle__vehicle_number__icontains=search_text)

        # distance & cost – only if the input is a valid number
        if search_text.isdigit():
            text_q |= Q(distance_traveled=int(search_text))
            text_q |= Q(fuel_cost=int(search_text))
        else:
            # accept floats like “120.5”
            try:
                val = float(search_text)
                text_q |= Q(distance_traveled=val)
                text_q |= Q(fuel_cost=val)
            except ValueError:
                pass          # not numeric – ignore these fields

        fuel_entries = fuel_entries.filter(text_q)

    # --- 2. traveller filter -------------------------------------------------
    traveler = request.GET.get('traveler', '').strip()
    if traveler:
        fuel_entries = fuel_entries.filter(
            travelled_by__username__icontains=traveler)

    # --- 3. date filters -----------------------------------------------------
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    if date_from:
        fuel_entries = fuel_entries.filter(date__gte=date_from)
    if date_to:
        fuel_entries = fuel_entries.filter(date__lte=date_to)

    # --- 4. pagination (unchanged) ------------------------------------------
    paginator = Paginator(fuel_entries, 10)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    return render(request, 'fuel_management.html',
                  {'fuel_entries': page_obj, 'page_obj': page_obj})


@login_required
def fuel_enter(request):
    """Handle fuel entry form submission - START of trip only."""
    if request.method == 'POST':
        try:
            # Get vehicle from form
            vehicle_id = request.POST['vehicle']
            vehicle = get_object_or_404(Vehicle, id=vehicle_id)

            # Get the authenticated user
            user = request.user
            if user.is_authenticated:
                # Create initial trip entry with start data only
                fuel_entry = FuelEntry.objects.create(
                    vehicle=vehicle,
                    travelled_by=user,  # Set logged-in user
                    date=request.POST['date'],
                    start_time=request.POST['start_time'],
                    trip_from="Trip Started",
                    trip_to="In Progress",
                    fuel_cost=request.POST['fuel_cost'],
                    odo_start_image=request.FILES['odo_start_image'],
                    odo_start_reading=request.POST['odo_start_reading'],
                    odo_end_reading=request.POST['odo_start_reading'],
                )
                messages.success(request, "Trip started successfully. Complete the trip by adding end details.")
                return redirect('fuel_complete_trip', entry_id=fuel_entry.id)
            else:
                messages.error(request, "User authentication failed. Please log in again.")
                return redirect('fuel_enter')

        except Exception as e:
            messages.error(request, f"Error starting trip: {str(e)}")
            return redirect('fuel_enter')

    # GET request - show form with vehicles
    vehicles = Vehicle.objects.all()
    last_odometer = FuelEntry.get_last_odometer_reading() if hasattr(FuelEntry, 'get_last_odometer_reading') else None
    return render(request, 'fuel_entre.html', {
        'last_odometer': last_odometer,
        'vehicles': vehicles
    })


@login_required
def fuel_complete_trip(request, entry_id):
    """Complete the trip by adding end details."""
    fuel_entry = get_object_or_404(FuelEntry, id=entry_id)

    if request.method == 'POST':
        try:
            fuel_entry.trip_from = request.POST.get('trip_from', '').strip()
            fuel_entry.trip_to = request.POST.get('trip_to', '').strip()
            fuel_entry.odo_end_reading = request.POST.get('odo_end_reading')
            fuel_entry.end_time = request.POST.get('end_time')

            if 'odo_end_image' in request.FILES:
                fuel_entry.odo_end_image = request.FILES['odo_end_image']

            fuel_entry.save()
            messages.success(request, "Trip completed successfully!")
            return redirect('fuel_management')

        except Exception as e:
            messages.error(request, f"Error completing trip: {str(e)}")

    return render(request, 'fuel_complete.html', {'entry': fuel_entry})


def fuel_edit(request, entry_id):
    """Edit existing fuel entry."""
    fuel_entry = get_object_or_404(FuelEntry, id=entry_id)

    if request.method == 'POST':
        try:
            # Update basic trip information
            vehicle_id = request.POST['vehicle']
            fuel_entry.vehicle = get_object_or_404(Vehicle, id=vehicle_id)

            # Update travelled_by if provided
            travelled_by_id = request.POST.get('travelled_by')
            if travelled_by_id:
                fuel_entry.travelled_by = get_object_or_404(User, id=travelled_by_id)

            # Update odometer readings
            fuel_entry.odo_start_reading = request.POST['odo_start_reading']

            # Update end reading if provided
            odo_end_reading = request.POST.get('odo_end_reading')
            if odo_end_reading:
                fuel_entry.odo_end_reading = odo_end_reading

            # Update fuel cost
            fuel_entry.fuel_cost = request.POST['fuel_cost']

            # Handle file updates - only update if new file is provided
            if 'odo_start_image' in request.FILES:
                fuel_entry.odo_start_image = request.FILES['odo_start_image']
            if 'odo_end_image' in request.FILES:
                fuel_entry.odo_end_image = request.FILES['odo_end_image']

            fuel_entry.save()
            messages.success(request, "Trip updated successfully!")
            return redirect('fuel_management')

        except Exception as e:
            messages.error(request, f"Error updating trip: {str(e)}")

    # GET request - show form with existing data
    vehicles = Vehicle.objects.all()
    users = User.objects.all()

    return render(request, 'fuel_edit.html', {
        'entry': fuel_entry,
        'vehicles': vehicles,
        'users': users
    })


def fuel_delete(request, entry_id):
    """Delete fuel entry."""
    if request.method == 'POST':
        try:
            fuel_entry = get_object_or_404(FuelEntry, id=entry_id)
            fuel_entry.delete()
            messages.success(request, "Trip entry deleted successfully.")
        except Exception as e:
            messages.error(request, f"Error deleting trip entry: {str(e)}")

    return redirect('fuel_management')


def fuel_monitoring(request):
    """
    Monitoring view (improved):
    - rate_per_litre: default override via ?rate= (used as "today's" rate)
    - Uses per-entry recorded litres if present (fields like fuel_used, litres, liters, litre).
    - If per-entry price-per-litre exists (fields like price_per_litre, fuel_price_per_litre), uses that to derive litres from cost.
    - If neither recorded litres nor per-entry rate exist, try deriving litres from (fuel_cost / today's rate).
    - If still unknown and vehicle.avg_mileage exists, compute litres = distance / avg_mileage.
    - allowance is computed using the selected "today's" rate (the value from the form / ?rate=) so the user can compare actual cost vs what it would cost today.
    - Robust handling for missing/zero distances or mileage.
    """
    vehicles = Vehicle.objects.all()
    users = User.objects.all()  # for the user filter select
    selected_id = request.GET.get('vid')
    selected_user_id = request.GET.get('user_id')

    # allow override via ?rate= ; default 109
    try:
        rate_per_litre = float(request.GET.get('rate', 109.0))
    except (TypeError, ValueError):
        rate_per_litre = 109.0

    selected_vehicle = None
    summary = {}
    trips = []
    vehicle_travelers = []  # users who have traveled this vehicle (for display)

    def _entry_distance(e):
        # try distance_traveled() method if available
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

    # Helper to determine litres used for an entry (robust priority order)
    def _entry_litres(e, distance, today_rate):
        """
        Priority:
         1) explicit recorded litres on entry (fields: fuel_used, litres, liters, litre)
         2) if entry stores a per-entry price_per_litre (price_per_litre, fuel_price_per_litre),
            and fuel_cost is present -> litres = cost / entry_rate
         3) if fuel_cost present and today_rate is provided -> litres = cost / today_rate
         4) if vehicle mileage exists and distance > 0 -> litres = distance / mileage
         5) fallback -> 0.0
        """
        # 1) explicit litres recorded
        for fld in ('fuel_used', 'litres', 'liters', 'litre'):
            if hasattr(e, fld) and getattr(e, fld) is not None:
                try:
                    val = float(getattr(e, fld))
                    if val >= 0:
                        return val
                except Exception:
                    pass

        # fetch recorded cost if available
        cost = None
        try:
            cost = float(getattr(e, 'fuel_cost', None) or getattr(e, 'cost', None) or getattr(e, 'amount', None) or 0.0)
        except Exception:
            cost = 0.0

        # 2) per-entry rate present -> use it to derive litres
        for price_field in ('price_per_litre', 'fuel_price_per_litre', 'rate_per_litre', 'price_per_liter'):
            if hasattr(e, price_field) and getattr(e, price_field) is not None:
                try:
                    entry_rate = float(getattr(e, price_field))
                    if entry_rate > 0 and cost:
                        return cost / entry_rate
                except Exception:
                    pass

        # 3) use today's rate to derive litres from cost (if cost present and today_rate > 0)
        try:
            if today_rate and today_rate > 0 and cost:
                return cost / float(today_rate)
        except Exception:
            pass

        # 4) derive from distance and vehicle mileage (if both present)
        # Note: vehicle_mileage should be passed in or extracted outside; here we return None to be handled.
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

        total_distance = 0.0
        total_cost = 0.0
        total_expected_cost = 0.0

        traveller_ids = set(entries.filter(travelled_by__isnull=False)
                                   .values_list('travelled_by__id', flat=True))
        if traveller_ids:
            vehicle_travelers = list(User.objects.filter(id__in=traveller_ids))

        if request.user.is_authenticated:
            if not any(u.id == request.user.id for u in vehicle_travelers):
                vehicle_travelers.append(request.user)

        # get vehicle mileage (if available)
        vehicle_mileage = getattr(selected_vehicle, 'avg_mileage', None) or getattr(selected_vehicle, 'mileage', None)
        try:
            vehicle_mileage = float(vehicle_mileage) if vehicle_mileage else None
        except Exception:
            vehicle_mileage = None

        for e in entries:
            distance = _entry_distance(e)
            try:
                cost = float(getattr(e, 'fuel_cost', None) or getattr(e, 'cost', None) or getattr(e, 'amount', None) or 0.0)
            except Exception:
                cost = 0.0

            cost_per_km = (cost / distance) if distance else 0.0

            # Determine fuel_used robustly
            litres = _entry_litres(e, distance, rate_per_litre)
            if litres is None:
                # if litres could not be found via cost or explicit fields, try mileage fallback
                if vehicle_mileage and vehicle_mileage > 0 and distance:
                    litres = distance / vehicle_mileage
                else:
                    litres = 0.0

            # allowance = how much this trip would cost using "today's" rate (the rate from the UI)
            allowance = litres * float(rate_per_litre)
            saving = allowance - cost  # positive => expected (today) > actual => saved (money in pocket)

            names = _entry_travellers(e)

            trips.append({
                'date': getattr(e, 'date', None),
                'start_time': getattr(e, 'start_time', None),
                'end_time': getattr(e, 'end_time', None),
                'distance': distance,
                'cost': cost,
                'cost_per_km': cost_per_km,
                'fuel_used': litres,
                'allowance': allowance,
                'saving': saving,
                'travelled_by': ', '.join(names) if names else '—'
            })

            total_distance += (distance or 0.0)
            total_cost += (cost or 0.0)
            total_expected_cost += (allowance or 0.0)

        avg_cost_per_km = (total_cost / total_distance) if total_distance else 0.0

        summary = {
            'trips': entries.count(),
            'distance': total_distance,
            'cost': total_cost,
            'cost_per_km': avg_cost_per_km,
            'expected_cost': total_expected_cost,
            'saving_total': (total_expected_cost - total_cost),
            'rate_per_litre': rate_per_litre,
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
    }
    return render(request, 'monitoring.html', ctx)
