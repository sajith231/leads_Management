from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import Enquiry
from common.cloudflare_storage import upload_to_cloudflare


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

        image = request.FILES.get('image') or None
        audio = request.FILES.get('audio') or None
        
        cloudflare_image_url = None
        cloudflare_image_key = None
        cloudflare_audio_url = None
        cloudflare_audio_key = None
        
        # Upload image to Cloudflare
        if image:
            result = upload_to_cloudflare(image, folder_name='enquiry_files/images')
            if result['success']:
                cloudflare_image_url = result['r2_url']
                cloudflare_image_key = result['file_key']
                image = None  # Clear local file since we have Cloudflare URL
            else:
                # If Cloudflare upload fails, keep local file
                pass
        
        # Upload audio to Cloudflare
        if audio:
            result = upload_to_cloudflare(audio, folder_name='enquiry_files/audio')
            if result['success']:
                cloudflare_audio_url = result['r2_url']
                cloudflare_audio_key = result['file_key']
                audio = None  # Clear local file since we have Cloudflare URL
            else:
                # If Cloudflare upload fails, keep local file
                pass

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
                image=image,
                audio=audio,
                cloudflare_image_url=cloudflare_image_url,
                cloudflare_image_key=cloudflare_image_key,
                cloudflare_audio_url=cloudflare_audio_url,
                cloudflare_audio_key=cloudflare_audio_key,
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

        # Handle image update
        if request.FILES.get('image'):
            image_file = request.FILES['image']
            result = upload_to_cloudflare(image_file, folder_name='enquiry_files/images')
            if result['success']:
                enquiry.cloudflare_image_url = result['r2_url']
                enquiry.cloudflare_image_key = result['file_key']
                enquiry.image = None
            else:
                enquiry.image = image_file
        
        # Handle audio update
        if request.FILES.get('audio'):
            audio_file = request.FILES['audio']
            result = upload_to_cloudflare(audio_file, folder_name='enquiry_files/audio')
            if result['success']:
                enquiry.cloudflare_audio_url = result['r2_url']
                enquiry.cloudflare_audio_key = result['file_key']
                enquiry.audio = None
            else:
                enquiry.audio = audio_file

        enquiry.save()
        return redirect('enquiry_list')

    return render(request, 'enquiry_edit.html', {'enquiry': enquiry})


@login_required
def enquiry_delete(request, pk):
    enquiry = get_object_or_404(Enquiry, pk=pk)
    if request.method == 'POST':
        enquiry.delete()
    return redirect('enquiry_list')