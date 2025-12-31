from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q

from .models import SoftwareComplaint
from software_master.models import Software
from app1.models import Branch, User

import json
import requests
import os
from datetime import datetime
import base64
import re
import unicodedata


@login_required
def software_update(request):
    # Get all complaints
    complaints = SoftwareComplaint.objects.all()
    
    # Get filter parameters
    search_query = request.GET.get('search', '').strip()
    branch_filter = request.GET.get('branch', '').strip()
    software_filter = request.GET.get('software', '').strip()  # NEW: Software filter
    date_from = request.GET.get('date_from', '').strip()
    date_to = request.GET.get('date_to', '').strip()
    status_filter = request.GET.get('status', '').strip()
    
    # Apply search filter (searches across multiple fields)
    if search_query:
        complaints = complaints.filter(
            Q(client_name__icontains=search_query) |
            Q(branch__icontains=search_query) |
            Q(software__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(status__icontains=search_query) |
            Q(requested_by__username__icontains=search_query) |
            Q(requested_by__first_name__icontains=search_query) |
            Q(requested_by__last_name__icontains=search_query)
        )
    
    # Apply branch filter
    if branch_filter:
        complaints = complaints.filter(branch__icontains=branch_filter)
    
    # Apply software filter - NEW
    if software_filter:
        complaints = complaints.filter(software__icontains=software_filter)
    
    # Apply status filter
    if status_filter:
        complaints = complaints.filter(status=status_filter)
    
    # Apply date range filter
    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d')
            complaints = complaints.filter(created_at__date__gte=date_from_obj)
        except ValueError:
            pass
    
    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d')
            complaints = complaints.filter(created_at__date__lte=date_to_obj)
        except ValueError:
            pass
    
    # Order by latest first
    complaints = complaints.order_by('-created_at')
    
    # Get all branches and softwares for filter dropdowns
    branches = Branch.objects.all().order_by('name')
    softwares = Software.objects.all().order_by('name')  # NEW
    
    # Pagination
    page = request.GET.get('page', 1)
    paginator = Paginator(complaints, 10)  # Show 10 complaints per page
    
    try:
        complaints_page = paginator.page(page)
    except PageNotAnInteger:
        complaints_page = paginator.page(1)
    except EmptyPage:
        complaints_page = paginator.page(paginator.num_pages)
    
    context = {
        'complaints': complaints_page,
        'branches': branches,
        'softwares': softwares,  # NEW
        'search_query': search_query,
        'branch_filter': branch_filter,
        'software_filter': software_filter,  # NEW
        'date_from': date_from,
        'date_to': date_to,
        'status_filter': status_filter,
        'total_count': paginator.count,
    }
    
    return render(request, 'software_update.html', context)


@login_required
def get_rrc_clients(request):
    try:
        response = requests.get(
            'https://accmaster.imcbs.com/api/sync/rrc-clients/',
            timeout=10
        )
        response.raise_for_status()
        return JsonResponse(response.json(), safe=False)
    except requests.RequestException as e:
        return JsonResponse({'error': str(e)}, status=500)


def sanitize_filename(filename):
    """
    Thoroughly clean filename to prevent encoding issues
    """
    # Normalize unicode characters
    filename = unicodedata.normalize('NFKD', filename)
    
    # Remove any non-ASCII characters
    filename = filename.encode('ascii', 'ignore').decode('ascii')
    
    # Split into name and extension
    name, ext = os.path.splitext(filename)
    
    # Keep only alphanumeric, underscores, and hyphens
    name = re.sub(r'[^\w\-]', '_', name)
    
    # Remove multiple underscores
    name = re.sub(r'_+', '_', name)
    
    # Remove leading/trailing underscores
    name = name.strip('_')
    
    # Ensure we have a name
    if not name:
        name = 'file'
    
    return f"{name}{ext}"


@login_required
def software_add(request):
    branches = Branch.objects.all()
    softwares = Software.objects.all()

    if request.method == 'POST':
        client_name = request.POST.get('client_name')
        branch_id = request.POST.get('branch')
        software_id = request.POST.get('software')
        description = request.POST.get('description')
        voice_note = request.POST.get('voice_note')

        branch = get_object_or_404(Branch, id=branch_id)
        software = get_object_or_404(Software, id=software_id)

        # ---------- FIXED IMAGE UPLOAD (MULTIPLE) ----------
        image_paths = []
        
        # Get all uploaded files
        for key in request.FILES:
            if key.startswith('images'):
                images = request.FILES.getlist(key)
                for idx, img in enumerate(images, 1):
                    # Generate timestamp with microseconds for uniqueness
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S%f')
                    
                    # Sanitize filename completely
                    safe_name = sanitize_filename(img.name)
                    filename = f"{timestamp}_img{idx}_{safe_name}"
                    
                    # Build path
                    filepath = os.path.join('software_complaints', filename)
                    
                    try:
                        # Save file
                        saved_path = default_storage.save(filepath, img)
                        image_paths.append(saved_path)
                        print(f"Saved image: {saved_path}")  # Debug log
                    except Exception as e:
                        messages.warning(request, f'Failed to upload image {idx}: {str(e)}')
                        print(f"Error saving image: {e}")  # Debug log

        # ---------- VOICE NOTE ----------
        voice_note_path = None
        if voice_note and voice_note.startswith('data:audio'):
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S%f')
            voice_filename = f"voice_{timestamp}.wav"
            voice_filepath = os.path.join('voice_notes', voice_filename)

            audio_data = voice_note.split(',')[1]
            audio_bytes = base64.b64decode(audio_data)

            from django.core.files.base import ContentFile
            voice_note_path = default_storage.save(voice_filepath, ContentFile(audio_bytes))

        # Create complaint with default status 'Pending' and logged-in user
        complaint = SoftwareComplaint.objects.create(
            client_name=client_name,
            branch=branch.name,
            software=software.name,
            description=description,
            images=json.dumps(image_paths) if image_paths else None,
            voice_note=voice_note_path,
            status='Pending',
            requested_by=request.user  # Add the logged-in user
        )
        
        print(f"Created complaint with {len(image_paths)} images")  # Debug log

        messages.success(request, f'Complaint submitted successfully with {len(image_paths)} image(s)!')
        return redirect('software_update')

    return render(request, 'software_add.html', {
        'branches': branches,
        'softwares': softwares
    })


@login_required
def software_update_status(request, pk):
    """
    Update the status of a software complaint via dropdown
    """
    if request.method == 'POST':
        complaint = get_object_or_404(SoftwareComplaint, pk=pk)
        new_status = request.POST.get('status')
        
        # Validate status
        valid_statuses = ['Pending', 'In Review', 'Under Development', 'Completed']
        if new_status in valid_statuses:
            old_status = complaint.status
            complaint.status = new_status
            complaint.save()
            messages.success(request, f'Status updated from "{old_status}" to "{new_status}"')
        else:
            messages.error(request, 'Invalid status selected')
    
    # Preserve filters when redirecting
    return redirect(request.META.get('HTTP_REFERER', 'software_update'))


@login_required
def software_edit(request, pk):
    complaint = get_object_or_404(SoftwareComplaint, pk=pk)
    branches = Branch.objects.all()
    softwares = Software.objects.all()

    if request.method == 'POST':
        complaint.client_name = request.POST.get('client_name')
        complaint.description = request.POST.get('description')
        complaint.status = request.POST.get('status', 'Pending')

        branch_id = request.POST.get('branch')
        software_id = request.POST.get('software')

        if branch_id:
            branch = get_object_or_404(Branch, id=branch_id)
            complaint.branch = branch.name

        if software_id:
            software = get_object_or_404(Software, id=software_id)
            complaint.software = software.name

        # ---------- HANDLE DELETED IMAGES ----------
        deleted_images_json = request.POST.get('deleted_images', '[]')
        try:
            deleted_images = json.loads(deleted_images_json)
            # Delete files from storage
            for img_path in deleted_images:
                if default_storage.exists(img_path):
                    default_storage.delete(img_path)
                    print(f"Deleted image: {img_path}")
        except Exception as e:
            print(f"Error deleting images: {e}")

        # Get existing images (minus deleted ones)
        existing_images = []
        if complaint.images:
            try:
                all_existing = json.loads(complaint.images)
                existing_images = [img for img in all_existing if img not in deleted_images]
            except:
                existing_images = []

        # ---------- VOICE NOTE ----------
        voice_note = request.POST.get('voice_note')
        if voice_note and voice_note.startswith('data:audio'):
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S%f')
            voice_filename = f"voice_{timestamp}.wav"
            voice_filepath = os.path.join('voice_notes', voice_filename)

            audio_data = voice_note.split(',')[1]
            audio_bytes = base64.b64decode(audio_data)

            from django.core.files.base import ContentFile
            complaint.voice_note = default_storage.save(voice_filepath, ContentFile(audio_bytes))

        # ---------- ADD NEW IMAGES ----------
        new_image_paths = []
        for key in request.FILES:
            if key.startswith('images'):
                images = request.FILES.getlist(key)
                for idx, img in enumerate(images, 1):
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S%f')
                    
                    # Sanitize filename completely
                    safe_name = sanitize_filename(img.name)
                    filename = f"{timestamp}_img{idx}_{safe_name}"
                    
                    # Build path
                    filepath = os.path.join('software_complaints', filename)
                    
                    try:
                        # Save file
                        saved_path = default_storage.save(filepath, img)
                        new_image_paths.append(saved_path)
                        print(f"Added new image: {saved_path}")
                    except Exception as e:
                        messages.warning(request, f'Failed to upload image {idx}: {str(e)}')
        
        # Combine existing (minus deleted) and new images
        all_images = existing_images + new_image_paths
        complaint.images = json.dumps(all_images) if all_images else None
        
        if deleted_images:
            messages.info(request, f'Removed {len(deleted_images)} image(s)')
        if new_image_paths:
            messages.info(request, f'Added {len(new_image_paths)} new image(s)')
        
        complaint.save()
        messages.success(request, f'Complaint updated successfully! Total images: {len(all_images)}')
        return redirect('software_update')

    return render(request, 'software_edit.html', {
        'complaint': complaint,
        'branches': branches,
        'softwares': softwares,
        'MEDIA_URL': settings.MEDIA_URL
    })


@login_required
def software_delete(request, pk):
    complaint = get_object_or_404(SoftwareComplaint, pk=pk)

    # Delete images
    if complaint.images:
        try:
            image_paths = json.loads(complaint.images)
            for img_path in image_paths:
                if default_storage.exists(img_path):
                    default_storage.delete(img_path)
        except Exception:
            pass

    # Delete voice note
    if complaint.voice_note:
        if default_storage.exists(complaint.voice_note):
            default_storage.delete(complaint.voice_note)

    complaint.delete()
    messages.success(request, 'Complaint deleted successfully!')
    
    # Preserve filters when redirecting
    return redirect(request.META.get('HTTP_REFERER', 'software_update'))


@login_required
def software_details(request, pk):
    complaint = get_object_or_404(SoftwareComplaint, pk=pk)

    image_list = []
    if complaint.images:
        try:
            image_list = json.loads(complaint.images)
            print(f"Loading images for complaint {pk}: {image_list}")  # Debug log
        except json.JSONDecodeError:
            image_list = []
            print(f"JSON decode error for complaint {pk}")  # Debug log

    return render(request, 'update_details.html', {
        'complaint': complaint,
        'image_list': image_list,
        'MEDIA_URL': settings.MEDIA_URL
    })