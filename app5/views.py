from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_http_methods
from django.views.decorators.csrf import csrf_exempt
from .models import JobCard, JobCardImage
import os
import json
import logging

# Set up logging
logger = logging.getLogger(__name__)

def jobcard_list(request):
    jobcards = JobCard.objects.all().order_by('-created_at')
    
    # Prepare data for template
    for jobcard in jobcards:
        # Group images by item_index
        jobcard.images_by_item = {}
        for image in jobcard.images.all():
            item_index = image.item_index
            if item_index not in jobcard.images_by_item:
                jobcard.images_by_item[item_index] = []
            jobcard.images_by_item[item_index].append(image)
    
    return render(request, 'jobcard_list.html', {'jobcards': jobcards})

@csrf_exempt
def jobcard_create(request):
    if request.method == 'POST':
        customer = request.POST.get('customer', '').strip()
        address = request.POST.get('address', '').strip()
        phone = request.POST.get('phone', '').strip()

        # Validate required fields
        if not customer or not address or not phone:
            messages.error(request, "Customer name, address, and phone are required fields.")
            return redirect('jobcard_create')

        # Get all items and their data
        items = request.POST.getlist('items[]')
        serials = request.POST.getlist('serials[]')
        configs = request.POST.getlist('configs[]')
        status_list = request.POST.getlist('status[]')
        
        # Build items_data structure
        items_data = []
        
        for idx, item_name in enumerate(items):
            if not item_name.strip():
                continue
                
            serial = serials[idx] if idx < len(serials) else ''
            config = configs[idx] if idx < len(configs) else ''
            status = status_list[idx] if idx < len(status_list) else 'logged'
            
            # Get complaints for this item
            complaint_descriptions = request.POST.getlist(f'complaints-{idx}[]')
            complaint_notes = request.POST.getlist(f'complaint_notes-{idx}[]')
            
            complaints = []
            for complaint_idx, description in enumerate(complaint_descriptions):
                if description.strip():
                    notes = complaint_notes[complaint_idx] if complaint_idx < len(complaint_notes) else ''
                    complaints.append({
                        'description': description.strip(),
                        'notes': notes.strip()
                    })
            
            # If no complaints, add a default one
            if not complaints:
                complaints.append({
                    'description': 'General complaint',
                    'notes': ''
                })
            
            items_data.append({
                'item': item_name,
                'serial': serial,
                'config': config,
                'status': status,
                'complaints': complaints
            })

        # Create single job card with all items and complaints
        if items_data:
            job_card = JobCard.objects.create(
                customer=customer,
                address=address,
                phone=phone,
                items_data=items_data
            )

            # Save images with proper indexing
            for item_idx, item_name in enumerate(items):
                if not item_name.strip():
                    continue
                    
                # Get complaints count for this item to know how many complaint indices we have
                complaint_descriptions = request.POST.getlist(f'complaints-{item_idx}[]')
                valid_complaints = [desc for desc in complaint_descriptions if desc.strip()]
                
                if not valid_complaints:
                    valid_complaints = ['General complaint']  # Default
                
                # For each complaint, save images
                for complaint_idx in range(len(valid_complaints)):
                    images = request.FILES.getlist(f'images-{item_idx}-{complaint_idx}[]')
                    for image in images:
                        JobCardImage.objects.create(
                            jobcard=job_card, 
                            image=image,
                            item_index=item_idx,
                            complaint_index=complaint_idx
                        )

            messages.success(request, f"Job card created successfully with {len(items_data)} items.")
        else:
            messages.error(request, "At least one item is required.")
            
        return redirect('jobcard_list')

    # For GET request, show the form with available items
    items = ["Mouse", "Keyboard", "CPU", "Laptop", "Desktop", "Printer", "Monitor", "Other"]
    return render(request, 'jobcard_form.html', {'items': items})

