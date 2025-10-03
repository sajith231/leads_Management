from django.shortcuts import render

# Create your views here.
from django.core.paginator import Paginator
from .models import SIM
from django.utils import timezone
from datetime import date

from datetime import date, timedelta
from django.contrib import messages

def _attach_days_remaining(sim_qs):
    """
    Adds dynamic attributes:
        .expiry_date        (date or None)
        .days_remaining     (int or None)
    Now uses validity_date instead of validity_days.
    """
    today = date.today()
    for sim in sim_qs:
        if sim.validity_date:                # ← new field
            sim.expiry_date = sim.validity_date
            sim.days_remaining = (sim.validity_date - today).days
        else:
            sim.expiry_date = None
            sim.days_remaining = None
    return sim_qs

def sim_management(request):
    search_query = request.GET.get('q', '').strip()
    sims = SIM.objects.all().order_by('-created_at')

    if search_query:
        sims = sims.filter(
            sim_no__icontains=search_query
        ) | sims.filter(
            provider__icontains=search_query
        )

    today = date.today()
    # 1.  attach real expiry & days-remaining
    sims = _attach_days_remaining(sims)

    # 2.  auto-banner for soon-expired SIMs
    expiring = [s for s in sims if s.days_remaining is not None and s.days_remaining <= 2]
    for sim in expiring:
        if sim.days_remaining < 0:
            messages.warning(request, f'SIM {sim.sim_no} has already expired!')
        elif sim.days_remaining == 0:
            messages.warning(request, f'SIM {sim.sim_no} expires today!')
        else:
            messages.info(request, f'SIM {sim.sim_no} expires in {sim.days_remaining} day(s).')

    paginator = Paginator(sims, 10)
    page_number = request.GET.get('page')
    sims_page = paginator.get_page(page_number)

    return render(request, 'sim_management.html', {
        'sims': sims_page,
        'search_query': search_query
    })



from django.shortcuts import render, redirect
from .models import SIM   # make sure your model name is correct
from django.db import IntegrityError
from django.contrib import messages
from app1.models import User 



def add_sim(request):
    if request.method == "POST":
        sim_no             = request.POST.get("sim_no")
        provider           = request.POST.get("provider")
        identify_person_id = request.POST.get("identify_person")
        incharge_id        = request.POST.get("incharge")
        last_recharge_date = request.POST.get("last_recharge_date")
        amount             = request.POST.get("amount")
        recharged_by_id    = request.POST.get("recharged_by")
        branch             = request.POST.get("branch")
        validity_days      = request.POST.get("validity_days")
        validity_date      = request.POST.get("validity_date") or None

        # ---- calculate validity_date if only days given ----
        if validity_days and not validity_date:
            try:
                days = int(validity_days)
                validity_date = (
                    datetime.strptime(last_recharge_date, "%Y-%m-%d").date()
                    + timedelta(days=days)
                ).strftime("%Y-%m-%d")
            except (ValueError, TypeError):
                validity_date = None

        # ---- resolve user names ----
        identify_name = User.objects.filter(pk=identify_person_id).first().name if identify_person_id else None
        incharge_name = User.objects.filter(pk=incharge_id).first().name if incharge_id else None
        recharged_name = User.objects.filter(pk=recharged_by_id).first().name if recharged_by_id else None

        try:
            # ---- create SIM ----
            sim = SIM.objects.create(
                sim_no=sim_no,
                provider=provider,
                identify_person=identify_name,
                incharge=incharge_name,
                last_recharge_date=last_recharge_date or None,
                amount=amount or None,
                branch=branch,
                validity_date=validity_date,
                validity_days=validity_days or None,
            )

            # ---- first recharge record ----
            if last_recharge_date and amount:
                SIMRecharge.objects.create(
                    sim=sim,
                    recharge_date=last_recharge_date,
                    amount=amount,
                    validity_date=validity_date,
                    validity_days=validity_days or None,
                    recharged_by=recharged_name or incharge_name or identify_name or "System",
                    notes="Initial recharge record"
                )

            messages.success(request, "SIM added successfully.")
            return redirect("sim_management")

        except IntegrityError:
            messages.error(request, f"SIM No {sim_no} already exists.")
            return redirect("add_sim")

    # GET request - prepare context
    users = User.objects.filter(is_active=True).order_by('name')
    
    # Get current logged-in user
    current_user = request.user if request.user.is_authenticated else None
    
    context = {
        "users": users,
        "current_user": current_user
    }
    
    return render(request, "add_sim.html", context)
# app3/views.py  (add at bottom)
# ----------  views.py  ----------
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import SIM, SIMRecharge
from app1.models import User

def _latest_recharge(sim: SIM) -> SIMRecharge | None:
    """Return the most recent recharge row for this SIM."""
    return SIMRecharge.objects.filter(sim=sim).order_by('-recharge_date').first()

