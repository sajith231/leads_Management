from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Campaigning
from software_master.models import Software
from datetime import datetime

@login_required
def campaigning_list(request):
    # Only get non-deleted campaigns
    campaigns = Campaigning.objects.filter(is_deleted=False).order_by('-campaign_id')
    
    # Pagination - 10 entries per page
    paginator = Paginator(campaigns, 10)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # Calculate display indices
    start_index = (page_obj.number - 1) * paginator.per_page + 1
    end_index = start_index + len(page_obj.object_list) - 1
    
    context = {
        'campaigns': page_obj,
        'start_index': start_index,
        'end_index': end_index,
        'total_count': campaigns.count()
    }
    return render(request, 'campaigning_list.html', context)


@login_required
def campaigning_add(request):
    softwares = Software.objects.all()
    
    if request.method == "POST":
        from_date = datetime.strptime(request.POST.get('from_date'), '%Y-%m-%d').date()
        to_date = datetime.strptime(request.POST.get('to_date'), '%Y-%m-%d').date()
        number_of_days = (to_date - from_date).days + 1
        
        Campaigning.objects.create(
            campaign_name=request.POST.get('campaign_name'),
            software_name=request.POST.get('software_name'),
            status=request.POST.get('status', 'draft'),
            from_date=from_date,
            to_date=to_date,
            number_of_days=number_of_days,
            location=request.POST.get('location'),
            total_amount=request.POST.get('total_amount'),
            total_reach=request.POST.get('total_reach') or 0,
            total_impression=request.POST.get('total_impression') or 0,
            total_leads=request.POST.get('total_leads') or 0,
            created_by=request.user  # Add the logged-in user
        )
        messages.success(request, 'Campaign added successfully!')
        return redirect('campaigning_list')
    
    return render(request, 'campaigning_form.html', {'softwares': softwares})


@login_required
def campaigning_edit(request, pk):
    campaign = get_object_or_404(Campaigning, pk=pk, is_deleted=False)
    softwares = Software.objects.all()
    
    if request.method == "POST":
        from_date = datetime.strptime(request.POST.get('from_date'), '%Y-%m-%d').date()
        to_date = datetime.strptime(request.POST.get('to_date'), '%Y-%m-%d').date()
        number_of_days = (to_date - from_date).days + 1
        
        campaign.campaign_name = request.POST.get('campaign_name')
        campaign.software_name = request.POST.get('software_name')
        campaign.status = request.POST.get('status', 'draft')
        campaign.from_date = from_date
        campaign.to_date = to_date
        campaign.number_of_days = number_of_days
        campaign.location = request.POST.get('location')
        campaign.total_amount = request.POST.get('total_amount')
        campaign.total_reach = request.POST.get('total_reach') or 0
        campaign.total_impression = request.POST.get('total_impression') or 0
        campaign.total_leads = request.POST.get('total_leads') or 0
        campaign.save()
        messages.success(request, 'Campaign updated successfully!')
        return redirect('campaigning_list')
    
    return render(request, 'campaigning_form.html', {'campaign': campaign, 'softwares': softwares})


@login_required
def campaigning_delete(request, pk):
    campaign = get_object_or_404(Campaigning, pk=pk, is_deleted=False)
    campaign.is_deleted = True
    campaign.save()
    messages.success(request, 'Campaign deleted successfully!')
    return redirect('campaigning_list')