@require_http_methods(["POST"])
def update_jobcard_status(request, pk):
    """Update status for a specific item in a job card"""
    try:
        # Parse JSON data
        data = json.loads(request.body)
        new_status = data.get('status')
        item_index = data.get('item_index', 0)
        
        logger.info(f"Status update request - JobCard: {pk}, Item Index: {item_index}, New Status: {new_status}")
        
        # Validate status
        valid_statuses = dict(JobCard.STATUS_CHOICES).keys()
        if new_status not in valid_statuses:
            return JsonResponse({
                "success": False, 
                "error": f"Invalid status: {new_status}"
            }, status=400)
        
        # Get job card
        jobcard = get_object_or_404(JobCard, pk=pk)
        
        # Update status for specific item
        if jobcard.items_data and item_index < len(jobcard.items_data):
            jobcard.items_data[item_index]['status'] = new_status
            jobcard.save()
            
            # Get display name for status
            status_display = dict(JobCard.STATUS_CHOICES).get(new_status, new_status)
            
            logger.info(f"Status updated successfully - JobCard: {pk}, Item: {item_index}, Status: {new_status}")
            
            return JsonResponse({
                "success": True, 
                "status": status_display,
                "message": f"Status updated to {status_display}"
            })
        else:
            return JsonResponse({
                "success": False, 
                "error": f"Item index {item_index} not found"
            }, status=404)
            
    except JobCard.DoesNotExist:
        logger.error(f"JobCard {pk} not found")
        return JsonResponse({"success": False, "error": "Job card not found"}, status=404)
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON data in request")
        return JsonResponse({"success": False, "error": "Invalid JSON data"}, status=400)
    except Exception as e:
        logger.error(f"Error updating status for JobCard {pk}: {str(e)}")
        return JsonResponse({"success": False, "error": str(e)}, status=500)

@require_POST
def delete_ticket_by_number(request, ticket_no):
    """Delete job card by ticket number"""
    try:
        logger.info(f"Delete request for ticket: {ticket_no}")
        
        jobcard = get_object_or_404(JobCard, ticket_no=ticket_no)
        
        # Delete all associated images
        for image in jobcard.images.all():
            if image.image and os.path.isfile(image.image.path):
                try:
                    os.remove(image.image.path)
                    logger.info(f"Deleted image file: {image.image.path}")
                except OSError as e:
                    logger.warning(f"Could not delete image file {image.image.path}: {e}")
            image.delete()
        
        customer_name = jobcard.customer
        customer_phone = jobcard.phone
        total_items = jobcard.get_total_items()
        total_complaints = jobcard.get_total_complaints()
        items_list = ', '.join(jobcard.get_items_list())
        
        jobcard.delete()
        logger.info(f"Successfully deleted JobCard {ticket_no} for {customer_name}")
        
        return JsonResponse({
            "success": True, 
            "message": f"✅ Successfully deleted complete ticket <strong>{ticket_no}</strong> for customer <strong>{customer_name}</strong> (Phone: {customer_phone}). <br>📋 Deleted {total_items} item(s) with {total_complaints} complaint(s): <strong>{items_list}</strong>"
        })
        
    except JobCard.DoesNotExist:
        logger.error(f"JobCard with ticket {ticket_no} not found")
        return JsonResponse({
            "success": False, 
            "error": f"No job card found with ticket number: {ticket_no}"
        }, status=404)
    except Exception as e:
        logger.error(f"Error deleting ticket {ticket_no}: {str(e)}")
        return JsonResponse({
            "success": False, 
            "error": f"⚠️ An error occurred while deleting ticket {ticket_no}: {str(e)}"
        }, status=500)