def edit_sim(request, sim_id):
    sim = get_object_or_404(SIM, id=sim_id)

    # Calculate validity_days from validity_date if needed (for display)
    if sim.validity_date and sim.last_recharge_date and not sim.validity_days:
        try:
            days_diff = (sim.validity_date - sim.last_recharge_date).days
            if days_diff > 0:
                sim.validity_days = days_diff
        except (TypeError, ValueError):
            pass

    if request.method == 'POST':
        # --- convert pk → name ---
        identify_id = request.POST.get('identify_person')
        incharge_id = request.POST.get('incharge')
        recharged_by_id = request.POST.get('recharged_by')
        
        identify_name = User.objects.filter(pk=identify_id).first().name if identify_id else None
        incharge_name = User.objects.filter(pk=incharge_id).first().name if incharge_id else None
        recharged_name = User.objects.filter(pk=recharged_by_id).first().name if recharged_by_id else None

        # Calculate validity_date from validity_days if provided
        validity_days = request.POST.get('validity_days')
        last_recharge_date = request.POST.get('last_recharge_date')
        validity_date = request.POST.get('validity_date')
        
        if validity_days and last_recharge_date and not validity_date:
            try:
                days = int(validity_days)
                validity_date = (
                    datetime.strptime(last_recharge_date, "%Y-%m-%d").date()
                    + timedelta(days=days)
                ).strftime("%Y-%m-%d")
            except (ValueError, TypeError):
                validity_date = None

        # update SIM fields
        sim.sim_no = request.POST.get('sim_no')
        sim.provider = request.POST.get('provider')
        sim.identify_person = identify_name
        sim.incharge = incharge_name
        sim.branch = request.POST.get('branch')
        sim.last_recharge_date = last_recharge_date or None
        sim.amount = request.POST.get('amount') or None
        sim.validity_days = validity_days or None
        sim.validity_date = validity_date or None
        sim.save()

        # Update or create recharge record if recharge data exists
        if last_recharge_date and request.POST.get('amount'):
            last_recharge = _latest_recharge(sim)
            
            if last_recharge:
                # Update existing recharge record
                last_recharge.recharge_date = last_recharge_date
                last_recharge.amount = request.POST.get('amount')
                last_recharge.validity_date = validity_date
                last_recharge.validity_days = validity_days or None
                last_recharge.recharged_by = recharged_name or sim.incharge or sim.identify_person or 'System'
                last_recharge.notes = 'Updated via SIM edit'
                last_recharge.save()
            else:
                # Create new recharge record
                SIMRecharge.objects.create(
                    sim=sim,
                    recharge_date=last_recharge_date,
                    amount=request.POST.get('amount'),
                    validity_date=validity_date,
                    validity_days=validity_days or None,
                    recharged_by=recharged_name or sim.incharge or sim.identify_person or 'System',
                    notes='Initial recharge record from SIM edit'
                )

        messages.success(request, 'SIM updated successfully.')
        return redirect('sim_management')

    # GET request - prepare context with current user
    users = User.objects.filter(is_active=True).order_by('name')
    current_user = request.user if request.user.is_authenticated else None
    
    return render(request, 'add_sim.html', {
        'sim': sim,
        'users': users,
        'current_user': current_user  # Added for auto-selection
    })

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from .models import SIM

def delete_sim(request, sim_id):
    if request.method == 'POST':
        sim = get_object_or_404(SIM, id=sim_id)
        sim.delete()
        messages.success(request, f'SIM {sim.sim_no} deleted.')
    return redirect('sim_management')


from datetime import date, timedelta
from django.shortcuts import render
from .models import SIM

def sim_reminder(request):
    """
    Return HTML fragment with SIMs whose *validity_date* is ≤ 2 days away.
    """
    today = date.today()
    threshold = today + timedelta(days=2)

    # 1.  fetch only SIMs that have a validity_date
    sims = SIM.objects.filter(
        last_recharge_date__isnull=False,
        validity_date__isnull=False          # ← new field
    )

    # 2.  attach dynamic expiry / days-remaining
    sims = _attach_days_remaining(sims)      # already uses validity_date now

    # 3.  keep those that expire within next 2 days
    sims = [s for s in sims
            if s.days_remaining is not None and s.days_remaining <= 2]

    # 4.  sort by soonest expiry
    sims.sort(key=lambda s: s.expiry_date)

    return render(request, 'sim_reminder.html', {'sims': sims})


# Add this view to handle manual recharge additions
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import SIM, SIMRecharge
from datetime import datetime, date


# ----------  add_recharge view (no 'validity' field anywhere)  ----------
from app1.models import User   # already imported

