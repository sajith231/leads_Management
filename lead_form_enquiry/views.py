from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import Enquiry


@login_required
def enquiry_list(request):
    enquiries = Enquiry.objects.all().order_by('-date')
    return render(request, 'enquiry_list.html', {'enquiries': enquiries})


@login_required
def enquiry_add(request):
    if request.method == 'POST':
        shop_name    = request.POST.get('shopName', '').strip()
        owner_name   = request.POST.get('ownerName', '').strip()
        location     = request.POST.get('location', '').strip()
        phone_number = request.POST.get('phoneNumber', '').strip()
        purpose      = request.POST.get('purpose', '').strip()
        notes        = request.POST.get('notes', '').strip()
        latitude     = request.POST.get('latitude', '').strip() or None
        longitude    = request.POST.get('longitude', '').strip() or None

        if shop_name and location and purpose:
            Enquiry.objects.create(
                owner_name=owner_name,
                shop_name=shop_name,
                location=location,
                phone_number=phone_number,
                purpose=purpose,
                notes=notes,
                latitude=latitude,
                longitude=longitude,
                creator=request.user.username,
            )
            return redirect('enquiry_list')

    return render(request, 'enquiry_form.html')


@login_required
def enquiry_edit(request, pk):
    enquiry = get_object_or_404(Enquiry, pk=pk)

    if request.method == 'POST':
        enquiry.shop_name    = request.POST.get('shopName', '').strip()
        enquiry.owner_name   = request.POST.get('ownerName', '').strip()
        enquiry.location     = request.POST.get('location', '').strip()
        enquiry.phone_number = request.POST.get('phoneNumber', '').strip()
        enquiry.purpose      = request.POST.get('purpose', '').strip()
        enquiry.notes        = request.POST.get('notes', '').strip()
        lat = request.POST.get('latitude', '').strip()
        lng = request.POST.get('longitude', '').strip()
        enquiry.latitude     = lat or None
        enquiry.longitude    = lng or None
        enquiry.save()
        return redirect('enquiry_list')

    return render(request, 'enquiry_edit.html', {'enquiry': enquiry})


@login_required
def enquiry_delete(request, pk):
    enquiry = get_object_or_404(Enquiry, pk=pk)
    if request.method == 'POST':
        enquiry.delete()
    return redirect('enquiry_list')