# Alternative delete method (for backwards compatibility)
@csrf_exempt
@require_http_methods(["POST", "DELETE"])
def delete_jobcard(request, jobcard_id):
    """Delete job card by ID"""
    try:
        logger.info(f"Delete request for JobCard ID: {jobcard_id}")
        
        jobcard = get_object_or_404(JobCard, pk=jobcard_id)
        
        # Delete all associated images
        for image in jobcard.images.all():
            if image.image and os.path.isfile(image.image.path):
                try:
                    os.remove(image.image.path)
                    logger.info(f"Deleted image file: {image.image.path}")
                except OSError as e:
                    logger.warning(f"Could not delete image file {image.image.path}: {e}")
            image.delete()
        
        customer_name = jobcard.customer
        ticket_no = jobcard.ticket_no
        jobcard.delete()
        logger.info(f"Successfully deleted JobCard {jobcard_id} ({ticket_no}) for {customer_name}")
        
        return JsonResponse({
            "success": True, 
            "message": f"Successfully deleted job card {ticket_no} for {customer_name}"
        })
        
    except JobCard.DoesNotExist:
        logger.error(f"JobCard {jobcard_id} not found")
        return JsonResponse({
            "success": False, 
            "error": f"No job card found with ID: {jobcard_id}"
        }, status=404)
    except Exception as e:
        logger.error(f"Error deleting JobCard {jobcard_id}: {str(e)}")
        return JsonResponse({
            "success": False, 
            "error": f"An error occurred while deleting: {str(e)}"
        }, status=500)

@csrf_exempt
def jobcard_edit(request, pk):
    jobcard = get_object_or_404(JobCard, pk=pk)
    
    if request.method == 'POST':
        try:
            # Get customer info from form
            customer = request.POST.get('customer', '').strip()
            address = request.POST.get('address', '').strip()
            phone = request.POST.get('phone', '').strip()

            # Validate required fields
            if not customer or not address or not phone:
                messages.error(request, "Customer name, address, and phone are required fields.")
                return redirect('jobcard_edit', pk=pk)

            # Keep track of images to preserve
            keep_images = set(request.POST.getlist('keep_images[]'))
            
            # Delete existing images that are not being kept
            for image in jobcard.images.all():
                if str(image.id) not in keep_images:
                    if image.image and os.path.isfile(image.image.path):
                        try:
                            os.remove(image.image.path)
                        except OSError:
                            pass
                    image.delete()

            # Get all items and their data from the form
            items = request.POST.getlist('items[]')
            serials = request.POST.getlist('serials[]')
            configs = request.POST.getlist('configs[]')
            
            # Get status for each item
            status_list = []
            for idx in range(len(items)):
                status_key = f'status-{idx}'
                status = request.POST.get(status_key, 'logged')
                status_list.append(status)
            
            # Build new items_data structure
            items_data = []
            
            for idx, item_name in enumerate(items):
                if not item_name.strip():
                    continue
                    
                serial = serials[idx] if idx < len(serials) else ''
                config = configs[idx] if idx < len(configs) else ''
                status = status_list[idx] if idx < len(status_list) else 'logged'
                
                # Get complaints for this item
                complaint_descriptions = request.POST.getlist(f'complaints-{idx}[]')
                complaint_notes = request.POST.getlist(f'complaint_notes-{idx}[]')
                complaint_ids = request.POST.getlist(f'complaint_ids-{idx}[]')
                
                complaints = []
                for complaint_idx, description in enumerate(complaint_descriptions):
                    if description.strip():
                        notes = complaint_notes[complaint_idx] if complaint_idx < len(complaint_notes) else ''
                        complaint_id = complaint_ids[complaint_idx] if complaint_idx < len(complaint_ids) else 0
                        complaints.append({
                            'description': description.strip(),
                            'notes': notes.strip(),
                            'id': int(complaint_id) if complaint_id and complaint_id != '0' else None
                        })
                
                # If no complaints, add a default one
                if not complaints:
                    complaints.append({
                        'description': 'General complaint',
                        'notes': '',
                        'id': None
                    })
                
                items_data.append({
                    'item': item_name,
                    'serial': serial,
                    'config': config,
                    'status': status,
                    'complaints': complaints
                })

            # Update the job card
            jobcard.customer = customer
            jobcard.address = address
            jobcard.phone = phone
            jobcard.items_data = items_data
            jobcard.save()

            # Handle new images for each item
            for item_idx, item_name in enumerate(items):
                if not item_name.strip():
                    continue
                    
                # Handle new images for this item
                new_images = request.FILES.getlist(f'new_images-{item_idx}[]')
                for image in new_images:
                    JobCardImage.objects.create(
                        jobcard=jobcard, 
                        image=image,
                        item_index=item_idx,
                        complaint_index=0  # All images for the item
                    )

            messages.success(request, f"Job card {jobcard.ticket_no} updated successfully with {len(items_data)} items.")
            return redirect('jobcard_list')
        
        except Exception as e:
            logger.error(f"Error editing JobCard {pk}: {str(e)}")
            messages.error(request, f"An error occurred: {str(e)}")
            return redirect('jobcard_edit', pk=pk)
    
    # For GET request, prepare data for the edit form
    items = []
    
    if jobcard.items_data:
        for item_idx, item_data in enumerate(jobcard.items_data):
            # Get ALL images for this item (regardless of complaint_index)
            item_images = list(jobcard.images.filter(item_index=item_idx).values('id', 'image'))
            
            # Convert image paths to URLs
            for img in item_images:
                if img['image']:
                    img['url'] = f"/media/{img['image']}"
                else:
                    img['url'] = ''
            
            # Build complaints list
            complaints = []
            for complaint in item_data.get('complaints', []):
                complaint_info = {
                    'id': complaint.get('id', 0),
                    'description': complaint.get('description', ''),
                    'notes': complaint.get('notes', '')
                }
                complaints.append(complaint_info)
            
            if not complaints:
                complaints = [{
                    'id': 0,
                    'description': '',
                    'notes': ''
                }]
            
            items.append({
                'name': item_data.get('item', ''),
                'serial': item_data.get('serial', ''),
                'config': item_data.get('config', ''),
                'status': item_data.get('status', 'logged'),
                'complaints': complaints,
                'images': item_images  # All images for this item
            })
    
    # Ensure we have at least one item for the form
    if not items:
        items = [{
            'name': '',
            'serial': '',
            'config': '',
            'status': 'logged',
            'complaints': [{
                'id': 0,
                'description': '',
                'notes': ''
            }],
            'images': []
        }]
    
    context = {
        'jobcard': jobcard,
        'items': items,
        'status_choices': JobCard.STATUS_CHOICES
    }
    
    return render(request, 'jobcard_edit.html', context)