def add_recharge(request, sim_id):
    sim = get_object_or_404(SIM, id=sim_id)
    users = User.objects.filter(is_active=True).order_by('name')

    if request.method == 'POST':
        recharge_date = request.POST.get('recharge_date')
        amount        = request.POST.get('amount')
        validity_days = request.POST.get('validity_days')
        validity_date = request.POST.get('validity_date') or None
        recharged_by_id = request.POST.get('recharged_by')
        notes         = request.POST.get('notes')

        if recharge_date and amount:
            # ---- calculate validity_date if only days given ----
            if validity_days and not validity_date:
                try:
                    days = int(validity_days)
                    validity_date = (
                        datetime.strptime(recharge_date, "%Y-%m-%d").date()
                        + timedelta(days=days)
                    ).strftime("%Y-%m-%d")
                except ValueError:
                    validity_date = None

            # ---- resolve user name ----
            recharged_user = User.objects.filter(pk=recharged_by_id).first() if recharged_by_id else None
            recharged_name = (
                recharged_user.name if recharged_user
                else sim.incharge or sim.identify_person or "System"
            )

            # ---- create recharge history row ----
            SIMRecharge.objects.create(
                sim=sim,
                recharge_date=recharge_date,
                amount=amount,
                validity_date=validity_date,
                validity_days=validity_days or None,
                recharged_by=recharged_name,
                notes=notes or "Manual recharge entry"
            )

            # ---- keep SIM header in sync ----
            sim.last_recharge_date = recharge_date
            sim.amount       = amount
            sim.validity_date = validity_date
            sim.validity_days = validity_days or None
            sim.save()

            messages.success(request, 'Recharge record added successfully.')
            return redirect('sim_recharge_history', sim_id=sim.id)
        else:
            messages.error(request, 'Recharge date and amount are required.')

    # GET request - prepare context
    current_user = request.user if request.user.is_authenticated else None
    
    context = {
        'sim': sim,
        'users': users,
        'current_user': current_user
    }
    
    return render(request, 'add_recharge.html', context)


from django.shortcuts import get_object_or_404, render
from django.http import JsonResponse
from .models import SIM, SIMRecharge
from datetime import date

def sim_recharge_history(request, sim_id):
    sim = get_object_or_404(SIM, id=sim_id)
    recharges = SIMRecharge.objects.filter(sim=sim).order_by('-recharge_date')

    # decorate with latest recharge info
    last = recharges.first()
    sim.last_recharge_date = last.recharge_date if last else None
    sim.amount = last.amount if last else None

    # decorate with expiry / days-left  (uses validity_days, not validity)
    _attach_days_remaining([sim])          # single-object list, same helper

    total_amount = sum(r.amount for r in recharges)

    context = {
        'sim': sim,
        'recharges': recharges,
        'total_amount': total_amount,
    }

    # optional AJAX response
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        html = render_to_string('sim_recharge_history.html', context, request=request)
        return JsonResponse({'html': html})

    return render(request, 'sim_recharge_history.html', context)



def delete_recharge(request, recharge_id):
    """Delete a single recharge record and return to its history page."""
    recharge = get_object_or_404(SIMRecharge, id=recharge_id)
    sim_id = recharge.sim.id
    recharge.delete()
    messages.success(request, 'Recharge record deleted.')
    return redirect('sim_recharge_history', sim_id=sim_id)



from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages

from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from app1.models import User          # NEW
from .models import SIMRecharge

def edit_recharge(request, pk):
    recharge = get_object_or_404(SIMRecharge, id=pk)
    sim = recharge.sim
    users = User.objects.filter(is_active=True).order_by('name')

    # Calculate validity_days from validity_date if needed (for display)
    if recharge.validity_date and recharge.recharge_date and not recharge.validity_days:
        try:
            days_diff = (recharge.validity_date - recharge.recharge_date).days
            if days_diff > 0:
                recharge.validity_days = days_diff
        except (TypeError, ValueError):
            pass

    if request.method == 'POST':
        user_pk = request.POST.get('recharged_by')
        selected_user = get_object_or_404(User, pk=user_pk) if user_pk else None

        # Calculate validity_date from validity_days if provided
        validity_days = request.POST.get('validity_days')
        recharge_date = request.POST.get('recharge_date')
        validity_date = request.POST.get('validity_date')
        
        if validity_days and recharge_date and not validity_date:
            try:
                days = int(validity_days)
                validity_date = (
                    datetime.strptime(recharge_date, "%Y-%m-%d").date()
                    + timedelta(days=days)
                ).strftime("%Y-%m-%d")
            except (ValueError, TypeError):
                validity_date = None

        # ---- read & save the recharge row ----
        recharge.recharge_date = recharge_date
        recharge.amount = request.POST.get('amount')
        recharge.validity_days = validity_days or None
        recharge.validity_date = validity_date or None
        recharge.recharged_by = selected_user.name if selected_user else ''
        recharge.notes = request.POST.get('notes')
        recharge.save()

        # ---- ALWAYS sync header with the newest recharge ----
        latest = SIMRecharge.objects.filter(sim=sim).order_by('-recharge_date').first()
        if latest:
            sim.last_recharge_date = latest.recharge_date
            sim.amount = latest.amount
            sim.validity_date = latest.validity_date
            sim.validity_days = latest.validity_days
            sim.save()

        messages.success(request, 'Recharge updated.')
        return redirect('sim_recharge_history', sim_id=sim.id)

    return render(request, 'edit_recharge.html',
                  {'recharge': recharge, 'users': users})