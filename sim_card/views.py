from django.shortcuts import render

# Create your views here.
from django.core.paginator import Paginator
from .models import SIM
from django.utils import timezone
from datetime import date

from datetime import date, timedelta
from django.contrib import messages

def sim_management(request):
    search_query = request.GET.get('q', '').strip()

    sims = SIM.objects.all().order_by('-created_at')
    if search_query:
        sims = sims.filter(
            sim_no__icontains=search_query
        ) | sims.filter(
            provider__icontains=search_query
        )

    # --- reminder logic ---
    today = date.today()
    threshold = today + timedelta(days=2)
    expiring = sims.filter(validity__lte=threshold, validity__isnull=False)
    for sim in expiring:
        days = (sim.validity - today).days
        if days < 0:
            messages.warning(request, f'SIM {sim.sim_no} has already expired!')
        elif days == 0:
            messages.warning(request, f'SIM {sim.sim_no} expires today!')
        else:
            messages.info(request, f'SIM {sim.sim_no} expires in {days} day(s).')
    # ---------------------

    for sim in sims:
        if sim.validity:
            sim.days_remaining = (sim.validity - today).days
        else:
            sim.days_remaining = None

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
        sim_no = request.POST.get("sim_no")
        provider = request.POST.get("provider")
        identify_person = request.POST.get("identify_person")
        incharge = request.POST.get("incharge")
        last_recharge_date = request.POST.get("last_recharge_date")
        amount = request.POST.get("amount")
        branch = request.POST.get("branch")
        validity = request.POST.get("validity")

        try:
            # Create the SIM
            sim = SIM.objects.create(
                sim_no=sim_no,
                provider=provider,
                identify_person=identify_person,
                incharge=incharge,
                last_recharge_date=last_recharge_date or None,
                amount=amount or None,
                branch=branch,
                validity=validity or None,
            )
            
            # Create recharge record if last_recharge_date and amount are provided
            if last_recharge_date and amount:
                SIMRecharge.objects.create(
                    sim=sim,
                    recharge_date=last_recharge_date,
                    amount=amount,
                    recharged_by=incharge or identify_person or "System",
                    notes=f"Initial recharge record"
                )
            
            messages.success(request, "SIM added successfully.")
            return redirect("sim_management")

        except IntegrityError:
            messages.error(request, f"SIM No {sim_no} already exists.")
            return redirect("add_sim")

    users = User.objects.filter(is_active=True).order_by('name')
    return render(request, "add_sim.html", {"users": users})

# app3/views.py  (add at bottom)
from django.shortcuts import get_object_or_404
from .models import SIM
from app1.models import User


def edit_sim(request, sim_id):
    sim = get_object_or_404(SIM, id=sim_id)

    if request.method == 'POST':
        # Store old values to check if recharge record needs to be created
        old_recharge_date = sim.last_recharge_date
        old_amount = sim.amount
        
        # Update SIM fields
        sim.provider = request.POST.get('provider')
        sim.identify_person = request.POST.get('identify_person')
        sim.incharge = request.POST.get('incharge')
        sim.last_recharge_date = request.POST.get('last_recharge_date') or None
        sim.amount = request.POST.get('amount') or None
        sim.branch = request.POST.get('branch')
        sim.validity = request.POST.get('validity') or None
        sim.save()

        # Check if recharge information was updated and create a new recharge record
        new_recharge_date = sim.last_recharge_date
        new_amount = sim.amount
        
        if new_recharge_date and new_amount:
            # Check if this is a new recharge (dates or amounts differ)
            if (str(old_recharge_date) != str(new_recharge_date) or 
                str(old_amount) != str(new_amount)):
                
                # Check if a recharge record already exists for this date
                existing_recharge = SIMRecharge.objects.filter(
                    sim=sim, 
                    recharge_date=new_recharge_date
                ).first()
                
                if not existing_recharge:
                    SIMRecharge.objects.create(
                        sim=sim,
                        recharge_date=new_recharge_date,
                        amount=new_amount,
                        recharged_by=sim.incharge or sim.identify_person or "System",
                        notes=f"Recharge updated via edit"
                    )

        messages.success(request, 'SIM updated successfully.')
        return redirect('sim_management')

    users = User.objects.filter(is_active=True).order_by('name')
    return render(request, 'add_sim.html', {'sim': sim, 'users': users})

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
    """Return a HTML fragment with SIMs that expire ≤ 2 days from today."""
    today = date.today()
    threshold = today + timedelta(days=2)          # next 2 days

    sims = SIM.objects.filter(
        validity__isnull=False
    ).filter(
        validity__lte=threshold
    ).order_by('validity')

    # decorate with days-remaining (same logic you already use)
    for sim in sims:
        sim.days_remaining = (sim.validity - today).days

    return render(request, 'sim_reminder.html', {'sims': sims})


# Add this view to handle manual recharge additions
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import SIM, SIMRecharge
from datetime import datetime, date


def add_recharge(request, sim_id):
    sim = get_object_or_404(SIM, id=sim_id)

    if request.method == 'POST':
        recharge_date = request.POST.get('recharge_date')
        amount = request.POST.get('amount')
        validity = request.POST.get('validity')   # new field
        recharged_by = request.POST.get('recharged_by')
        notes = request.POST.get('notes')

        if recharge_date and amount:
            # Create recharge record
            SIMRecharge.objects.create(
                sim=sim,
                recharge_date=recharge_date,
                amount=amount,
                recharged_by=recharged_by or sim.incharge or sim.identify_person or "System",
                notes=notes or "Manual recharge entry"
            )

            # Update SIM with latest values
            sim.last_recharge_date = recharge_date
            sim.amount = amount

            if validity:
                try:
                    sim.validity = datetime.strptime(validity, "%Y-%m-%d").date()
                except ValueError:
                    messages.error(request, 'Invalid validity date format.')
                    return render(request, 'add_recharge.html', {'sim': sim})

            # calculate days remaining
            if sim.validity:
                sim.days_remaining = (sim.validity - date.today()).days

            sim.save()

            messages.success(request, 'Recharge record added successfully.')
            return redirect('sim_recharge_history', sim_id=sim.id)
        else:
            messages.error(request, 'Please provide both recharge date and amount.')

    return render(request, 'add_recharge.html', {'sim': sim})



from django.shortcuts import get_object_or_404, render
from django.http import JsonResponse
from .models import SIM, SIMRecharge
from datetime import date

def sim_recharge_history(request, sim_id):
    sim = get_object_or_404(SIM, id=sim_id)
    recharges = SIMRecharge.objects.filter(sim=sim).order_by('-recharge_date')
    last = recharges.first()

    sim.last_recharge_date = last.recharge_date if last else None
    sim.amount = last.amount if last else None
    sim.days_remaining = (sim.validity - date.today()).days if sim.validity else None
    total_amount = sum(r.amount for r in recharges)

    context = {
        'sim': sim, 
        'recharges': recharges, 
        'total_amount': total_amount
    }

    # Check if it's an AJAX request
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        html = render_to_string("sim_recharge_history.html", context, request=request)
        return JsonResponse({"html": html})

    # Regular request - use the existing template for now
    return render(request, "sim_recharge_history.html", context)