@csrf_exempt
def api_jobcard_detail(request, pk):
    if request.method == 'GET':
        try:
            jobcard = get_object_or_404(JobCard, pk=pk)
            
            data = {
                'ticket_no': jobcard.ticket_no,
                'customer': jobcard.customer,
                'address': jobcard.address,
                'phone': jobcard.phone,
                'items': []
            }
            
            if jobcard.items_data:
                for item_idx, item_data in enumerate(jobcard.items_data):
                    # Get images for this item
                    item_images = {}
                    for img in jobcard.images.filter(item_index=item_idx):
                        complaint_idx = img.complaint_index
                        if complaint_idx not in item_images:
                            item_images[complaint_idx] = []
                        item_images[complaint_idx].append({
                            'id': img.id,
                            'url': img.image.url
                        })
                    
                    # Build complaints with images
                    complaints = []
                    for complaint_idx, complaint in enumerate(item_data.get('complaints', [])):
                        complaints.append({
                            'description': complaint.get('description', ''),
                            'notes': complaint.get('notes', ''),
                            'images': item_images.get(complaint_idx, [])
                        })
                    
                    data['items'].append({
                        'name': item_data.get('item', ''),
                        'serial': item_data.get('serial', ''),
                        'config': item_data.get('config', ''),
                        'status': item_data.get('status', 'logged'),
                        'complaints': complaints
                    })
            
            return JsonResponse(data)
        except Exception as e:
            logger.error(f"Error fetching JobCard {pk} details: {str(e)}")
            return JsonResponse({'error': str(e)}, status=500)