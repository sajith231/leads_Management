# views.py (updated)

# At the top of views.py, add these imports
from .models import (
    JobCard, JobCardImage, Item, Supplier, 
    WarrantyTicket, WarrantyItemLog, StandbyIssuance,
    ServiceBilling, ServiceItem,RequirementItem  # Add these
)
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from app2.models import StandbyItem, StandbyImage
from app1.models import Complaint  
import os
import json
from collections import defaultdict
import requests
from django.core.paginator import Paginator
from django.utils import timezone
from app1.models import User 
from decimal import Decimal, InvalidOperation
from django.conf import settings


def jobcard_list(request):
    jobcards = JobCard.objects.all().order_by('-created_at')
    
    # Add pagination
    paginator = Paginator(jobcards, 25)  # Show 25 job cards per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get counts for each status
    status_counts = {
        'total': JobCard.objects.count(),
        'logged': JobCard.objects.filter(status='logged').count(),
        'sent_technician': JobCard.objects.filter(status='sent_technician').count(),
        'pending': JobCard.objects.filter(status='pending').count(),
        'completed': JobCard.objects.filter(status='completed').count(),
        'returned': JobCard.objects.filter(status='returned').count(),
        'rejected': JobCard.objects.filter(status='rejected').count(),
    }
    
    context = {
        'page_obj': page_obj,
        'status_counts': status_counts,
    }
    return render(request, 'jobcard_list.html', context)

import logging
from datetime import datetime
import requests

from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages

logger = logging.getLogger(__name__)

# Add this import at the top of your app5/views.py
from purchase_order.models import Item as PurchaseItem, Department

@csrf_exempt
def jobcard_create(request):
    if request.method == 'POST':
        # ... existing POST logic remains the same ...
        customer = request.POST.get('customer', '').strip()
        address = request.POST.get('address', '').strip()
        phone = request.POST.get('phone', '').strip()
        
        # Check if self-assigned
        self_assigned = request.POST.get('self_assigned') == 'true'
        technician = None
        assigned_date = None

        # Creator
        creator = None
        creator_name = "Unknown"
        if request.session.get('custom_user_id'):
            try:
                creator = User.objects.get(id=request.session['custom_user_id'])
                creator_name = getattr(creator, "name", creator.username if hasattr(creator, 'username') else str(creator))
            except User.DoesNotExist:
                pass
        
        if self_assigned:
            status = 'sent_technician'
            assigned_date = timezone.now()
            technician = creator_name if creator else "Self-Assigned User"
        else:
            status = 'logged'

        if not customer or not address or not phone:
            messages.error(request, "Customer name, address, and phone are required fields.")
            return redirect('app5:jobcard_create')

        items = request.POST.getlist('items[]')
        serials = request.POST.getlist('serials[]')
        configs = request.POST.getlist('configs[]')
        warranties = request.POST.getlist('warranty[]')
        take_to_offices = request.POST.getlist('take_to_office[]')
        suppliers = request.POST.getlist('supplier[]')
        ticket_nos = request.POST.getlist('warranty_ticket_no[]')
        warranty_customers = request.POST.getlist('warranty_customer_name[]')
        warranty_items = request.POST.getlist('warranty_item_name[]')

        items_data = []

        for idx, item_name in enumerate(items):
            if not item_name:
                continue

            warranty_value = warranties[idx] if idx < len(warranties) else "no"
            take_to_office_value = take_to_offices[idx] if idx < len(take_to_offices) else "no"

            item_entry = {
                "item": item_name,
                "serial": serials[idx] if idx < len(serials) else "",
                "config": configs[idx] if idx < len(configs) else "",
                "status": status,
                "complaints": [],
                "warranty": warranty_value,
                "take_to_office": take_to_office_value,
            }

            if warranty_value == 'yes':
                item_entry["warranty_details"] = {
                    "supplier": suppliers[idx] if idx < len(suppliers) else "",
                    "ticket_no": ticket_nos[idx] if idx < len(ticket_nos) else "",
                    "customer_name": warranty_customers[idx] if idx < len(warranty_customers) else customer,
                    "item_name": warranty_items[idx] if idx < len(warranty_items) else item_name,
                }
            else:
                item_entry["warranty_details"] = None

            # Complaints for this item
            complaint_descriptions = request.POST.getlist(f'complaints-{idx}[]')
            complaint_notes = request.POST.getlist(f'complaint_notes-{idx}[]')
            
            for complaint_idx, description in enumerate(complaint_descriptions):
                if not description.strip():
                    continue
                item_entry["complaints"].append({
                    "description": description,
                    "notes": complaint_notes[complaint_idx] if complaint_idx < len(complaint_notes) else '',
                    "images": []
                })

            items_data.append(item_entry)

        # Create Job Card
        job_card = JobCard.objects.create(
            customer=customer,
            address=address,
            phone=phone,
            status=status,
            items_data=items_data,
            created_by=creator,
            technician=technician,
            assigned_date=assigned_date,
            self_assigned=self_assigned
        )

        # Save complaint images
        for idx, item_name in enumerate(items):
            complaint_descriptions = request.POST.getlist(f'complaints-{idx}[]')
            for complaint_idx, description in enumerate(complaint_descriptions):
                if not description.strip():
                    continue
                images = request.FILES.getlist(f'images-{idx}-{complaint_idx}[]')
                for image in images:
                    JobCardImage.objects.create(
                        jobcard=job_card,
                        image=image,
                        item_index=idx,
                        complaint_index=complaint_idx
                    )
                    try:
                        if idx < len(items_data) and complaint_idx < len(items_data[idx]["complaints"]):
                            items_data[idx]["complaints"][complaint_idx]["images"].append(image.name)
                    except Exception as e:
                        logger.debug(f"Error attaching image: {e}")

        # Update job card with final items_data
        job_card.items_data = items_data
        job_card.save()

        # WhatsApp Notification (existing code)
        # ... [WhatsApp notification code remains the same] ...

        success_message = f"Job card #{job_card.ticket_no} created successfully with {len(items_data)} item(s)."
        if self_assigned:
            success_message += f" Self-assigned to {technician}."
        
        messages.success(request, success_message)
        return redirect('app5:jobcard_list')
    

    # âœ… GET Request - USE PURCHASE_ORDER ITEMS
    try:
        # Get items from purchase_order app with section field
        from purchase_order.models import Item as POItem
        purchase_items = POItem.objects.filter(is_active=True).order_by('section', 'name')
        
        # Group items by section for the template
        items_by_section = {}
        for item in purchase_items:
            section = item.section or 'GENERAL'
            if section not in items_by_section:
                items_by_section[section] = []
            items_by_section[section].append(item)
        
        logger.info(f"✅ Loaded {purchase_items.count()} items from purchase_order")
        using_po_items = True
        
        # Get departments for filtering (optional)
        departments = Department.objects.filter(is_active=True).order_by('name')
        
    except Exception as e:
        logger.error(f"Error loading purchase items: {e}")
        # Fallback to app5 items if purchase_order is not available
        from .models import Item as App5Item
        purchase_items = App5Item.objects.all().order_by('name')
        items_by_section = {'GENERAL': list(purchase_items)}
        departments = []
        using_po_items = False
    
    # Get suppliers from purchase_order
    try:
        from purchase_order.models import Supplier as POSupplier
        suppliers = POSupplier.objects.filter(is_active=True).order_by('name')
    except ImportError:
        from .models import Supplier
        suppliers = Supplier.objects.filter(is_active=True).order_by('name')

    hardware_complaints = Complaint.objects.filter(complaint_type='hardware').order_by('description')

    # Fetch customer data from API
    customer_data = []
    try:
        api_url = "https://accmaster.imcbs.com/api/sync/rrc-clients/"
        response = requests.get(api_url, timeout=10)
        if response.status_code == 200:
            customer_data = response.json()
            for customer in customer_data:
                customer['address'] = customer.get('address', '')
                customer['phone_number'] = customer.get('mobile', '')
                customer['branch'] = customer.get('branch', '')
    except Exception as e:
        logger.warning("Error fetching customer data: %s", e)

    return render(request, 'jobcard_form.html', {
        'items_by_section': items_by_section,  # âœ… Using purchase_order items
        'departments': departments,  # âœ… Optional: for filtering
        'customer_data': customer_data,
        'suppliers': suppliers,
        'hardware_complaints': hardware_complaints,
    })




@require_POST
def delete_jobcard(request, pk):
    try:
        jobcard = get_object_or_404(JobCard, pk=pk)
        for image in jobcard.images.all():
            if image.image and os.path.isfile(image.image.path):
                os.remove(image.image.path)
            image.delete()
        jobcard.delete()
        return JsonResponse({"success": True, "message": "Deleted successfully."})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})


@require_POST
def delete_ticket_by_number(request, ticket_no):
    try:
        jobcards = JobCard.objects.filter(ticket_no=ticket_no)
        if not jobcards.exists():
            return JsonResponse({"success": False, "error": f"No job cards found with ticket number: {ticket_no}"})

        first_jobcard = jobcards.first()
        customer_name = first_jobcard.customer
        customer_phone = first_jobcard.phone
        deleted_count = 0
        deleted_items = []

        for jobcard in jobcards:
            if isinstance(jobcard.items_data, list):
                for item in jobcard.items_data:
                    deleted_items.append(item.get("item", "Unknown"))

            for image in jobcard.images.all():
                if image.image and os.path.isfile(image.image.path):
                    try:
                        os.remove(image.image.path)
                    except OSError:
                        pass
                image.delete()
            jobcard.delete()
            deleted_count += 1

        return JsonResponse({
            "success": True,
            "message": (
                f"âœ… Deleted complete ticket <strong>{ticket_no}</strong> "
                f"for customer <strong>{customer_name}</strong> (Phone: {customer_phone}).<br>"
                f"ðŸ“‹ Deleted {deleted_count} job card(s) for items: <strong>{', '.join(set(deleted_items))}</strong>"
            )
        })

    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})


@csrf_exempt
def jobcard_edit(request, pk):
    jobcard = get_object_or_404(JobCard, pk=pk)

    if request.method == "POST":
        # --- Update customer info ---
        jobcard.customer = request.POST.get("customer", "").strip()
        jobcard.address = request.POST.get("address", "").strip()
        jobcard.phone = request.POST.get("phone", "").strip()
        jobcard.status = request.POST.get("status", "logged")

        # Get form data for items
        device_categories = request.POST.getlist("device_category[]")
        items = request.POST.getlist("items[]")
        serials = request.POST.getlist("serials[]")
        configs = request.POST.getlist("configs[]")
        
        # New fields from create form
        warranties = request.POST.getlist("warranty[]")
        take_to_offices = request.POST.getlist("take_to_office[]")
        suppliers = request.POST.getlist("supplier[]")
        ticket_nos = request.POST.getlist("warranty_ticket_no[]")
        warranty_customers = request.POST.getlist("warranty_customer_name[]")
        warranty_items = request.POST.getlist("warranty_item_name[]")
        
        items_data = []

        for idx, item_name in enumerate(items):
            if not item_name.strip():
                continue

            # Get device category for this item
            device_category = device_categories[idx] if idx < len(device_categories) else ""
            
            # Get warranty and office values
            warranty_value = warranties[idx] if idx < len(warranties) else "no"
            take_to_office_value = take_to_offices[idx] if idx < len(take_to_offices) else "no"
            
            item_entry = {
                "device_category": device_category,
                "item": item_name,
                "serial": serials[idx] if idx < len(serials) else "",
                "config": configs[idx] if idx < len(configs) else "",
                "warranty": warranty_value,
                "take_to_office": take_to_office_value,
                "complaints": []
            }

            # Add warranty details if applicable
            if warranty_value == 'yes':
                item_entry["warranty_details"] = {
                    "supplier": suppliers[idx] if idx < len(suppliers) else "",
                    "ticket_no": ticket_nos[idx] if idx < len(ticket_nos) else "",
                    "customer_name": warranty_customers[idx] if idx < len(warranty_customers) else jobcard.customer,
                    "item_name": warranty_items[idx] if idx < len(warranty_items) else item_name,
                }
            else:
                item_entry["warranty_details"] = None

            # Get complaint data
            complaint_ids = request.POST.getlist(f"complaint_ids-{idx}[]")
            complaint_descriptions = request.POST.getlist(f"complaints-{idx}[]")
            complaint_notes = request.POST.getlist(f"complaint_notes-{idx}[]")
            
            # Handle existing images to keep
            keep_images = request.POST.getlist("keep_images[]")
            
            # Delete images marked for removal
            JobCardImage.objects.filter(jobcard=jobcard, item_index=idx).exclude(id__in=keep_images).delete()

            for c_idx, description in enumerate(complaint_descriptions):
                if not description.strip():
                    continue
                    
                complaint_id = complaint_ids[c_idx] if c_idx < len(complaint_ids) else ""
                
                complaint_entry = {
                    "id": complaint_id,
                    "description": description,
                    "notes": complaint_notes[c_idx] if c_idx < len(complaint_notes) else "",
                    "images": []
                }

                # Handle newly uploaded images for this complaint
                new_images = request.FILES.getlist(f"new_images-{idx}[]")
                for image in new_images:
                    img_obj = JobCardImage.objects.create(
                        jobcard=jobcard,
                        image=image,
                        item_index=idx,
                        complaint_index=c_idx
                    )
                    complaint_entry["images"].append({
                        "id": img_obj.id,
                        "url": img_obj.image.url,
                        "name": img_obj.image.name
                    })

                # Add existing images for this complaint
                existing_images = JobCardImage.objects.filter(
                    jobcard=jobcard, 
                    item_index=idx, 
                    complaint_index=c_idx,
                    id__in=keep_images
                )
                for img_obj in existing_images:
                    complaint_entry["images"].append({
                        "id": img_obj.id,
                        "url": img_obj.image.url,
                        "name": img_obj.image.name
                    })

                item_entry["complaints"].append(complaint_entry)

            items_data.append(item_entry)

        jobcard.items_data = items_data
        jobcard.save()

        messages.success(request, "Job card updated successfully.")
        return redirect("app5:jobcard_edit", pk=jobcard.pk)

    # --- GET: Show form ---
    # Try to get items from purchase_order app (same as create view)
    try:
        # Get items from purchase_order app with section field
        from purchase_order.models import Item as POItem
        purchase_items = POItem.objects.filter(is_active=True).order_by('section', 'name')
        
        # Group items by section for the template
        items_by_section = {}
        for item in purchase_items:
            section = item.section or 'GENERAL'
            if section not in items_by_section:
                items_by_section[section] = []
            items_by_section[section].append(item)
        
        logger.info(f"✅ Edit form: Loaded {purchase_items.count()} items from purchase_order")
        using_po_items = True
        
    except Exception as e:
        logger.error(f"Error loading purchase items for edit: {e}")
        # Fallback if purchase_order is not available
        items_by_section = {
            "GENERAL": [{"name": "General Item 1"}, {"name": "General Item 2"}],
            "HARDWARE": [{"name": "Mouse"}, {"name": "Keyboard"}, {"name": "Monitor"}],
            "SOFTWARE": [{"name": "Windows OS"}, {"name": "MS Office"}],
            "PAPER_ROLLS": [{"name": "Thermal Paper Roll"}],
        }
    
    # Get suppliers from purchase_order (same as create view)
    try:
        from purchase_order.models import Supplier as POSupplier
        suppliers = POSupplier.objects.filter(is_active=True).order_by('name')
    except ImportError:
        from .models import Supplier
        suppliers = Supplier.objects.filter(is_active=True).order_by('name')
    
    # Get hardware complaints
    hardware_complaints = Complaint.objects.filter(complaint_type='hardware').order_by('description')
    
    # Get customer data from API (same as create view)
    customer_data = []
    try:
        api_url = "https://accmaster.imcbs.com/api/sync/rrc-clients/"
        response = requests.get(api_url, timeout=10)
        if response.status_code == 200:
            customer_data = response.json()
            for customer in customer_data:
                customer['address'] = customer.get('address', '')
                customer['phone_number'] = customer.get('mobile', '')
                customer['branch'] = customer.get('branch', '')
    except Exception as e:
        logger.warning("Error fetching customer data: %s", e)

    # Prepare structured items for template
    structured_items = []
    for idx, item in enumerate(jobcard.items_data or []):
        # Determine device_category from existing data or default to empty
        device_category = item.get("device_category", "")
        
        # Get warranty details
        warranty_details = item.get("warranty_details", {})
        
        structured_items.append({
            "name": item.get("item", ""),
            "device_category": device_category,
            "serial": item.get("serial", ""),
            "config": item.get("config", ""),
            "warranty": item.get("warranty", "no"),
            "take_to_office": item.get("take_to_office", "no"),
            "warranty_details": warranty_details,
            "complaints": [
                {
                    "id": f"{idx}-{c_idx}",
                    "description": complaint.get("description", ""),
                    "notes": complaint.get("notes", ""),
                    "images": jobcard.images.filter(
                        item_index=idx,
                        complaint_index=c_idx
                    )
                }
                for c_idx, complaint in enumerate(item.get("complaints", []))
            ]
        })

    context = {
        "jobcard": jobcard,
        "items": structured_items,
        "items_by_section": items_by_section,
        "suppliers": suppliers,
        "hardware_complaints": hardware_complaints,
        "customer_data": customer_data,
    }
    return render(request, "jobcard_edit.html", context)


@csrf_exempt
def update_status(request, pk):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            status = data.get('status')
            item_index = data.get('item_index', 0)
            
            job = JobCard.objects.get(pk=pk)
            
            # Update status for specific item if item_index is provided
            if item_index is not None and job.items_data:
                if 0 <= item_index < len(job.items_data):
                    # Update the status for the specific item
                    job.items_data[item_index]['status'] = status
                    job.save()
                    return JsonResponse({"success": True, "status": status})
            
            # Fallback: update the main job status
            job.status = status
            job.save()
            return JsonResponse({"success": True, "status": job.get_status_display()})
        except JobCard.DoesNotExist:
            return JsonResponse({"success": False, "error": "Job not found"}, status=404)
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=400)
    return JsonResponse({"success": False, "error": "Invalid request"}, status=400)


# ------------------------------
# Item Master Views
# ------------------------------

def item_master(request):
    items = Item.objects.all().order_by("name")
    context = {
        "items": items,
        "page_title": "Item Master",
        "total_items": items.count(),
    }
    return render(request, "item_master.html", context)


def add_item(request):
    if request.method == "POST":
        name = request.POST.get("name", "").strip().upper()  # force uppercase
        if not name:
            messages.error(request, "Item name cannot be empty.")
            return redirect("app5:add_item")

        # âœ… Check only letters/numbers allowed
        import re
        if not re.match(r'^[A-Z0-9 ]+$', name):
            messages.error(request, "Item name must contain only CAPITAL letters and numbers.")
            return redirect("app5:add_item")

        # âœ… Prevent duplicate
        if Item.objects.filter(name=name).exists():
            messages.error(request, f'Item "{name}" already exists!')
            return redirect("app5:add_item")

        Item.objects.create(name=name)
        messages.success(request, f'Item "{name}" added successfully!')
        return redirect("app5:item_master")

    return render(request, "add_item.html")
def edit_item(request, item_id):
    item = get_object_or_404(Item, id=item_id)
    if request.method == "POST":
        name = request.POST.get("name", "").strip().upper()

        if not name:
            messages.error(request, "Item name cannot be empty.")
            return redirect("app5:edit_item", item_id=item.id)

        import re
        if not re.match(r'^[A-Z0-9 ]+$', name):
            messages.error(request, "Item name must contain only CAPITAL letters and numbers.")
            return redirect("app5:edit_item", item_id=item.id)

        # âœ… Check duplicates (exclude current item)
        if Item.objects.filter(name=name).exclude(id=item.id).exists():
            messages.error(request, f'Item "{name}" already exists!')
            return redirect("app5:edit_item", item_id=item.id)

        item.name = name
        item.save()
        messages.success(request, f'Item "{name}" updated successfully!')
        return redirect("app5:item_master")

    return render(request, "add_item.html", {"item": item})



def delete_item(request, item_id):
    item = get_object_or_404(Item, id=item_id)
    item.delete()
    messages.success(request, f'Item "{item.name}" deleted successfully!')
    return redirect("app5:item_master")

@csrf_exempt
def update_jobcard_status(request, pk):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            action = data.get("action")
            completion_details = data.get("completion_details", {})
            item_index = data.get("item_index")

            jobcard = JobCard.objects.get(pk=pk)

            if action == "accepted":
                jobcard.status = "accepted"
                # Also update individual item status if item_index is provided
                if item_index is not None and jobcard.items_data:
                    if 0 <= item_index < len(jobcard.items_data):
                        jobcard.items_data[item_index]['status'] = "accepted"
                        
            elif action == "rejected":
                jobcard.status = "rejected"
                if item_index is not None and jobcard.items_data:
                    if 0 <= item_index < len(jobcard.items_data):
                        jobcard.items_data[item_index]['status'] = "rejected"
                        
            elif action == "completed":
                jobcard.status = "completed"
                if item_index is not None and jobcard.items_data:
                    if 0 <= item_index < len(jobcard.items_data):
                        jobcard.items_data[item_index]['status'] = "completed"
                
                # Save completion details if provided
                if completion_details:
                    if not hasattr(jobcard, 'completion_details') or jobcard.completion_details is None:
                        jobcard.completion_details = {}
                    
                    jobcard.completion_details.update({
                        'work_done': completion_details.get('work_done', ''),
                        'parts_used': completion_details.get('parts_used', ''),
                        'time_spent': completion_details.get('time_spent', '0'),
                        'notes': completion_details.get('notes', ''),
                        'completed_at': timezone.now().isoformat()
                    })
            else:
                return JsonResponse({"success": False, "error": "Invalid action"})

            jobcard.save()
            return JsonResponse({"success": True})
        except JobCard.DoesNotExist:
            return JsonResponse({"success": False, "error": "JobCard not found"})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})
    return JsonResponse({"success": False, "error": "Invalid request"})


from django.shortcuts import render
from .models import JobCard

def jobcard_assign_table(request):
    # Show all jobcards
    jobcards_list = JobCard.objects.all().order_by('-created_at')  # adjust ordering if need
    paginator = Paginator(jobcards_list, 10)  # Show 10 jobcards per page

    page_number = request.GET.get("page")
    jobcards = paginator.get_page(page_number)
    # Get accurate counts for each status
    stats = {
        "total": JobCard.objects.count(),
        "logged": JobCard.objects.filter(status="logged").count(),
        "accepted": JobCard.objects.filter(status="accepted").count(),  # Added this line
        "sent_technician": JobCard.objects.filter(status="sent_technician").count(),
        "pending": JobCard.objects.filter(status="pending").count(),
        "completed": JobCard.objects.filter(status="completed").count(),
        "returned": JobCard.objects.filter(status="returned").count(),
        "rejected": JobCard.objects.filter(status="rejected").count(),
    }
    
    context = {
        "jobcards": jobcards,
        "stats": stats
    }
    return render(request, "jobcard_assign_table.html", context)
 
from django.http import JsonResponse
from django.shortcuts import get_object_or_404

from app1.models import User   # the model that holds your users
import requests
from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404
from .models import JobCard
from app1.models import User

# âœ… Updated WhatsApp API credentials
import os

WHATSAPP_API_SECRET = os.getenv("WA_SECRET")
WHATSAPP_API_ACCOUNT = os.getenv("WA_ACCOUNT")

def send_whatsapp_message(phone_number, message):
    url = f"https://app.dxing.in/api/send/whatsapp?secret={WHATSAPP_API_SECRET}&account={WHATSAPP_API_ACCOUNT}&recipient={phone_number}&type=text&message={message}&priority=1"
    response = requests.get(url)
    if response.status_code == 200:
        print(f"WhatsApp message sent successfully to {phone_number}")
    else:
        print(f"Failed to send WhatsApp message to {phone_number}. Status code: {response.status_code}, Response: {response.text}")



def assign_new_job(request):
    if request.method == 'POST':
        ticket_number = request.POST.get('ticketNumber')
        technician = request.POST.get('technician')
        status = request.POST.get('status', 'sent_technician')
        
        try:
            jobcard = JobCard.objects.get(ticket_no=ticket_number)
            jobcard.technician = technician
            jobcard.status = status  # Update main status
            
            # âœ… SET THE ASSIGNED DATE WHEN ASSIGNING TO TECHNICIAN
            if not jobcard.assigned_date:  # Only set if not already set
                jobcard.assigned_date = timezone.now()
            
            # âœ… UPDATE INDIVIDUAL ITEM STATUSES TO 'sent_technician'
            if jobcard.items_data:
                for item in jobcard.items_data:
                    item['status'] = 'sent_technician'  # Update each item's status
            
            jobcard.save()
            
            # Fetch the technician's phone number from the User model
            try:
                assigned_user = User.objects.get(name=technician)
                if assigned_user.phone_number:
                    # Prepare the WhatsApp message
                    message = f"You have been assigned a new job. Ticket Number: {ticket_number}"
                    send_whatsapp_message(assigned_user.phone_number, message)
            except User.DoesNotExist:
                pass  # Silently fail if user not found
            
            messages.success(request, f"Job {ticket_number} assigned to {technician} successfully!")
            return redirect('app5:jobcard_assign_table')
        except JobCard.DoesNotExist:
            messages.error(request, f"Job card with ticket number {ticket_number} not found")
        except User.DoesNotExist:
            messages.error(request, f"User {technician} not found")
        except Exception as e:
            messages.error(request, f"Error assigning job: {str(e)}")
    
    # GET request - show the form
    jobcards = JobCard.objects.filter(status='logged').order_by("-created_at")
    technicians = User.objects.filter(status='active').order_by('name')
    
    context = {
        "jobcards": jobcards,
        "technicians": technicians,
    }
    return render(request, "jobcard_assign_form.html", context)

def get_customer_by_ticket(request, ticket_no):
    """API endpoint to get customer details by ticket number"""
    try:
        jobcard = get_object_or_404(JobCard, ticket_no=ticket_no)
        return JsonResponse({
            "success": True,
            "customer": jobcard.customer,
            "phone": jobcard.phone,
            "address": jobcard.address
        })
    except JobCard.DoesNotExist:
        return JsonResponse({
            "success": False,
            "error": f"Job card with ticket number {ticket_no} not found"
        })
    except Exception as e:
        return JsonResponse({
            "success": False,
            "error": str(e)
        })
    
    from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages

def jobcard_assign_edit(request, pk):
    jobcard = get_object_or_404(JobCard, pk=pk)
    technicians = User.objects.filter(status='active').order_by('name')

    if request.method == "POST":
        technician = request.POST.get("technician")
        status = request.POST.get("status", "sent_technician")
        
        # Check if technician is being assigned/changed
        if technician and technician != jobcard.technician:
            jobcard.technician = technician
            # âœ… SET/UPDATE THE ASSIGNED DATE WHEN TECHNICIAN CHANGES
            jobcard.assigned_date = timezone.now()
        
        jobcard.status = status
        
        # âœ… UPDATE INDIVIDUAL ITEM STATUSES
        if jobcard.items_data:
            for item in jobcard.items_data:
                item['status'] = status  # Update each item's status
        
        jobcard.save()

        messages.success(request, f"Job {jobcard.ticket_no} updated successfully!")
        return redirect("app5:jobcard_assign_table")

    context = {
        "assign": jobcard,
        "technicians": technicians,
        "jobcards": JobCard.objects.all()
    }
    return render(request, "jobcard_assign_edit.html", context)


# In your views.py
def assign_job_to_technician(request):
    if request.method == 'POST':
        ticket_number = request.POST.get('ticketNumber')
        technician_name = request.POST.get('technician')
        status = request.POST.get('status', 'sent_technician')
        
        try:
            jobcard = JobCard.objects.get(ticket_no=ticket_number)
            
            # Update the job card with technician and status
            jobcard.technician = technician_name
            jobcard.status = status  # This should be 'sent_technician'
            
            # If you have per-item status, update that too
            if hasattr(jobcard, 'items_data'):
                for item in jobcard.items_data:
                    item['status'] = 'sent_technician'
            
            jobcard.save()
            
            messages.success(request, f'Job assigned to {technician_name} successfully!')
            return redirect('app5:jobcard_assign_table')
            
        except JobCard.DoesNotExist:
            messages.error(request, 'Job card not found!')

    
   

# supplier


from django.shortcuts import render, redirect, get_object_or_404
from .models import Supplier

def supplier_master(request):
    suppliers = Supplier.objects.all().order_by('id')  # Add ordering by ID
    return render(request, "supplier_master_table.html", {"suppliers": suppliers})

def supplier_master_add(request):
    if request.method == "POST":
        name = request.POST.get("name")
        place = request.POST.get("place")
        phone = request.POST.get("phone")
        address = request.POST.get("address")

        Supplier.objects.create(
            name=name,
            place=place,
            phone=phone,
            address=address
        )
        return redirect("app5:supplier_master")

    return render(request, "supplier_master_add.html")

def supplier_master_delete(request, pk):
    supplier = get_object_or_404(Supplier, pk=pk)
    supplier.delete()
    return redirect("app5:supplier_master")

def supplier_master_edit(request, pk):
    supplier = get_object_or_404(Supplier, pk=pk)

    if request.method == "POST":
        supplier.name = request.POST.get("name")
        supplier.place = request.POST.get("place")
        supplier.phone = request.POST.get("phone")
        supplier.address = request.POST.get("address")
        supplier.save()
        return redirect("app5:supplier_master")  # back to table

    return render(request, "supplier_master_edit.html", {"supplier": supplier}) 





# views.py
from django.shortcuts import render
from .models import JobCard


    # Get current user's name from session
def job_technician_accept(request):
    current_user_name = "Unknown"
    if request.session.get('custom_user_id'):
        try:
            current_user = User.objects.get(id=request.session['custom_user_id'])
            current_user_name = getattr(current_user, "name", current_user.username if hasattr(current_user, 'username') else str(current_user))
        except User.DoesNotExist:
            pass
    
    # Handle status updates via POST
    if request.method == "POST":
        jobcard_id = request.POST.get('jobcard_id')
        action = request.POST.get('action')
        
        try:
            jobcard = JobCard.objects.get(pk=jobcard_id, technician=current_user_name)
            
            if action == "accept":
                jobcard.status = "accepted"
                if jobcard.items_data:
                    for item in jobcard.items_data:
                        item['status'] = "accepted"
                messages.success(request, f"Job {jobcard.ticket_no} accepted successfully!")
                
            elif action == "reject":
                jobcard.status = "rejected"
                if jobcard.items_data:
                    for item in jobcard.items_data:
                        item['status'] = "rejected"
                messages.success(request, f"Job {jobcard.ticket_no} rejected!")
                
            elif action == "complete":
                jobcard.status = "completed"
                if jobcard.items_data:
                    for item in jobcard.items_data:
                        item['status'] = "completed"
                messages.success(request, f"Job {jobcard.ticket_no} marked as completed!")
            
            jobcard.save()
            return redirect('app5:job_technician_accept')
            
        except JobCard.DoesNotExist:
            messages.error(request, "Job card not found or you are not assigned to this job")
    
    # Get jobcards assigned to current technician
    processed_jobcards = JobCard.objects.filter(
        technician=current_user_name,
        status__in=["sent_technician", "accepted", "rejected", "completed"]
    )

    # Count by statuses
    accepted_count = processed_jobcards.filter(status="accepted").count()
    pending_count = processed_jobcards.filter(status="sent_technician").count()
    rejected_count = processed_jobcards.filter(status="rejected").count()
    completed_count = processed_jobcards.filter(status="completed").count()
    total_count = processed_jobcards.count()

    context = {
        "processed_jobcards": processed_jobcards,
        "accepted_count": accepted_count,
        "pending_count": pending_count,
        "rejected_count": rejected_count,
        "completed_count": completed_count,
        "total_count": total_count,
        "current_user_name": current_user_name,
    }
    return render(request, "job_technician_accept.html", context)

from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from .models import JobCard  # Make sure to import your JobCard model

def api_jobcard_detail(request, pk):
    """
    API endpoint to get job card details
    """
    jobcard = get_object_or_404(JobCard, pk=pk)
    
    # Return JSON response with job card data
    data = {
        'id': jobcard.id,
        'title': jobcard.title,
        'description': jobcard.description,
        # Add other fields as needed
    }
    return JsonResponse(data)

@csrf_exempt
def update_jobcard_status(request, pk):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            action = data.get("action")
            completion_details = data.get("completion_details", {})
            item_index = data.get("item_index")

            jobcard = JobCard.objects.get(pk=pk)

            # Map actions to status values
            status_mapping = {
                "accepted": "accepted",  # This maps to "In Technician Hand" in display
                "rejected": "rejected",
                "completed": "completed"
            }

            if action in status_mapping:
                new_status = status_mapping[action]
                jobcard.status = new_status
                
                # Update individual item status if item_index is provided
                if item_index is not None and jobcard.items_data:
                    if 0 <= item_index < len(jobcard.items_data):
                        jobcard.items_data[item_index]['status'] = new_status
                
                # Update ALL items' status to maintain consistency
                elif jobcard.items_data:
                    for item in jobcard.items_data:
                        item['status'] = new_status
                
                # Handle completion details for completed status
                if action == "completed" and completion_details:
                    if not hasattr(jobcard, 'completion_details') or jobcard.completion_details is None:
                        jobcard.completion_details = {}
                    
                    jobcard.completion_details.update({
                        'work_done': completion_details.get('work_done', ''),
                        'parts_used': completion_details.get('parts_used', ''),
                        'time_spent': completion_details.get('time_spent', '0'),
                        'notes': completion_details.get('notes', ''),
                        'completed_at': timezone.now().isoformat()
                    })
                
                jobcard.save()
                return JsonResponse({
                    "success": True, 
                    "status": new_status,
                    "display_status": get_status_display(new_status)
                })
            else:
                return JsonResponse({"success": False, "error": "Invalid action"})

        except JobCard.DoesNotExist:
            return JsonResponse({"success": False, "error": "JobCard not found"})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})
    
    return JsonResponse({"success": False, "error": "Invalid request"})


def get_status_display(status):
    """Helper function to get consistent status display across the application"""
    status_display_map = {
        'logged': 'Logged',
        'sent_technician': 'Sent To Technician',
        'accepted': 'In Technician Hand',
        'completed': 'Completed',
        'returned': 'Returned',
        'rejected': 'Rejected'
    }
    return status_display_map.get(status, status.title())


@csrf_exempt
def update_standby_issued(request, pk):
    """API endpoint to update standby issued status"""
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            standby_issued = data.get("standby_issued", False)
            
            jobcard = JobCard.objects.get(pk=pk)
            jobcard.standby_issued = standby_issued
            jobcard.save()
            
            return JsonResponse({
                "success": True, 
                "standby_issued": jobcard.standby_issued
            })
            
        except JobCard.DoesNotExist:
            return JsonResponse({"success": False, "error": "JobCard not found"})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})
    
    return JsonResponse({"success": False, "error": "Invalid request"})



# views.py - Add these views

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from .models import JobCard, StandbyIssuance        # âœ… from app5
from app2.models import StandbyItem, StandbyImage
 # âœ… from app2
from django.utils import timezone
from django.db import models
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
import json
from .models import JobCard, JobCardImage, Item, StandbyIssuance          # âœ… only from app5
from app2.models import StandbyItem, StandbyImage
 # âœ… correct app for StandbyItem
from app1.models import User

def standby_issue_form(request, jobcard_id):
    """Show the standby issue form for a specific job card"""
    jobcard = get_object_or_404(JobCard, id=jobcard_id)
    
    # Check if the current user is assigned to this job card
    current_user_name = "Unknown"
    if request.session.get('custom_user_id'):
        try:
            current_user = User.objects.get(id=request.session['custom_user_id'])
            current_user_name = getattr(current_user, "name", current_user.username if hasattr(current_user, 'username') else str(current_user))
        except User.DoesNotExist:
            pass
    
    if jobcard.technician != current_user_name:
        messages.error(request, "You are not assigned to this job card.")
        return redirect('app5:job_technician_accept')
    
    # âœ… FIXED: Get only "in_stock" standby items with only ORIGINAL images
    available_items = StandbyItem.objects.filter(
        status='in_stock', 
        stock__gt=0
    ).prefetch_related(
        models.Prefetch(
            'images',
            queryset=StandbyImage.objects.filter(
                models.Q(image_type='original') | models.Q(image_type__isnull=True)
            )
        )
    ).order_by('name')
    
    context = {
        'jobcard': jobcard,
        'available_items': available_items,
        'current_user_name': current_user_name,
    }
    return render(request, 'standby_item_issued.html', context)

@require_POST
@require_POST
def standby_issue_item(request, jobcard_id):
    """Handle the standby item issuance for a job card"""
    jobcard = get_object_or_404(JobCard, id=jobcard_id)
    standby_item_id = request.POST.get('item_id')
    
    try:
        # Get the current user
        current_user = None
        if request.session.get('custom_user_id'):
            try:
                current_user = User.objects.get(id=request.session['custom_user_id'])
            except User.DoesNotExist:
                pass
        
        # Get the standby item
        standby_item = StandbyItem.objects.get(id=standby_item_id)
        
        # Validate stock availability
        if standby_item.stock < 1:
            messages.error(request, f"Item '{standby_item.name}' is out of stock")
            return redirect('app5:standby_issue_form', jobcard_id=jobcard_id)
        
        # Create the standby issuance record
        issuance = StandbyIssuance.objects.create(
            standby_item=standby_item,
            job_card=jobcard,
            issued_to=jobcard.customer,
            issued_by=current_user,
            expected_return_date=timezone.now() + timezone.timedelta(days=7),
            status='issued',
            issued_date=timezone.now()
        )
        
        # âœ… UPDATE STANDBY ITEM WITH CUSTOMER DETAILS
        standby_item.stock -= 1
        standby_item.status = 'with_customer'
        
        # Store customer information in the standby item
        standby_item.customer_name = jobcard.customer
        standby_item.customer_place = jobcard.address  # Using address as place
        standby_item.customer_phone = jobcard.phone
        standby_item.issued_date = timezone.now()
        
        standby_item.save()
        
        # Update job card standby issued status
        jobcard.standby_issued = True
        jobcard.save()
        
        messages.success(request, f'Standby item "{standby_item.name}" issued successfully to {jobcard.customer}!')
        return redirect('app5:job_technician_accept')
        
    except StandbyItem.DoesNotExist:
        messages.error(request, "Selected standby item not found.")
    except Exception as e:
        messages.error(request, f"Error issuing standby item: {str(e)}")
    
    return redirect('app5:standby_issue_form', jobcard_id=jobcard_id)

from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from .models import JobCard, StandbyIssuance

@csrf_exempt
def standby_return_item(request, jobcard_id):
    jobcard = get_object_or_404(JobCard, id=jobcard_id)
    
    # Use 'job_card' instead of 'jobcard' - note the underscore
    active_issuances = StandbyIssuance.objects.filter(job_card=jobcard, status='issued')
    
    if request.method == 'POST':
        # Process the return form
        return_date = request.POST.get('return_date')
        condition_notes = request.POST.get('condition_notes')
        additional_notes = request.POST.get('additional_notes')
        
        # Update all active issuances
        for issuance in active_issuances:
            issuance.actual_return_date = return_date
            issuance.status = 'returned'
            if condition_notes:
                issuance.condition_notes = condition_notes
            if additional_notes:
                issuance.additional_notes = additional_notes
            issuance.save()
        
        # Update job card standby status
        jobcard.standby_issued = False
        jobcard.save()
        
        return redirect('app5:standby_issuance_details', jobcard_id=jobcard.id)
    
    context = {
        'jobcard': jobcard,
        'active_issuances': active_issuances,
        'today': timezone.now().date(),
    }
    return render(request, 'return_standby_item.html', context)

# app5/views.py - Replace view_standby_issuance_details with this fixed version

def view_standby_issuance_details(request, jobcard_id):
    """View to display standby item issuance details for a specific job card"""
    jobcard = get_object_or_404(JobCard, id=jobcard_id)
    
    # Get standby issuance records for this job card
    standby_issuances = StandbyIssuance.objects.filter(job_card=jobcard)\
        .select_related('standby_item')\
        .prefetch_related('standby_item__images')\
        .order_by('-issued_date')
    
    # Process each issuance to include return details
    processed_issuances = []
    for issuance in standby_issuances:
        # âœ… Get return condition images - FIXED query
        return_images = []
        
        if issuance.status == 'returned':
            # Get images that are linked to return records OR have return_condition type
            return_images = issuance.standby_item.images.filter(
                models.Q(image_type='return_condition') |
                models.Q(standby_return__isnull=False)
            ).distinct().order_by('-uploaded_at')
            
            # Also check for images uploaded around the return date
            if not return_images.exists() and issuance.actual_return_date:
                # Look for images uploaded on or after the return date
                potential_return_images = issuance.standby_item.images.filter(
                    uploaded_at__date__gte=issuance.actual_return_date
                ).order_by('-uploaded_at')
                return_images = potential_return_images
        
        # Attach return details to issuance
        issuance.return_images = list(return_images)
        issuance.return_images_count = len(issuance.return_images)
        issuance.has_return_details = issuance.status == 'returned'
        issuance.effective_return_date = issuance.actual_return_date
        issuance.return_condition_notes = issuance.condition_on_return or ""
        
        processed_issuances.append(issuance)
        
        logger.info(f"Issuance {issuance.id}: status={issuance.status}, "
                   f"return_images_count={issuance.return_images_count}, "
                   f"return_date={issuance.actual_return_date}")
    
    # Also check for direct returns (items returned via return_standby_items)
    direct_return_details = []
    try:
        from app2.models import StandbyReturn
        
        # Get StandbyReturn records that might be related to this job card
        standby_returns = StandbyReturn.objects.filter(
            models.Q(customer_name_at_return__icontains=jobcard.customer) |
            models.Q(customer_phone_at_return__icontains=jobcard.phone)
        ).select_related('item').prefetch_related('return_images')
        
        for standby_return in standby_returns:
            # Get return images linked to this specific return
            return_imgs = standby_return.return_images.all()
            
            direct_return_details.append({
                'item_name': standby_return.item.name,
                'serial_number': standby_return.item.serial_number,
                'return_date': standby_return.return_date,
                'return_notes': standby_return.return_notes or '',
                'return_images': list(return_imgs),
                'stock_after_return': standby_return.stock_on_return,
                'is_direct_return': True,
                'customer_at_return': standby_return.customer_name_at_return,
            })
            
            logger.info(f"Direct return found: {standby_return.item.name}, "
                       f"images={return_imgs.count()}, date={standby_return.return_date}")
                
    except Exception as e:
        logger.error(f"Error processing direct return details: {e}")
    
    context = {
        'jobcard': jobcard,
        'standby_issuances': processed_issuances,
        'direct_return_details': direct_return_details,
    }
    return render(request, 'standby_issuance_details.html', context)

def extract_return_details(standby_item):
    """Extract return details from standby item for direct returns"""
    if not standby_item.notes:
        return None
    
    # Look for return section in notes using more flexible pattern
    import re
    return_pattern = r'--- RETURNED ON (.+?) ---\s*(.*?)(?=---|$)'
    matches = re.findall(return_pattern, standby_item.notes, re.DOTALL)
    
    if not matches:
        return None
    
    # Get the most recent return
    return_date_str, return_notes = matches[-1]
    
    # Get return condition images
    return_images = standby_item.images.filter(image_type='return_condition')
    
    # Try to parse return date
    from datetime import datetime
    return_date = None
    try:
        return_date = datetime.strptime(return_date_str.strip(), '%d-%m-%Y').date()
    except:
        # If parsing fails, use the item's update date
        return_date = standby_item.updated_at.date()
    
    return {
        'item_name': standby_item.name,
        'serial_number': standby_item.serial_number,
        'return_date': return_date,
        'return_notes': return_notes.strip(),
        'return_images': return_images,
        'stock_after_return': standby_item.stock,
        'is_direct_return': True,
    }

def extract_return_details(standby_item):
    """Extract return details from standby item notes and images"""
    if not standby_item.notes:
        return None
    
    # Look for return section in notes using more flexible pattern
    import re
    return_pattern = r'--- RETURNED ON (.+?) ---\s*(.*?)(?=---|$)'
    matches = re.findall(return_pattern, standby_item.notes, re.DOTALL | re.IGNORECASE)
    
    if not matches:
        return None
    
    # Get the most recent return
    return_date_str, return_notes = matches[-1]
    
    # Get return condition images
    return_images = standby_item.images.filter(image_type='return_condition')
    
    # If no specific return images, get all images as fallback
    if not return_images:
        return_images = standby_item.images.all()
    
    # Try to parse return date
    from datetime import datetime
    return_date = None
    try:
        # Try different date formats
        for fmt in ('%d-%m-%Y', '%d/%m/%Y', '%Y-%m-%d', '%d %b %Y'):
            try:
                return_date = datetime.strptime(return_date_str.strip(), fmt).date()
                break
            except ValueError:
                continue
    except:
        # If parsing fails, use the item's update date
        return_date = standby_item.updated_at.date()
    
    return {
        'item_name': standby_item.name,
        'serial_number': standby_item.serial_number,
        'return_date': return_date,
        'return_notes': return_notes.strip(),
        'return_images': return_images,
        'stock_after_return': standby_item.stock,
        'is_direct_return': True,
    }

def get_standby_item_details(request, item_id):
    """API endpoint to get standby item details"""
    try:
        item = get_object_or_404(StandbyItem, id=item_id)
        
        # Get image URLs
        image_urls = [img.image.url for img in item.images.all()]
        
        return JsonResponse({
            'success': True,
            'item': {
                'id': item.id,
                'name': item.name,
                'serial_number': item.serial_number,
                'stock': item.stock,
                'status': item.status,
                'notes': item.notes,
                'images': image_urls,
                'created_at': item.created_at.isoformat() if item.created_at else None,
            }
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

@csrf_exempt
def update_standby_issued_status(request, jobcard_id):
    """API endpoint to update standby issued status"""
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            standby_issued = data.get("standby_issued", False)
            
            jobcard = JobCard.objects.get(id=jobcard_id)
            jobcard.standby_issued = standby_issued
            jobcard.save()
            
            return JsonResponse({
                "success": True, 
                "standby_issued": jobcard.standby_issued
            })
            
        except JobCard.DoesNotExist:
            return JsonResponse({
                "success": False, 
                "error": "JobCard not found"
            })
        except Exception as e:
            return JsonResponse({
                "success": False, 
                "error": str(e)
            })
    
    return JsonResponse({
        "success": False, 
        "error": "Invalid request"
    })



# Add this to app5/views.py (at the end)

@csrf_exempt
def standby_issuance_return(request, jobcard_id):
    """Handle returning standby item to stock with images, notes, and date"""
    item = get_object_or_404(StandbyItem, id=item_id)
    
    # Check if item is actually with customer
    if item.status != 'with_customer':
        messages.error(request, f'Item "{item.name}" is not currently with a customer.')
        return redirect('item_list')
    
    if request.method == 'POST':
        # âœ… Get form data
        return_date_str = request.POST.get('return_date')
        return_notes = request.POST.get('return_notes', '').strip()
        stock = request.POST.get('stock', item.stock)
        return_images = request.FILES.getlist('return_images')
        
        # Parse return date
        try:
            from django.utils.dateparse import parse_date
            return_date = parse_date(return_date_str)
            if not return_date:
                return_date = timezone.now().date()
        except:
            return_date = timezone.now().date()
        
        logger.info(f"Processing return for item {item.id} - {item.name}")
        logger.info(f"Return date: {return_date}, Notes: {return_notes[:50] if return_notes else 'None'}")
        
        try:
            # âœ… Create StandbyReturn record FIRST
            standby_return = StandbyReturn.objects.create(
                item=item,
                return_date=return_date,
                return_notes=return_notes,
                returned_by=request.user if request.user.is_authenticated else None,
                stock_on_return=stock,
                # Store original customer info at time of return
                customer_name_at_return=item.customer_name,
                customer_place_at_return=item.customer_place,
                customer_phone_at_return=item.customer_phone,
                issued_date_at_return=item.issued_date
            )
            
            logger.info(f"Created StandbyReturn record: {standby_return.id}")
            
            # âœ… Save return images linked to the StandbyReturn record
            images_saved = 0
            for image in return_images:
                try:
                    StandbyImage.objects.create(
                        item=item, 
                        image=image,
                        image_type='return_condition',
                        standby_return=standby_return  # Link to the return record
                    )
                    images_saved += 1
                except Exception as e:
                    logger.error(f"Error saving return image: {e}")
            
            logger.info(f"Saved {images_saved} return condition images linked to return record {standby_return.id}")
            
            # âœ… Update item status and details AFTER creating return record
            item.status = 'in_stock'
            item.stock = stock
            
            # Add return notes to item's notes with clear separation
            if return_notes:
                current_notes = item.notes or ''
                return_info = f"\n\n--- RETURNED ON {return_date.strftime('%d-%m-%Y')} ---\n{return_notes}"
                item.notes = current_notes + return_info
            
            # Clear customer information
            item.customer_name = None
            item.customer_place = None
            item.customer_phone = None
            item.issued_date = None
            
            item.save()
            logger.info(f"Item {item.id} updated - status: {item.status}, stock: {item.stock}")
            
            # âœ… Try to find and update related issuance (if exists)
            try:
                from .models import StandbyIssuance  # Import if exists in your models
                related_issuance = StandbyIssuance.objects.filter(
                    standby_item=item,
                    issued_to=item.customer_name,  # Use the original customer name before clearing
                    status='issued'
                ).first()
                
                if related_issuance:
                    # Set return date
                    related_issuance.actual_return_date = return_date
                    related_issuance.status = 'returned'
                    
                    # Store return notes
                    if return_notes:
                        related_issuance.condition_on_return = return_notes
                    
                    # Append to general notes for backup
                    existing_notes = related_issuance.notes or ''
                    timestamp = timezone.now().strftime('%d-%m-%Y %H:%M')
                    additional_info = f"\n\n--- RETURNED VIA DIRECT RETURN ON {timestamp} ---"
                    additional_info += f"\nReturn Date: {return_date.strftime('%d-%m-%Y')}"
                    additional_info += f"\nCustomer: {standby_return.customer_name_at_return}"
                    if return_notes:
                        additional_info += f"\nCondition Notes: {return_notes}"
                    if images_saved > 0:
                        additional_info += f"\n{images_saved} return condition image(s) uploaded"
                    
                    related_issuance.notes = (existing_notes + additional_info).strip()
                    related_issuance.save()
                    
                    logger.info(f"Updated issuance {related_issuance.id} with return details")
                    
                    # Update job card standby status if exists
                    if hasattr(related_issuance, 'job_card') and related_issuance.job_card:
                        related_issuance.job_card.standby_issued = False
                        related_issuance.job_card.save()
                        logger.info(f"Updated job card {related_issuance.job_card.id} - standby_issued: False")
                        
            except Exception as e:
                logger.warning(f"No related issuance found or error updating issuance: {e}")
            
            # Success message
            success_msg = f'Item "{item.name}" has been returned to stock successfully!'
            if images_saved > 0:
                success_msg += f' {images_saved} image(s) uploaded.'
            messages.success(request, success_msg)
            
            return redirect('item_list')
            
        except Exception as e:
            logger.error(f"Error creating standby return record: {e}")
            messages.error(request, f"Error processing return: {str(e)}")
            return redirect('standby_return_item', item_id=item_id)
    
    # For GET request, show the return form with current customer info
    context = {
        'item': item,
        'today': date.today(),
    }
    return render(request, 'return_standby_items.html', context)


# Add these warranty views to your existing views.py

# views.py - Complete with proper imports
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.core.paginator import Paginator
from django.utils import timezone
from django.db import models
from django.db.models import Q

# Import your models
from .models import JobCard, JobCardImage, Item, Supplier
from .models import WarrantyTicket, WarrantyItemLog, StandbyIssuance

# Import from other apps
from app1.models import User
from app2.models import StandbyItem, StandbyImage

import os
import json
import logging
import requests
from collections import defaultdict
from datetime import datetime

logger = logging.getLogger(__name__)

# Your existing job card views here...
# ... [all your existing job card views] ...

# Warranty Management Views
from purchase_order.models import Supplier as POSupplier

def warranty_item_management(request):
    """
    Display warranty item management page with supplier selection
    """
    try:
        # Try to use purchase_order suppliers first (preferred)
        from purchase_order.models import Supplier as POSupplier
        suppliers = POSupplier.objects.select_related('department').filter(is_active=True).order_by('-id')
        supplier_source = 'purchase_order'
    except ImportError:
        # Fallback to app5 suppliers
        from .models import Supplier
        
        # âœ… CHECK if is_active field exists
        field_names = [f.name for f in Supplier._meta.get_fields()]
        
        if 'is_active' in field_names:
            # Field exists, use it
            suppliers = Supplier.objects.filter(is_active=True).order_by('-id')
        else:
            # Field doesn't exist, get all suppliers
            suppliers = Supplier.objects.all().order_by('-id')
            
        supplier_source = 'app5'
    except Exception as e:
        suppliers = []
        supplier_source = 'none'
        logger.error(f"Error getting suppliers: {e}")

    # Get pre-selected values from URL parameters
    ticket_no = request.GET.get('ticket_no', '')
    supplier_id = request.GET.get('supplier_id', '')
    item_name = request.GET.get('item_name', '')
    serial_no = request.GET.get('serial_no', '')
    
    # Try to find supplier by ID or name
    pre_selected_supplier = None
    if supplier_id:
        try:
            # First try by ID
            if supplier_source == 'purchase_order':
                pre_selected_supplier = POSupplier.objects.filter(id=supplier_id, is_active=True).first()
            else:
                # For app5 suppliers, check if is_active exists
                field_names = [f.name for f in Supplier._meta.get_fields()]
                
                if 'is_active' in field_names:
                    pre_selected_supplier = Supplier.objects.filter(id=supplier_id, is_active=True).first()
                else:
                    pre_selected_supplier = Supplier.objects.filter(id=supplier_id).first()
            
            if not pre_selected_supplier:
                # Try by name
                if supplier_source == 'purchase_order':
                    pre_selected_supplier = POSupplier.objects.filter(name__icontains=supplier_id, is_active=True).first()
                else:
                    if 'is_active' in field_names:
                        pre_selected_supplier = Supplier.objects.filter(name__icontains=supplier_id, is_active=True).first()
                    else:
                        pre_selected_supplier = Supplier.objects.filter(name__icontains=supplier_id).first()
        except Exception as e:
            logger.error(f"Error finding supplier: {e}")

    context = {
        'suppliers': suppliers,
        'supplier_source': supplier_source,
        'pre_selected_ticket': ticket_no,
        'pre_selected_supplier': pre_selected_supplier,
        'pre_selected_item': item_name,
        'pre_selected_serial': serial_no,
    }
    return render(request, 'warranty_item.html', context)

# Alias for backwards compatibility
warranty_item = warranty_item_management

# Alias for backwards compatibility
warranty_item = warranty_item_management

@require_http_methods(["GET"])
def api_all_warranty_tickets(request):
    """
    API endpoint to get all job cards with warranty items
    Returns tickets that have at least one warranty item with status 'yes' AND not sent to supplier
    """
    try:
        # Get all job cards
        jobcards = JobCard.objects.all()
        
        tickets_data = []
        for jobcard in jobcards:
            # Check if jobcard has warranty items with warranty='yes' AND not processed/sent to supplier
            pending_warranty_items = []
            if hasattr(jobcard, 'items_data') and jobcard.items_data:
                pending_warranty_items = [
                    item for item in jobcard.items_data 
                    if (item.get('warranty') == 'yes' and 
                        not item.get('warranty_status') in ['sent_to_supplier', 'returned_from_supplier'])
                ]
            
            # Only include tickets that have pending warranty items (not sent to supplier)
            if pending_warranty_items:
                tickets_data.append({
                    'ticket_no': jobcard.ticket_no,
                    'customer': jobcard.customer,
                    'phone': jobcard.phone,
                    'items_count': len(pending_warranty_items),
                    'created_at': jobcard.created_at.isoformat(),
                })
        
        return JsonResponse({
            'success': True,
            'tickets': tickets_data
        })
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@require_http_methods(["GET"])
def api_ticket_details(request):
    """
    API endpoint to get detailed information about a specific ticket
    Including customer info and all warranty items
    """
    ticket_no = request.GET.get('ticket_no')
    
    if not ticket_no:
        return JsonResponse({
            'success': False,
            'error': 'Ticket number is required'
        }, status=400)
    
    try:
        jobcard = get_object_or_404(JobCard, ticket_no=ticket_no)
        
        # Get items data from the jobcard's items_data property
        items_data = jobcard.items_data if hasattr(jobcard, 'items_data') else []
        
        # âœ… FILTER: Only include items with warranty='yes' AND not sent to supplier
        filtered_items = []
        for item in items_data:
            warranty_status = item.get('warranty_status')
            warranty_value = item.get('warranty')
            
            # Include only items with warranty='yes' AND not sent to supplier
            if (warranty_value == 'yes' and 
                warranty_status != 'sent_to_supplier' and 
                warranty_status != 'returned_from_supplier'):
                filtered_items.append(item)
        
        jobcard_data = {
            'ticket_no': jobcard.ticket_no,
            'customer': jobcard.customer,
            'phone': jobcard.phone,
            'address': jobcard.address,
            'status': getattr(jobcard, 'status', 'pending'),
            'created_at': jobcard.created_at.isoformat(),
            'items_data': filtered_items,  # âœ… Use filtered items
        }
        
        return JsonResponse({
            'success': True,
            'jobcard': jobcard_data
        })
    
    except JobCard.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Ticket not found'
        }, status=404)
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])

# Complete process_warranty_tickets function for app5/views.py
# This version works regardless of migration state

@csrf_exempt
@require_http_methods(["POST"])
def process_warranty_tickets(request):
    """
    Process multiple warranty items submission
    âœ… USES ONLY purchase_order.Supplier
    """
    try:
        supplier_id = request.POST.get('supplier')
        ticket_no = request.POST.get('ticket_no')
        selected_items = request.POST.getlist('selected_items')
        item_serials = request.POST.getlist('item_serials[]')
        
        logger.info(f"Processing warranty tickets - Supplier ID: {supplier_id}, Ticket: {ticket_no}")
        
        # Validate required fields
        if not all([supplier_id, ticket_no]) or not selected_items:
            error_msg = 'Supplier, ticket number, and at least one item must be selected'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': error_msg})
            messages.error(request, error_msg)
            return redirect('app5:warranty_item')
        
        # Get jobcard
        try:
            jobcard = JobCard.objects.get(ticket_no=ticket_no)
            logger.info(f"Found jobcard: {jobcard.ticket_no}")
        except JobCard.DoesNotExist:
            error_msg = f'Job card {ticket_no} not found'
            logger.error(error_msg)
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': error_msg})
            messages.error(request, error_msg)
            return redirect('app5:warranty_item')
        
        # âœ… GET SUPPLIER FROM PURCHASE_ORDER MODEL
        supplier = None
        try:
            from purchase_order.models import Supplier as POSupplier
            
            logger.info(f"Looking for POSupplier with ID: {supplier_id}")
            
            # Try with is_active=True first
            supplier = POSupplier.objects.filter(id=supplier_id, is_active=True).first()
            
            if not supplier:
                # Try without is_active filter
                logger.warning(f"Supplier {supplier_id} not found with is_active=True, trying without filter")
                supplier = POSupplier.objects.filter(id=supplier_id).first()
            
            if supplier:
                logger.info(f"âœ… Found supplier: ID={supplier.id}, Name={supplier.name}, Active={supplier.is_active}")
            else:
                # List all available suppliers for debugging
                all_suppliers = POSupplier.objects.all().values('id', 'name', 'is_active')
                logger.error(f"âŒ Supplier {supplier_id} not found. Available suppliers: {list(all_suppliers)}")
                
                # âœ… Fixed nested f-string issue here
                supplier_list = ", ".join([f"ID {s['id']}: {s['name']}" for s in all_suppliers[:5]])
                error_msg = f"Supplier with ID {supplier_id} not found. Available suppliers: {supplier_list}"
                
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'error': error_msg})
                messages.error(request, error_msg)
                return redirect('app5:warranty_item')
                
        except ImportError:
            error_msg = 'purchase_order app not available. Cannot process warranty tickets.'
            logger.error(error_msg)
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': error_msg})
            messages.error(request, error_msg)
            return redirect('app5:warranty_item')
        except Exception as e:
            error_msg = f'Error finding supplier: {str(e)}'
            logger.error(f"Supplier lookup error: {e}", exc_info=True)
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': error_msg})
            messages.error(request, error_msg)
            return redirect('app5:warranty_item')
        
        created_tickets = []
        processed_items = []
        duplicate_items = []
        
        # Process each selected item
        for idx, selected_item in enumerate(selected_items):
            logger.info(f"Processing item {idx + 1}/{len(selected_items)}: {selected_item}")
            
            selected_item_data = None
            item_serial = item_serials[idx] if idx < len(item_serials) else ''
            item_index = None
            
            if hasattr(jobcard, 'items_data') and jobcard.items_data:
                for item_idx, item in enumerate(jobcard.items_data):
                    if item.get('item') == selected_item:
                        selected_item_data = item
                        item_serial = item.get('serial', '') or item_serial
                        item_index = item_idx
                        break
            
            if not selected_item_data:
                logger.warning(f"Item {selected_item} not found in jobcard items_data")
                continue
            
            # Check warranty
            if selected_item_data.get('warranty') != 'yes':
                logger.warning(f"Item {selected_item} does not have warranty='yes'")
                continue
            
            # DUPLICATE DETECTION
            existing_tickets = WarrantyTicket.objects.filter(
                selected_item=selected_item,
                status__in=['pending', 'submitted', 'approved']
            )
            
            if item_serial:
                existing_tickets = existing_tickets.filter(
                    models.Q(item_serial=item_serial) | models.Q(selected_item=selected_item)
                )
            
            if existing_tickets.exists():
                duplicate_tickets = list(existing_tickets.values_list('ticket_no', flat=True))
                logger.info(f"Duplicate found for {selected_item}: {duplicate_tickets}")
                duplicate_items.append({
                    'item': selected_item,
                    'serial': item_serial,
                    'existing_tickets': duplicate_tickets
                })
                continue
            
            # Generate warranty ticket number
            last_warranty = WarrantyTicket.objects.order_by('-id').first()
            if last_warranty:
                try:
                    last_num = int(last_warranty.ticket_no.split('-')[-1])
                    new_ticket_no = f"WT-{last_num + 1:06d}"
                except Exception:
                    new_ticket_no = f"WT-{WarrantyTicket.objects.count() + 1:06d}"
            else:
                new_ticket_no = "WT-000001"
            
            logger.info(f"Creating warranty ticket: {new_ticket_no}")
            
            # Update warranty status in jobcard
            if item_index is not None and jobcard.items_data:
                jobcard.items_data[item_index]['warranty_status'] = 'sent_to_supplier'
                jobcard.items_data[item_index]['warranty_sent_date'] = timezone.now().isoformat()
                jobcard.items_data[item_index]['warranty_supplier'] = supplier.name
                jobcard.items_data[item_index]['warranty_ticket_no'] = new_ticket_no
                jobcard.items_data[item_index]['warranty_processed'] = True
            
            # âœ… Create warranty ticket
            try:
                warranty_ticket = WarrantyTicket.objects.create(
                    ticket_no=new_ticket_no,
                    jobcard=jobcard,
                    supplier=supplier,
                    selected_item=selected_item,
                    item_serial=item_serial,
                    status='submitted',
                    issue_description=f"Warranty claim for {selected_item}",
                    submitted_at=timezone.now()
                )
                logger.info(f"âœ… Created warranty ticket: {new_ticket_no}")
            except Exception as e:
                logger.error(f"Error creating warranty ticket: {e}", exc_info=True)
                error_msg = f"Error creating warranty ticket for {selected_item}: {str(e)}"
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'error': error_msg})
                messages.error(request, error_msg)
                return redirect('app5:warranty_item')
            
            # Create log entry
            WarrantyItemLog.objects.create(
                warranty_ticket=warranty_ticket,
                action='Created and Sent to Supplier',
                description=f'Warranty ticket created for {selected_item} and sent to {supplier.name}',
                performed_by=request.user.username if request.user.is_authenticated else 'System'
            )
            
            created_tickets.append(new_ticket_no)
            processed_items.append({
                'name': selected_item,
                'ticket_no': new_ticket_no,
                'serial': item_serial
            })
        
        # Save jobcard
        jobcard.save()
        logger.info(f"Jobcard saved with {len(processed_items)} processed items")
        
        # Prepare response
        response_data = {
            'success': True,
            'items_processed': len(processed_items),
            'processed_items': processed_items,
            'supplier': supplier.name,
            'jobcard_ticket': jobcard.ticket_no
        }
        
        if duplicate_items:
            response_data['duplicate_items'] = duplicate_items
            response_data['has_duplicates'] = True
        
        # WhatsApp notification
        if created_tickets:
            try:
                items_list = "\n".join([f"â€¢ {item['name']}" for item in processed_items])
                message_text = (
                    f"ðŸ”§ *Warranty Items Sent to Supplier*\n\n"
                    f"*Job Card:* {jobcard.ticket_no}\n"
                    f"*Supplier:* {supplier.name}\n"
                    f"*Customer:* {jobcard.customer}\n"
                    f"*Items ({len(processed_items)}):*\n{items_list}\n"
                    f"*Warranty Tickets:* {', '.join(created_tickets)}\n"
                    f"*Date:* {timezone.now().strftime('%d-%m-%Y')}"
                )
                
                if duplicate_items:
                    duplicate_list = "\n".join([
                        f"â€¢ {item['item']} (Existing: {', '.join(item['existing_tickets'])})" 
                        for item in duplicate_items
                    ])
                    message_text += f"\n\nâš ï¸ *Duplicates Skipped:*\n{duplicate_list}"
                
                whatsapp_api_base = "https://app.dxing.in/api/send/whatsapp"
                params = {
                    "secret": settings.DXING_SECRET,
                    "account": settings.DXING_ACCOUNT,
                    "type": "text",
                    "priority": 1,
                    "recipient": "9946545535",
                    "message": message_text
                }
                requests.get(whatsapp_api_base, params=params, timeout=5)
            except Exception as e:
                logger.debug(f"WhatsApp notification failed: {e}")
        
        # Return response
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse(response_data)
        
        if duplicate_items:
            duplicate_message = "Some items were skipped due to existing warranty tickets: " + \
                ", ".join([f"{item['item']} (Ticket: {', '.join(item['existing_tickets'])})" 
                           for item in duplicate_items])
            messages.warning(request, duplicate_message)
        
        if processed_items:
            messages.success(
                request, 
                f'âœ… Created {len(created_tickets)} warranty ticket(s) and sent to {supplier.name}'
            )
        
        return redirect('app5:warranty_ticket_list')
    
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        logger.error(f"Error processing warranty items: {error_detail}")
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': str(e)})
        messages.error(request, f'Error processing warranty items: {str(e)}')
        return redirect('app5:warranty_item')


# In views.py, update the warranty_ticket_list function
def warranty_ticket_list(request):
    """
    Display list of all warranty tickets with filtering
    """
    status_filter = request.GET.get('status', '')
    supplier_filter = request.GET.get('supplier', '')
    
    warranty_tickets = WarrantyTicket.objects.select_related(
        'jobcard', 'supplier'
    ).all().order_by('-created_at')
    
    if status_filter:
        warranty_tickets = warranty_tickets.filter(status=status_filter)
    
    if supplier_filter:
        warranty_tickets = warranty_tickets.filter(supplier_id=supplier_filter)
    
    # Calculate status counts
    total_count = warranty_tickets.count()
    pending_count = warranty_tickets.filter(status='pending').count()
    submitted_count = warranty_tickets.filter(status='submitted').count()
    approved_count = warranty_tickets.filter(status='approved').count()
    rejected_count = warranty_tickets.filter(status='rejected').count()
    completed_count = warranty_tickets.filter(status='completed').count()
    
    # âœ… FIXED: Get suppliers with proper error handling
    suppliers = []
    supplier_source = 'none'
    
    try:
        # Try purchase_order suppliers first
        from purchase_order.models import Supplier as POSupplier
        suppliers = POSupplier.objects.filter(is_active=True).order_by('name')
        supplier_source = 'purchase_order'
    except ImportError:
        try:
            # Fallback to app5 suppliers
            from .models import Supplier
            field_names = [f.name for f in Supplier._meta.get_fields()]
            
            if 'is_active' in field_names:
                # Field exists
                suppliers = Supplier.objects.filter(is_active=True).order_by('name')
            else:
                # Field doesn't exist, get all suppliers
                suppliers = Supplier.objects.all().order_by('name')
                
            supplier_source = 'app5'
        except Exception as e:
            logger.error(f"Error getting suppliers: {e}")
            suppliers = []
            supplier_source = 'none'
    
    status_choices = WarrantyTicket.STATUS_CHOICES
    
    context = {
        'warranty_tickets': warranty_tickets,
        'suppliers': suppliers,
        'supplier_source': supplier_source,
        'status_choices': status_choices,
        'current_status': status_filter,
        'current_supplier': supplier_filter,
        'total_count': total_count,
        'pending_count': pending_count,
        'submitted_count': submitted_count,
        'approved_count': approved_count,
        'rejected_count': rejected_count,
        'completed_count': completed_count,
    }
    
    return render(request, 'warranty_ticket_list.html', context)

def warranty_ticket_detail(request, ticket_id):
    """
    Display detailed view of a warranty ticket with logs
    """
    warranty_ticket = get_object_or_404(
        WarrantyTicket.objects.select_related('jobcard', 'supplier'),
        id=ticket_id
    )
    
    logs = warranty_ticket.logs.all().order_by('-created_at')
    
    context = {
        'warranty_ticket': warranty_ticket,
        'logs': logs,
    }
    
    return render(request, 'warranty_ticket_detail.html', context)

@require_http_methods(["POST"])
def update_warranty_item_status(request, ticket_id):
    """
    Update warranty item status when returned from supplier
    """
    try:
        warranty_ticket = get_object_or_404(WarrantyTicket, id=ticket_id)
        new_status = request.POST.get('status')
        resolution_notes = request.POST.get('resolution_notes', '')
        
        if not new_status:
            messages.error(request, 'Status is required')
            return redirect('app5:warranty_ticket_detail', ticket_id=ticket_id)
        
        old_status = warranty_ticket.status
        warranty_ticket.status = new_status
        
        # âœ… UPDATE WARRANTY STATUS IN JOBCARD when status indicates return
        if new_status in ['completed', 'approved', 'returned']:
            warranty_ticket.resolved_at = timezone.now()
            
            jobcard = warranty_ticket.jobcard
            item_name = warranty_ticket.selected_item
            
            if hasattr(jobcard, 'items_data') and jobcard.items_data:
                for idx, item in enumerate(jobcard.items_data):
                    if item.get('item') == item_name:
                        # âœ… CHANGE STATUS FROM "sent_to_supplier" TO "returned_from_supplier"
                        jobcard.items_data[idx]['warranty_status'] = 'returned_from_supplier'
                        jobcard.items_data[idx]['warranty_return_date'] = timezone.now().isoformat()
                        jobcard.items_data[idx]['warranty_resolution'] = resolution_notes
                        jobcard.items_data[idx]['warranty_processed'] = True
                        break
            
            jobcard.save()
        
        warranty_ticket.resolution_notes = resolution_notes
        warranty_ticket.save()
        
        # Create log entry
        WarrantyItemLog.objects.create(
            warranty_ticket=warranty_ticket,
            action=f'Status changed from {old_status} to {new_status}',
            description=resolution_notes or f'Status updated to {new_status}',
            performed_by=request.user.username if request.user.is_authenticated else 'System'
        )
        
        messages.success(request, f'Warranty ticket status updated to {new_status}')
        return redirect('app5:warranty_ticket_detail', ticket_id=ticket_id)
    
    except Exception as e:
        messages.error(request, f'Error updating status: {str(e)}')
        return redirect('app5:warranty_ticket_detail', ticket_id=ticket_id)
    

@require_http_methods(["GET"])
def api_warranty_details(request):
    """
    API endpoint to get warranty details for a specific item
    """
    ticket_no = request.GET.get('ticket_no')
    item_name = request.GET.get('item_name')
    
    if not ticket_no or not item_name:
        return JsonResponse({
            'success': False,
            'error': 'Ticket number and item name are required'
        }, status=400)
    
    try:
        # Get the job card
        jobcard = JobCard.objects.get(ticket_no=ticket_no)
        
        # Find warranty ticket for this specific item
        warranty_ticket = WarrantyTicket.objects.filter(
            jobcard=jobcard,
            selected_item=item_name
        ).select_related('supplier').first()
        
        if not warranty_ticket:
            return JsonResponse({
                'success': False,
                'error': 'No warranty ticket found for this item'
            })
        
        # âœ… NEW: Get return details if exists
        return_details = None
        if hasattr(warranty_ticket, 'return_item'):
            return_item = warranty_ticket.return_item
            return_details = {
                'return_date': return_item.return_date.strftime('%d %b %Y') if return_item.return_date else 'N/A',
                'handled_by': return_item.returned_by.username if return_item.returned_by else 'N/A',
                'notes': return_item.notes or '',
                'images': []
            }
            
            # Get return images
            try:
                return_images = return_item.images.all()
                for img in return_images:
                    return_details['images'].append({
                        'url': img.image.url,
                        'name': os.path.basename(img.image.name)
                    })
            except Exception as e:
                logger.debug(f"Error getting return images: {e}")
        
        # Prepare warranty information
        warranty_info = {
            'id': warranty_ticket.id,
            'ticket_no': warranty_ticket.ticket_no,
            'status': warranty_ticket.status,
            'supplier': warranty_ticket.supplier.name if warranty_ticket.supplier else 'N/A',
            'customer': jobcard.customer,
            'phone': jobcard.phone,
            'submitted_date': warranty_ticket.submitted_at.strftime('%d %b %Y') if warranty_ticket.submitted_at else 'N/A',
            'resolved_date': warranty_ticket.resolved_at.strftime('%d %b %Y') if warranty_ticket.resolved_at else None,
            'issue_description': warranty_ticket.issue_description or '',
            'resolution_notes': warranty_ticket.resolution_notes or '',
            'return_details': return_details  # âœ… Add return details
        }
        
        return JsonResponse({
            'success': True,
            'warranty_info': warranty_info
        })
    
    except JobCard.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Job card not found'
        }, status=404)
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
    
def warranty_ticket_edit(request, ticket_id):
    ticket = get_object_or_404(WarrantyTicket, id=ticket_id)
    suppliers = Supplier.objects.all()

    if request.method == 'POST':
        # Only update the supplier field
        supplier_id = request.POST.get('supplier')
        
        if supplier_id:
            ticket.supplier_id = supplier_id
            ticket.save()
            messages.success(request, f'Warranty ticket {ticket.ticket_no} supplier updated successfully!')
        else:
            messages.error(request, 'Please select a supplier.')
        
        return redirect('app5:warranty_ticket_list')

    return render(request, 'warranty_ticket_edit.html', {
        'ticket': ticket,
        'suppliers': suppliers,
    })
@require_http_methods(["POST"])
def warranty_ticket_delete(request, ticket_id):
    try:
        ticket = WarrantyTicket.objects.get(id=ticket_id)
        ticket_no = ticket.ticket_no
        ticket.delete()
        
        messages.success(request, f'Warranty ticket {ticket_no} deleted successfully!')
        return redirect('app5:warranty_ticket_list')
        
    except WarrantyTicket.DoesNotExist:
        messages.error(request, 'Ticket not found')
        return redirect('app5:warranty_ticket_list')
    except Exception as e:
        messages.error(request, f'Error deleting ticket: {str(e)}')
        return redirect('app5:warranty_ticket_list')
    


from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from .models import WarrantyTicket, ReturnItem
import os
from django.conf import settings

# In views.py, replace the return_warranty_item function with this:

def return_warranty_item(request, ticket_id):
    """
    View for returning a warranty item - FIXED version
    """
    # Get the warranty ticket
    ticket = get_object_or_404(WarrantyTicket, id=ticket_id)
    
    # Check if item is already returned
    if hasattr(ticket, 'return_item'):
        messages.warning(request, f"This item for ticket {ticket.ticket_no} has already been returned.")
        return redirect('app5:warranty_ticket_list')
    
    if request.method == 'POST':
        try:
            return_date = request.POST.get('return_date')
            notes = request.POST.get('notes', '')
            images = request.FILES.getlist('images')
            
            # Validate return date
            if not return_date:
                messages.error(request, "Return date is required.")
                return render(request, 'return_warranty_item.html', {'ticket': ticket})
            
            # âœ… UPDATE WARRANTY STATUS IN JOBCARD ITEMS_DATA
            jobcard = ticket.jobcard
            item_name = ticket.selected_item
            
            if hasattr(jobcard, 'items_data') and jobcard.items_data:
                for idx, item in enumerate(jobcard.items_data):
                    if item.get('item') == item_name:
                        # âœ… CHANGE STATUS FROM "sent_to_supplier" TO "returned_from_supplier"
                        jobcard.items_data[idx]['warranty_status'] = 'returned_from_supplier'
                        jobcard.items_data[idx]['warranty_return_date'] = timezone.now().isoformat()
                        jobcard.items_data[idx]['warranty_resolution'] = notes
                        jobcard.items_data[idx]['warranty_processed'] = True
                        break
                
                # Save the updated jobcard
                jobcard.save()
            
            # Create return item record
            return_item = ReturnItem.objects.create(
                warranty_ticket=ticket,
                return_date=return_date,
                notes=notes,
                returned_by=request.user if request.user.is_authenticated else None
            )
            
            # Handle image uploads - FIXED: Use the correct model
            if images:
                for image in images:
                    # Validate image size (5MB limit)
                    if image.size > 5 * 1024 * 1024:  # 5MB in bytes
                        messages.warning(request, f"Image {image.name} is too large. Maximum size is 5MB.")
                        continue
                    
                    # âœ… FIXED: Use the correct model for return images
                    # If you have a ReturnImage model, use it. Otherwise, we need to create one.
                    try:
                        # Try to import ReturnImage if it exists
                        from .models import ReturnImage
                        ReturnImage.objects.create(
                            return_item=return_item,
                            image=image
                        )
                    except ImportError:
                        # If ReturnImage doesn't exist, save images in a different way
                        # For now, we'll just skip image saving but continue with the return process
                        logger.warning("ReturnImage model not found, skipping image upload")
                        break
            
            # Update ticket status
            ticket.status = 'completed'  # Mark as completed
            ticket.resolved_at = timezone.now()
            ticket.save()
            
            # Create log entry for the return
            WarrantyItemLog.objects.create(
                warranty_ticket=ticket,
                action='Item Returned from Supplier',
                description=f'Item returned from supplier with notes: {notes}',
                performed_by=request.user.username if request.user.is_authenticated else 'System'
            )
            
            messages.success(request, f"Item for warranty ticket {ticket.ticket_no} has been successfully returned and status updated.")
            return redirect('app5:warranty_ticket_list')
            
        except Exception as e:
            messages.error(request, f"Error processing return: {str(e)}")
            return render(request, 'return_warranty_item.html', {'ticket': ticket})
    
    # GET request - show the form
    return render(request, 'return_warranty_item.html', {'ticket': ticket})

def return_item_detail(request, return_id):
    """
    View to see details of a completed return
    """
    return_item = get_object_or_404(ReturnItem, id=return_id)
    return render(request, 'app5/return_item_detail.html', {'return_item': return_item})

def return_item_delete(request, return_id):
    """
    View to delete a return record (admin only)
    """
    if not request.user.is_staff:
        messages.error(request, "You don't have permission to delete return records.")
        return redirect('app5:warranty_ticket_list')
    
    return_item = get_object_or_404(ReturnItem, id=return_id)
    ticket_no = return_item.warranty_ticket.ticket_no
    
    if request.method == 'POST':
        try:
            return_item.delete()
            messages.success(request, f"Return record for ticket {ticket_no} has been deleted.")
        except Exception as e:
            messages.error(request, f"Error deleting return record: {str(e)}")
    
    return redirect('app5:warranty_ticket_list')



# Service Billing Views
# Replace the service_billing_view function in your views.py with this fixed version

def service_billing_view(request):
    """
    Display service billing form and generate invoices
    âœ… FIXED: Amount determines service type (0 = Free, >0 = Payable)
    """
    # Get current user
    current_user_name = "Unknown"
    if request.session.get('custom_user_id'):
        try:
            current_user = User.objects.get(id=request.session['custom_user_id'])
            current_user_name = getattr(current_user, "name", current_user.username if hasattr(current_user, 'username') else str(current_user))
        except User.DoesNotExist:
            pass
    
    # Handle invoice generation
    if request.method == 'POST':
        try:
            # Get form data
            ticket_no = request.POST.get('ticketNo')
            date = request.POST.get('date')
            customer_name = request.POST.get('customerName')
            customer_contact = request.POST.get('customerContact')
            customer_address = request.POST.get('customerAddress')
            payment_status = request.POST.get('paymentStatus')
            notes = request.POST.get('notes', '')
            
            # Get service items data
            item_names = request.POST.getlist('itemName[]')
            item_serials = request.POST.getlist('itemSerial[]')
            service_descriptions = request.POST.getlist('serviceDescription[]')
            service_statuses = request.POST.getlist('serviceStatus[]')
            service_charges = request.POST.getlist('serviceCharge[]')
            
            logger.info("=== BILLING DEBUG START ===")
            logger.info(f"Item Names: {item_names}")
            logger.info(f"Service Charges: {service_charges}")
            logger.info(f"Service Statuses (from form): {service_statuses}")
            
            # Validate required fields
            if not all([ticket_no, date, customer_name, customer_contact]):
                messages.error(request, "Please fill in all required fields.")
                return redirect('app5:service_billing_view')
            
            if not item_names or not any(name.strip() for name in item_names):
                messages.error(request, "At least one service item is required.")
                return redirect('app5:service_billing_view')
            
            # Get the job card
            try:
                jobcard = JobCard.objects.get(ticket_no=ticket_no, technician=current_user_name)
            except JobCard.DoesNotExist:
                messages.error(request, "Job card not found or you are not assigned to this job.")
                return redirect('app5:service_billing_view')
            
            # Check if invoice already exists
            existing_invoice = ServiceBilling.objects.filter(ticket_no=ticket_no).first()
            if existing_invoice:
                messages.warning(request, f"An invoice already exists for this job card: INV-{existing_invoice.ticket_no}")
                return redirect('app5:service_billing_view')
            
            # âœ… FIXED: Amount determines service type
            subtotal = 0.00
            services_data = []
            free_items_count = 0
            payable_items_count = 0
            
            for i in range(len(item_names)):
                if not item_names[i].strip():
                    continue
                
                # Get the charge amount first
                try:
                    charge_value = service_charges[i] if i < len(service_charges) else '0'
                    charge = float(charge_value) if charge_value else 0.00
                except (ValueError, TypeError) as e:
                    logger.error(f"Error parsing charge for item {i}: {e}")
                    charge = 0.00
                
                # âœ… DETERMINE SERVICE TYPE BASED ON AMOUNT
                if charge == 0.00:
                    # Amount is 0 â†’ Free Service
                    service_status = 'Free'
                    free_items_count += 1
                    logger.info(f"Item {i}: {item_names[i]} - Amount: â‚¹0.00 â†’ FREE SERVICE")
                else:
                    # Amount > 0 â†’ Payable Service
                    service_status = 'Payment'
                    subtotal += charge
                    payable_items_count += 1
                    logger.info(f"Item {i}: {item_names[i]} - Amount: â‚¹{charge} â†’ PAYABLE - Running Subtotal: â‚¹{subtotal}")
                
                # Safe access to other fields
                serial_no = item_serials[i] if i < len(item_serials) else ''
                service_description = service_descriptions[i] if i < len(service_descriptions) else ''
                
                services_data.append({
                    'item_name': item_names[i],
                    'serial_no': serial_no,
                    'service_description': service_description,
                    'service_status': service_status,  # Auto-determined
                    'charge': charge
                })
            
            # Calculate final totals
            tax = round(subtotal * 0.1, 2)  # 10% tax on payable items only
            total = round(subtotal + tax, 2)
            
            logger.info("=== FINAL CALCULATIONS ===")
            logger.info(f"Free Items (Amount = 0): {free_items_count}")
            logger.info(f"Payable Items (Amount > 0): {payable_items_count}")
            logger.info(f"Subtotal: â‚¹{subtotal}")
            logger.info(f"Tax (10%): â‚¹{tax}")
            logger.info(f"Total: â‚¹{total}")
            logger.info("=== BILLING DEBUG END ===")
            
            # Create ServiceBilling record
            service_billing = ServiceBilling.objects.create(
                ticket_no=ticket_no,
                date=date,
                customer_name=customer_name,
                customer_contact=customer_contact,
                customer_address=customer_address,
                technician=current_user_name,
                subtotal=subtotal,
                tax=tax,
                total=total,
                payment_status=payment_status,
                notes=notes
            )
            
            # Create ServiceItem records
            for item_data in services_data:
                ServiceItem.objects.create(
                    billing=service_billing,
                    item_name=item_data['item_name'],
                    serial_no=item_data['serial_no'],
                    service_description=item_data['service_description'],
                    charge=item_data['charge'],
                    service_status=item_data['service_status']  # Auto-determined
                )
            
            # Update job card status
            jobcard.status = 'completed'
            if jobcard.items_data:
                for item in jobcard.items_data:
                    item['status'] = 'completed'
            jobcard.save()
            
            # Prepare billing data for display
            billing_data = {
                'invoice_no': f"INV-{service_billing.ticket_no}",
                'ticket_no': ticket_no,
                'date': date,
                'customer_name': customer_name,
                'customer_contact': customer_contact,
                'customer_address': customer_address,
                'payment_status': payment_status,
                'technician': current_user_name,
                'services': [[
                    item['item_name'], 
                    item['serial_no'], 
                    item['service_description'], 
                    float(item['charge']),
                    item['service_status']
                ] for item in services_data],
                'subtotal': float(subtotal),
                'tax': float(tax),
                'total': float(total),
                'notes': notes,
                'generated_at': timezone.now().strftime('%d %b %Y %I:%M %p'),
                'free_items_count': free_items_count,
                'payable_items_count': payable_items_count
            }
            
            # Send WhatsApp notification
            try:
                items_list = "\n".join([
                    f"â€¢ {service[0]}: â‚¹{service[3]:.2f} ({'FREE' if service[3] == 0 else 'PAID'})" 
                    for service in billing_data['services']
                ])
                message_text = (
                    f"ðŸ“‹ *Service Invoice Generated*\n\n"
                    f"*Invoice No:* {billing_data['invoice_no']}\n"
                    f"*Date:* {billing_data['date']}\n"
                    f"*Customer:* {billing_data['customer_name']}\n"
                    f"*Phone:* {billing_data['customer_contact']}\n"
                    f"*Technician:* {billing_data['technician']}\n\n"
                    f"*Services:*\n{items_list}\n\n"
                    f"*Free Services:* {free_items_count}\n"
                    f"*Payable Services:* {payable_items_count}\n"
                    f"*Subtotal:* â‚¹{billing_data['subtotal']:.2f}\n"
                    f"*Tax (10%):* â‚¹{billing_data['tax']:.2f}\n"
                    f"*Total Amount Due:* â‚¹{billing_data['total']:.2f}\n\n"
                    f"*Payment Status:* {billing_data['payment_status'].title()}"
                )
                
                whatsapp_api_base = "https://app.dxing.in/api/send/whatsapp"
                params = {
                    "secret": settings.DXING_SECRET,
                    "account": settings.DXING_ACCOUNT,
                    "type": "text",
                    "priority": 1,
                    "recipient": "9946545535",
                    "message": message_text
                }
                requests.get(whatsapp_api_base, params=params, timeout=5)
            except Exception as e:
                logger.debug(f"WhatsApp notification failed: {e}")
            
            success_message = f"âœ… Invoice created successfully for ticket {ticket_no}!"
            if free_items_count > 0 and payable_items_count > 0:
                success_message += f" ({free_items_count} free, {payable_items_count} payable - Total: â‚¹{total})"
            elif free_items_count > 0 and payable_items_count == 0:
                success_message += f" (All {free_items_count} services are FREE)"
            else:
                success_message += f" (Total: â‚¹{total})"
            
            messages.success(request, success_message)
            
            context = {
                'show_invoice': True,
                'billing_data': billing_data,
                'current_user_name': current_user_name,
            }
            
            return render(request, 'service_billing.html', context)
            
        except Exception as e:
            import traceback
            logger.error(f"Error generating invoice: {str(e)}\n{traceback.format_exc()}")
            messages.error(request, f"Error generating invoice: {str(e)}")
            return redirect('app5:service_billing_view')
    
    # GET request - show form
    technician_jobcards = JobCard.objects.filter(
        technician=current_user_name,
        status__in=['accepted', 'sent_technician']
    ).order_by('-created_at')
    
    # Check for pre-selected job card
    ticket_no = request.GET.get('ticket_no')
    pre_selected_jobcard = None
    if ticket_no:
        try:
            pre_selected_jobcard = JobCard.objects.get(ticket_no=ticket_no, technician=current_user_name)
        except JobCard.DoesNotExist:
            pass
    
    context = {
        'show_invoice': False,
        'technician_jobcards': technician_jobcards,
        'pre_selected_jobcard': pre_selected_jobcard,
        'current_user_name': current_user_name,
        'today': timezone.now().date().isoformat(),
    }
    
    return render(request, 'service_billing.html', context)


@require_http_methods(["GET"])
def get_jobcard_details(request, ticket_no):
    """
    API endpoint to get job card details for pre-filling billing form
    """
    try:
        jobcard = get_object_or_404(JobCard, ticket_no=ticket_no)
        
        items = []
        if hasattr(jobcard, 'items_data') and jobcard.items_data:
            for item in jobcard.items_data:
                items.append({
                    'name': item.get('item', ''),
                    'serial': item.get('serial', ''),
                    'config': item.get('config', ''),
                })
        
        return JsonResponse({
            'success': True,
            'items': items,
            'customer': jobcard.customer,
            'phone': jobcard.phone,
            'address': jobcard.address,
        })
    
    except JobCard.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Job card not found'
        }, status=404)
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
    

def service_billing_list(request):
    """
    Display list of job cards with invoice status - FIXED VERSION
    """
    current_user_name = "Unknown"
    if request.session.get('custom_user_id'):
        try:
            current_user = User.objects.get(id=request.session['custom_user_id'])
            current_user_name = getattr(
                current_user, "name",
                current_user.username if hasattr(current_user, 'username') else str(current_user)
            )
        except User.DoesNotExist:
            pass

    # Get all jobcards for this technician
    jobcards = JobCard.objects.filter(technician=current_user_name).order_by('-created_at')

    # Enhanced jobcard processing with invoice data
    for jobcard in jobcards:
        try:
            # Check if invoice exists for this jobcard
            invoice = ServiceBilling.objects.filter(ticket_no=jobcard.ticket_no).first()
            if invoice:
                jobcard.has_invoice = True
                jobcard.invoice = invoice
                
                # Get service items for this invoice
                service_items = ServiceItem.objects.filter(billing=invoice)
                jobcard.service_items_list = [f"{item.item_name} (â‚¹{item.charge})" for item in service_items]
                jobcard.invoice_total = invoice.total
            else:
                jobcard.has_invoice = False
                jobcard.service_items_list = []
                jobcard.invoice_total = 0
                
        except Exception as e:
            jobcard.has_invoice = False
            jobcard.service_items_list = []
            jobcard.invoice_total = 0

    # Counts for dashboard
    total_jobcards = jobcards.count()
    accepted_count = jobcards.filter(status='accepted').count()
    completed_count = jobcards.filter(status='completed').count()
    returned_count = jobcards.filter(status='returned').count()
    
    # Count invoices
    invoiced_count = ServiceBilling.objects.filter(technician=current_user_name).count()

    paginator = Paginator(jobcards, 25)
    page_number = request.GET.get('page')
    jobcards_page = paginator.get_page(page_number)

    context = {
        'jobcards': jobcards_page,
        'total_jobcards': total_jobcards,
        'accepted_count': accepted_count,
        'completed_count': completed_count,
        'returned_count': returned_count,
        'invoiced_count': invoiced_count,
        'current_user_name': current_user_name,
    }
    return render(request, 'service_billing_list.html', context)





def service_billing_edit(request, ticket_no):
    """
    Edit an existing service invoice
    âœ… FIXED: Amount determines service type (0 = Free, >0 = Payable)
    """
    # Get current user
    current_user_name = "Unknown"
    if request.session.get('custom_user_id'):
        try:
            current_user = User.objects.get(id=request.session['custom_user_id'])
            current_user_name = getattr(current_user, "name", current_user.username if hasattr(current_user, 'username') else str(current_user))
        except User.DoesNotExist:
            pass
    
    try:
        # Get the existing invoice
        service_billing = get_object_or_404(ServiceBilling, ticket_no=ticket_no)
        
        if request.method == 'POST':
            # Update invoice data
            service_billing.date = request.POST.get('date')
            service_billing.customer_name = request.POST.get('customerName')
            service_billing.customer_contact = request.POST.get('customerContact')
            service_billing.customer_address = request.POST.get('customerAddress')
            service_billing.payment_status = request.POST.get('paymentStatus')
            service_billing.notes = request.POST.get('notes', '')
            
            # Get service items data
            item_names = request.POST.getlist('itemName[]')
            item_serials = request.POST.getlist('itemSerial[]')
            service_descriptions = request.POST.getlist('serviceDescription[]')
            service_charges = request.POST.getlist('serviceCharge[]')
            
            logger.info("=== EDIT BILLING DEBUG START ===")
            logger.info(f"Editing ticket: {ticket_no}")
            logger.info(f"Item Names: {item_names}")
            logger.info(f"Service Charges: {service_charges}")
            
            # Delete existing items
            service_billing.service_items.all().delete()
            
            # âœ… FIXED: Amount determines service type
            subtotal = 0.00
            services_data = []
            free_items_count = 0
            payable_items_count = 0
            
            for i in range(len(item_names)):
                if not item_names[i].strip():
                    continue
                
                # Get the charge amount first
                try:
                    charge_value = service_charges[i] if i < len(service_charges) else '0'
                    charge = float(charge_value) if charge_value else 0.00
                except (ValueError, TypeError) as e:
                    logger.error(f"Error parsing charge for item {i}: {e}")
                    charge = 0.00
                
                # âœ… DETERMINE SERVICE TYPE BASED ON AMOUNT
                if charge == 0.00:
                    # Amount is 0 â†’ Free Service
                    service_status = 'Free'
                    free_items_count += 1
                    logger.info(f"Item {i}: {item_names[i]} - Amount: â‚¹0.00 â†’ FREE SERVICE")
                else:
                    # Amount > 0 â†’ Payable Service
                    service_status = 'Payment'
                    subtotal += charge
                    payable_items_count += 1
                    logger.info(f"Item {i}: {item_names[i]} - Amount: â‚¹{charge} â†’ PAYABLE - Running Subtotal: â‚¹{subtotal}")
                
                # Safe access to other fields
                serial_no = item_serials[i] if i < len(item_serials) else ''
                service_description = service_descriptions[i] if i < len(service_descriptions) else ''
                
                # Create ServiceItem
                ServiceItem.objects.create(
                    billing=service_billing,
                    item_name=item_names[i],
                    serial_no=serial_no,
                    service_description=service_description,
                    charge=charge,
                    service_status=service_status  # Auto-determined
                )
                
                services_data.append({
                    'item_name': item_names[i],
                    'serial_no': serial_no,
                    'service_description': service_description,
                    'service_status': service_status,
                    'charge': charge
                })
            
            # Calculate final totals
            tax = round(subtotal * 0.1, 2)
            total = round(subtotal + tax, 2)
            
            logger.info("=== FINAL CALCULATIONS ===")
            logger.info(f"Free Items (Amount = 0): {free_items_count}")
            logger.info(f"Payable Items (Amount > 0): {payable_items_count}")
            logger.info(f"Subtotal: â‚¹{subtotal}")
            logger.info(f"Tax (10%): â‚¹{tax}")
            logger.info(f"Total: â‚¹{total}")
            logger.info("=== EDIT BILLING DEBUG END ===")
            
            # Update billing totals
            service_billing.subtotal = subtotal
            service_billing.tax = tax
            service_billing.total = total
            service_billing.save()
            
            success_message = f"âœ… Invoice updated successfully for ticket {ticket_no}!"
            if free_items_count > 0 and payable_items_count > 0:
                success_message += f" ({free_items_count} free, {payable_items_count} payable - Total: â‚¹{total})"
            elif free_items_count > 0 and payable_items_count == 0:
                success_message += f" (All {free_items_count} services are FREE)"
            else:
                success_message += f" (Total: â‚¹{total})"
            
            messages.success(request, success_message)
            return redirect('app5:service_billing_list')
        
        # GET request - show edit form
        invoice_items = service_billing.service_items.all()
        
        # Prepare services data
        services_data = []
        for item in invoice_items:
            services_data.append({
                'item_name': item.item_name,
                'serial_no': item.serial_no or '',
                'service_description': item.service_description,
                'service_status': item.service_status,
                'charge': float(item.charge)
            })
        
        context = {
            'service_billing': service_billing,
            'invoice_items': invoice_items,
            'services_data': services_data,
            'current_user_name': current_user_name,
            'is_edit': True,
        }
        
        return render(request, 'service_billing_edit.html', context)
        
    except ServiceBilling.DoesNotExist:
        messages.error(request, f"No invoice found for ticket {ticket_no}.")
        return redirect('app5:service_billing_list')
    except Exception as e:
        messages.error(request, f"Error editing invoice: {str(e)}")
        return redirect('app5:service_billing_list')


def view_service_invoice(request, ticket_no):
    """
    View to display a generated service invoice for a specific ticket
    """
    # Get current user
    current_user_name = "Unknown"
    if request.session.get('custom_user_id'):
        try:
            current_user = User.objects.get(id=request.session['custom_user_id'])
            current_user_name = getattr(current_user, "name", current_user.username if hasattr(current_user, 'username') else str(current_user))
        except User.DoesNotExist:
            pass
    
    try:
        # Get the job card
        jobcard = get_object_or_404(JobCard, ticket_no=ticket_no, technician=current_user_name)
        
        # Get the invoice for this job card
        service_billing = get_object_or_404(ServiceBilling, ticket_no=ticket_no)
        
        # Get invoice items
        invoice_items = service_billing.service_items.all()
        
        # Prepare billing data for template
        services = []
        for item in invoice_items:
            services.append([
                item.item_name,
                item.serial_no or '',
                item.service_description,
                float(item.charge),  # Keep as float
                item.service_status
            ])

        billing_data = {
            'invoice_no': service_billing.ticket_no,
            'ticket_no': ticket_no,
            'date': service_billing.date.strftime('%Y-%m-%d'),
            'customer_name': service_billing.customer_name,
            'customer_contact': service_billing.customer_contact,
            'customer_address': service_billing.customer_address,
            'payment_status': service_billing.payment_status,
            'technician': service_billing.technician,
            'services': services,
            'subtotal': float(service_billing.subtotal),
            'tax': float(service_billing.tax),
            'total': float(service_billing.total),
            'notes': service_billing.notes or '',
            'generated_at': service_billing.created_at.strftime('%d %b %Y %I:%M %p'),
            'free_items_count': invoice_items.filter(charge=0).count(),
            'payable_items_count': invoice_items.filter(charge__gt=0).count()
        }
        
        context = {
            'show_invoice': True,
            'billing_data': billing_data,
            'current_user_name': current_user_name,
            'is_view_only': True,
        }
        
        return render(request, 'service_billing.html', context)
        
    except JobCard.DoesNotExist:
        messages.error(request, f"Job card with ticket number {ticket_no} not found or you don't have permission to view it.")
        return redirect('app5:service_billing_list')
    except ServiceBilling.DoesNotExist:
        messages.error(request, f"No invoice found for job card {ticket_no}.")
        return redirect('app5:service_billing_list')
    except Exception as e:
        messages.error(request, f"Error loading invoice: {str(e)}")
        return redirect('app5:service_billing_list')
    


@require_http_methods(["DELETE", "POST"])
def delete_service_invoice(request, ticket_no):
    """
    Delete service invoice and related job card
    """
    try:
        jobcard = get_object_or_404(JobCard, ticket_no=ticket_no)
        
        # Get customer info for confirmation message
        customer_name = jobcard.customer
        customer_phone = jobcard.phone
        
        # Delete the job card (this will cascade to related records)
        jobcard.delete()
        
        return JsonResponse({
            "success": True,
            "message": f"âœ… Invoice for ticket {ticket_no} (Customer: {customer_name}, Phone: {customer_phone}) has been deleted successfully!"
        })
        
    except JobCard.DoesNotExist:
        return JsonResponse({
            "success": False,
            "error": f"Job card with ticket number {ticket_no} not found"
        }, status=404)
    except Exception as e:
        return JsonResponse({
            "success": False,
            "error": f"Error deleting invoice: {str(e)}"
        }, status=500)
    

@csrf_exempt
@require_http_methods(["POST"])
def update_jobcard_status_by_ticket(request):
    """
    Update job card status by ticket number (for service billing list)
    """
    try:
        data = json.loads(request.body)
        ticket_no = data.get('ticket_no')
        action = data.get('action')
        
        if not ticket_no or not action:
            return JsonResponse({
                "success": False, 
                "error": "Ticket number and action are required"
            })
        
        # Get the job card by ticket number
        jobcard = get_object_or_404(JobCard, ticket_no=ticket_no)
        
        # Map actions to status values
        status_mapping = {
            "completed": "completed",
            "returned": "returned"
        }
        
        if action in status_mapping:
            new_status = status_mapping[action]
            jobcard.status = new_status
            
            # Update individual item statuses
            if jobcard.items_data:
                for item in jobcard.items_data:
                    item['status'] = new_status
            
            jobcard.save()
            
            return JsonResponse({
                "success": True, 
                "status": new_status,
                "message": f"Job card {ticket_no} status updated to {new_status}"
            })
        else:
            return JsonResponse({
                "success": False, 
                "error": "Invalid action"
            })
            
    except JobCard.DoesNotExist:
        return JsonResponse({
            "success": False, 
            "error": f"Job card with ticket number {ticket_no} not found"
        })
    except Exception as e:
        return JsonResponse({
            "success": False, 
            "error": str(e)
        })


        # Add this function to your views.py

@require_http_methods(["GET"])
def api_jobcard_status(request, ticket_no):
    """
    API endpoint to get job card status by ticket number
    """
    try:
        jobcard = get_object_or_404(JobCard, ticket_no=ticket_no)
        
        return JsonResponse({
            'success': True,
            'ticket_no': jobcard.ticket_no,
            'status': jobcard.status,
            'technician': jobcard.technician or '',
            'customer': jobcard.customer,
            'phone': jobcard.phone,
            'address': jobcard.address,
            'items_count': len(jobcard.items_data) if jobcard.items_data else 0,
            'created_at': jobcard.created_at.isoformat() if jobcard.created_at else None
        })
    
    except JobCard.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': f'Job card with ticket number {ticket_no} not found'
        }, status=404)
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
    


# lead
# app5/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q
from django.http import JsonResponse
from django.urls import reverse
from django.apps import apps

from .models import Lead, RequirementItem
from django.db.models import Sum

# Import user model and District (custom app1)
from app1.models import User, District

# Optional imports (defensive)
try:
    from app1.models import BusinessNature
except Exception:
    BusinessNature = None

try:
    from app1.models import StateMaster
except Exception:
    StateMaster = None

try:
    from purchase_order.models import Department
except Exception:
    Department = None


# -----------------------
# Helper utilities
# -----------------------
def resolve_active_user(val):
    """
    Try to resolve a user value (pk, userid, email) to an active User instance.
    Returns User or None.
    """
    if not val:
        return None

    # try pk
    try:
        return User.objects.get(pk=int(val), is_active=True)
    except Exception:
        pass

    # try userid
    try:
        return User.objects.get(userid=val, is_active=True)
    except Exception:
        pass

    # try email
    try:
        return User.objects.get(email__iexact=val, is_active=True)
    except Exception:
        pass

    return None


def user_display_name(u):
    """
    Return a friendly display name for a user object.
    Prefer get_full_name(), then name attribute, then username, then pk.
    """
    if not u:
        return ""
    try:
        full = u.get_full_name()
    except Exception:
        full = ""
    if full:
        return full
    return getattr(u, "name", "") or getattr(u, "username", "") or str(getattr(u, "pk", ""))


# -----------------------
# Lead form view (create)
from django.contrib.auth.decorators import login_required
from django.utils import timezone
import logging
import json
import requests
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.apps import apps
from django.db import transaction
from django.db.models import Q
from decimal import Decimal

logger = logging.getLogger(__name__)


@login_required




@login_required
def lead_form_view(request):
    """
    GET: show form with API data and campaigns
    POST: create Lead with proper saving of marketedBy, consultant, branch, and
          support for firm-name toggle (existing firm select OR free-text name).
    """
    import logging
    import json
    import requests  # Added for API calls
    from django.shortcuts import render, redirect, get_object_or_404
    from django.contrib import messages
    from django.contrib.auth import get_user_model
    from django.apps import apps
    from django.utils import timezone
    from django.db import transaction
    from django.db.models import Q

    logger = logging.getLogger(__name__)

    # Resolve user model
    try:
        from app1.models import User as AppUser
        UserModel = AppUser
    except Exception:
        UserModel = get_user_model()

    # ✅ GET LOGGED-IN USER
    current_user = None
    current_user_name = None
    if request.session.get('custom_user_id'):
        try:
            current_user = UserModel.objects.get(id=request.session['custom_user_id'])
            current_user_name = getattr(current_user, 'name', current_user.username if hasattr(current_user, 'username') else str(current_user))
            
            # ✅ LOG USER INFO FOR DEBUGGING
            logger.info(f"========================================")
            logger.info(f"Current User: {current_user_name}")
            logger.info(f"User ID: {current_user.id}")
            logger.info(f"User Level: {getattr(current_user, 'user_level', 'N/A')}")
            logger.info(f"Is Superuser: {getattr(current_user, 'is_superuser', False)}")
            logger.info(f"Is Staff: {getattr(current_user, 'is_staff', False)}")
            logger.info(f"========================================")
            
        except UserModel.DoesNotExist:
            logger.warning(f"User with ID {request.session['custom_user_id']} not found")

    # Resolve Lead model defensively
    try:
        from .models import Lead
    except Exception:
        try:
            Lead = apps.get_model('app5', 'Lead')
        except Exception:
            Lead = None

    # ✅ NEW: FETCH CAMPAIGNS FROM DATABASE
    campaigns = []
    try:
        from campaign.models import Campaigning
        campaigns = Campaigning.objects.filter(is_deleted=False).order_by('-campaign_id')
        logger.info(f"✅ Loaded {campaigns.count()} campaigns from database")
    except Exception as e:
        logger.warning(f"⚠️ Could not load campaigns: {e}")
        campaigns = []

    # ✅ UPDATED: Get active leads with ENHANCED ADMIN FILTERING
    active_leads_data = []
    if Lead:
        try:
            # Import Campaigning model for campaign details
            try:
                from campaign.models import Campaigning
                has_campaigning = True
            except Exception:
                has_campaigning = False
                logger.warning("Campaigning model not available")

            # ✅ Start with all active leads
            active_leads_qs = Lead.objects.filter(status__iexact='Active')
            total_active = active_leads_qs.count()
            logger.info(f"📊 Total active leads in database: {total_active}")
            
            # ✅ Apply user-based filtering with enhanced admin detection
            if current_user:
                active_leads_qs = get_user_filtered_leads(current_user, active_leads_qs)
                filtered_count = active_leads_qs.count()
                logger.info(f"📊 After filtering: {filtered_count} leads visible to {current_user_name}")
            else:
                # No user logged in - show no leads for security
                active_leads_qs = active_leads_qs.none()
                logger.warning("⚠️ No current user - showing 0 leads")
            
            active_leads_qs = active_leads_qs.order_by('-created_at')[:50]
            
            # Process each lead to ensure all fields are properly formatted
            for lead in active_leads_qs:
                # ✅ Get campaign display name if campaign ID exists
                campaign_display = ""
                if hasattr(lead, 'campaign') and lead.campaign:
                    try:
                        if has_campaigning:
                            # Try to get campaign details from Campaigning model
                            campaign = Campaigning.objects.filter(
                                campaign_unique_id=lead.campaign
                            ).first()
                            
                            if campaign:
                                # Build full display name: ID - Name (Software) [Status]
                                campaign_display = f"{campaign.campaign_unique_id} - {campaign.campaign_name}"
                                if campaign.software_name:
                                    campaign_display += f" ({campaign.software_name})"
                                if campaign.status:
                                    campaign_display += f" [{campaign.status.title()}]"
                            else:
                                # Campaign ID not found, use raw value
                                campaign_display = lead.campaign
                        else:
                            # Campaigning model not available, use raw value
                            campaign_display = lead.campaign
                    except Exception as e:
                        logger.debug(f"Could not fetch campaign details: {e}")
                        campaign_display = lead.campaign
                
                # ✅ ADD TIME ELAPSED CALCULATION
                time_elapsed = ""
                if hasattr(lead, 'created_at') and lead.created_at:
                    now = timezone.now()
                    delta = now - lead.created_at
                    
                    if delta.days > 365:
                        years = delta.days // 365
                        time_elapsed = f"{years} year{'s' if years > 1 else ''} ago"
                    elif delta.days > 30:
                        months = delta.days // 30
                        time_elapsed = f"{months} month{'s' if months > 1 else ''} ago"
                    elif delta.days > 0:
                        time_elapsed = f"{delta.days} day{'s' if delta.days > 1 else ''} ago"
                    elif delta.seconds > 3600:
                        hours = delta.seconds // 3600
                        time_elapsed = f"{hours} hour{'s' if hours > 1 else ''} ago"
                    elif delta.seconds > 60:
                        minutes = delta.seconds // 60
                        time_elapsed = f"{minutes} minute{'s' if minutes > 1 else ''} ago"
                    else:
                        time_elapsed = "Just now"
                
                # Build requirements JSON for each lead
                requirements_data = []
                if hasattr(lead, 'requirements'):
                    for req in lead.requirements.all():
                        requirements_data.append({
                            'id': req.id,
                            'item_id': req.item.id if hasattr(req, 'item') and req.item else None,
                            'item_name': getattr(req, 'item_name', ''),
                            'section': getattr(req, 'section', 'GENERAL'),
                            'unit': getattr(req, 'unit', 'pcs'),
                            'price': float(req.price) if req.price is not None else 0.00,
                            'quantity': int(req.quantity) if req.quantity is not None else 1,
                        })
                
                requirements_json = json.dumps(requirements_data) if requirements_data else '[]'
                
                lead_dict = {
                    'id': lead.id,
                    'ownerName': lead.ownerName,
                    'phoneNo': lead.phoneNo,
                    'email': lead.email if lead.email else '',
                    'ticket_number': getattr(lead, 'ticket_number', f'TKT-{lead.id}'),
                    'status': lead.status,
                    'priority': getattr(lead, 'priority', 'Medium'),
                    'customerType': lead.customerType,
                    'name': lead.name if lead.name else '',
                    'address': lead.address if lead.address else '',
                    'place': lead.place if lead.place else '',
                    'District': lead.District if lead.District else '',
                    'State': lead.State if lead.State else '',
                    'pinCode': lead.pinCode if lead.pinCode else '',
                    'firstName': lead.firstName if lead.firstName else '',
                    'lastName': getattr(lead, 'lastName', '') if hasattr(lead, 'lastName') else '',
                    'individualAddress': lead.individualAddress if lead.individualAddress else '',
                    'individualPlace': lead.individualPlace if lead.individualPlace else '',
                    'individualDistrict': lead.individualDistrict if lead.individualDistrict else '',
                    'individualState': lead.individualState if lead.individualState else '',
                    'individualPinCode': lead.individualPinCode if lead.individualPinCode else '',
                    'refFrom': lead.refFrom if lead.refFrom else '',
                    'business': lead.business if lead.business else '',
                    'campaign': lead.campaign if hasattr(lead, 'campaign') and lead.campaign else '',
                    'campaign_display': campaign_display,
                    'marketedBy': lead.marketedBy if lead.marketedBy else '',
                    'Consultant': lead.Consultant if lead.Consultant else '',
                    'requirement': lead.requirement if lead.requirement else '',
                    'details': lead.details if lead.details else '',
                    'requirements_count': len(requirements_data),
                    'requirements_json': requirements_json,
                    'date': lead.date.strftime('%Y-%m-%d') if lead.date else '',
                    'created_at': lead.created_at if hasattr(lead, 'created_at') else None,
                    'time_elapsed': time_elapsed,
                }
                active_leads_data.append(lead_dict)
            
            logger.info(f"✅ Final result: {len(active_leads_data)} leads prepared for user {current_user_name}")
            
        except Exception as e:
            logger.error(f"❌ Error fetching active leads: {e}", exc_info=True)
            active_leads_data = []

    # -------------------------
    # Determine active users robustly
    # Build a list of dicts: {'id', 'name', 'department'}
    # -------------------------
    active_users = []
    user_field_names = []
    
    try:
        # Get field names from User model
        from app1.models import User
        user_field_names = [f.name for f in User._meta.get_fields()]
        
        # Try to get active users
        if 'status' in user_field_names:
            active_users = list(User.objects.filter(status='active').values('id', 'name', 'department', 'designation').order_by('name'))
        elif 'is_active' in user_field_names:
            users_qs = User.objects.filter(is_active=True).order_by('name')
            for u in users_qs:
                active_users.append({
                    'id': u.id,
                    'name': getattr(u, 'name', str(u)),
                    'department': getattr(u, 'department', ''),
                    'designation': getattr(u, 'designation', '')
                })
    except Exception as e:
        logger.warning(f"Could not fetch users from app1.User: {e}")

    # Fallback: try with UserModel if active_users is still empty
    if not active_users:
        try:
            # choose filter predicate
            if 'status' in user_field_names:
                users_qs = UserModel.objects.filter(status__iexact='active').order_by('name')
            elif 'is_active' in user_field_names:
                users_qs = UserModel.objects.filter(is_active=True).order_by('first_name', 'username')
            else:
                users_qs = UserModel.objects.all().order_by('id')

            # Build portable display name & department/role
            for u in users_qs:
                # determine display name
                display_name = None
                # common attributes in different user models
                for attr in ('name', 'full_name', 'get_full_name', 'first_name', 'username', 'email'):
                    try:
                        if attr == 'get_full_name' and hasattr(u, 'get_full_name'):
                            val = u.get_full_name()
                        else:
                            val = getattr(u, attr, None)
                        if val:
                            display_name = val
                            break
                    except Exception:
                        continue
                if not display_name:
                    display_name = str(u)

                # determine department/role/designation
                role = ''
                designation = ''
                for rattr in ('department', 'dept'):
                    try:
                        val = getattr(u, rattr, None)
                        if val:
                            role = str(val)
                            break
                    except Exception:
                        continue
                
                for dattr in ('designation', 'role', 'position'):
                    try:
                        val = getattr(u, dattr, None)
                        if val:
                            designation = str(val)
                            break
                    except Exception:
                        continue

                active_users.append({
                    'id': getattr(u, 'id', None),
                    'name': display_name,
                    'department': role,
                    'designation': designation
                })

        except Exception as e:
            logger.warning(f"Could not build active_users list: {e}")
            active_users = []

    # ✅ FETCH CUSTOMER DATA FROM API
    existing_firms = []
    api_customer_data = []
    
    try:
        # Fetch from API
        api_url = "https://accmaster.imcbs.com/api/sync/rrc-clients/"
        logger.info(f"Fetching customer data from API: {api_url}")
        
        # Add headers to mimic a browser request
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/json',
        }
        
        response = requests.get(api_url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            api_data = response.json()
            logger.info(f"✅ Successfully fetched {len(api_data)} customers from API")
            
            # DEBUG: Log first few customers to check structure
            if api_data:
                logger.info(f"Sample API customer data structure: {api_data[0] if api_data else 'No data'}")
                if api_data:
                    logger.info(f"API keys in first customer: {list(api_data[0].keys())}")
            
            # Process API data for firm names dropdown
            for customer in api_data:
                firm_name = customer.get('name', '').strip()
                
                if firm_name:
                    # Add to existing_firms for searchable select
                    if firm_name not in existing_firms:
                        existing_firms.append(firm_name)
                    
                    # Store full customer data for auto-fill
                    api_customer_data.append({
                        'code': customer.get('code', ''),
                        'name': firm_name,
                        'address': customer.get('address', ''),
                        'address3': customer.get('address3', ''),
                        'branch': customer.get('branch', ''),
                        'district': customer.get('district', ''),
                        'state': customer.get('state', ''),
                        'mobile': customer.get('mobile', ''),
                        'software': customer.get('software', ''),
                        'nature': customer.get('nature', ''),
                        'rout': customer.get('rout', ''),
                        'installationdate': customer.get('installationdate', ''),
                    })
            
            # Sort firms alphabetically
            existing_firms.sort()
            
            logger.info(f"✅ Processed {len(existing_firms)} unique firm names from API")
            logger.info(f"✅ Processed {len(api_customer_data)} full customer records")
            
        else:
            logger.warning(f"⚠️ API returned status code: {response.status_code}")
            logger.warning(f"Response content: {response.text[:200]}")
            messages.warning(request, f"Could not fetch customer data from API (Status: {response.status_code})")
            
    except requests.exceptions.Timeout:
        logger.error("❌ API request timeout")
        messages.warning(request, "API request timed out. Using local data only.")
        
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ API request failed: {e}")
        messages.warning(request, "Could not connect to customer API. Using local data only.")
        
    except Exception as e:
        logger.error(f"❌ Error processing API data: {e}", exc_info=True)
        messages.warning(request, "Error processing customer data from API.")
    
    # ✅ FALLBACK: Add existing firms from local database
    try:
        if Lead:
            local_firms = Lead.objects.filter(
                customerType='Business',
                name__isnull=False
            ).exclude(name='').values_list('name', flat=True).distinct().order_by('name')
            
            for firm in local_firms:
                firm_name = str(firm).strip()
                if firm_name and firm_name not in existing_firms:
                    existing_firms.append(firm_name)
            
            logger.info(f"✅ Added {len(local_firms)} firms from local database")
            
    except Exception as e:
        logger.debug(f"Could not fetch local firms: {e}")
    
    # ✅ ENSURE WE HAVE SAMPLE DATA IF BOTH SOURCES FAIL
    if not existing_firms:
        logger.warning("⚠️ No firms found from API or database, using sample data")
        existing_firms = [
            "ABC Corporation",
            "XYZ Enterprises",
            "Global Solutions Ltd",
            "Tech Innovators Inc",
            "Prime Services Co"
        ]
        # Add sample API data for testing
        api_customer_data = [
            {
                'code': 'TEST001',
                'name': 'ABC Corporation',
                'address': '123 Test Street',
                'address3': 'Test City',
                'branch': 'Main',
                'district': 'Test District',
                'state': 'Test State',
                'mobile': '9876543210',
                'software': 'Test Software',
                'nature': 'Manufacturing',
                'rout': 'Direct',
                'installationdate': '2023-01-01',
            }
        ]
    
    logger.info(f"📊 Final counts - API customers: {len(api_customer_data)}, Unique firms: {len(existing_firms)}, Campaigns: {len(campaigns)}")

    if request.method == "POST":
        data = request.POST

        assignment_type = data.get("assignmentType", "unassigned")
        customer_type = "Business" if data.get("customerTypeToggle") == 'on' else "Individual"

        # ✅ FIXED: Properly resolve marketedBy to user name
        marketed_by_val = data.get("marketedBy")
        marketed_by_name = None

        if marketed_by_val:
            try:
                # Try to get user by ID
                user = UserModel.objects.filter(id=marketed_by_val).first()
                if user:
                    # Get the user's name
                    marketed_by_name = getattr(user, 'name', None) or \
                                      getattr(user, 'username', None) or \
                                      str(user)
                else:
                    # If not found by ID, use the value as-is
                    marketed_by_name = marketed_by_val
            except Exception as e:
                logger.warning(f"Error resolving marketedBy user: {e}")
                marketed_by_name = marketed_by_val

        # ✅ Get consultant name (direct text input)
        consultant_name = data.get("Consultant", "").strip()

        # ✅ FIXED: Get branch/requirement - resolve department name if ID provided
        requirement_val = data.get("requirement", "").strip()
        branch_name = None

        if requirement_val:
            try:
                # Check if it's a department ID
                if requirement_val.isdigit():
                    try:
                        from purchase_order.models import Department
                        dept = Department.objects.filter(id=requirement_val).first()
                        if dept:
                            branch_name = dept.name
                        else:
                            branch_name = requirement_val
                    except Exception:
                        branch_name = requirement_val
                else:
                    branch_name = requirement_val
            except Exception as e:
                logger.warning(f"Error resolving department: {e}")
                branch_name = requirement_val

        # -----------------------
        # ✅ UPDATED: Firm name handling for searchable select
        # -----------------------
        posted_firm_name = data.get('name', '').strip()
        final_name = posted_firm_name

        # ✅ Get campaign details (campaign unique ID)
        campaign_details = data.get("campaign", "").strip()

        # Build the lead data
        lead_kwargs = {
            "ownerName": data.get("ownerName"),
            "phoneNo": data.get("phoneNo"),
            "email": data.get("email"),
            "customerType": customer_type,
            "status": data.get("status") or None,
            "priority": data.get("priority") or "Medium",
            "refFrom": data.get("refFrom"),
            "business": data.get("business"),
            "campaign": campaign_details,
            "details": data.get("details"),
            "marketedBy": marketed_by_name,
            "Consultant": consultant_name,
            "requirement": branch_name,
            "assignment_type": assignment_type,
            "date": data.get("date") or None,
        }

        # ✅ ADD FIRM/BUSINESS SPECIFIC FIELDS BASED ON CUSTOMER TYPE
        if customer_type == "Business":
            lead_kwargs.update({
                "name": final_name,
                "address": data.get("address"),
                "place": data.get("place"),
                "District": data.get("District"),
                "State": data.get("State"),
                "pinCode": data.get("pinCode"),
            })
        else:  # Individual
            lead_kwargs.update({
                "firstName": data.get("firstName"),
                "lastName": data.get("lastName"),
                "individualAddress": data.get("individualAddress"),
                "individualPlace": data.get("individualPlace"),
                "individualDistrict": data.get("individualDistrict"),
                "individualState": data.get("individualState"),
                "individualPinCode": data.get("individualPinCode"),
            })

        # ✅ Handle assignment if self-assigned
        if assignment_type == "self_assigned":
            try:
                assign_user = None
                if request.session.get('custom_user_id'):
                    try:
                        assign_user = UserModel.objects.get(id=request.session['custom_user_id'])
                    except Exception:
                        assign_user = None
                elif request.user and request.user.is_authenticated:
                    assign_user = request.user

                if assign_user:
                    assigned_name = getattr(assign_user, 'name', None) or \
                                  getattr(assign_user, 'username', None) or \
                                  str(assign_user)

                    lead_kwargs["assigned_to_name"] = assigned_name
                    lead_kwargs["assigned_date"] = timezone.now().date()
                    lead_kwargs["assigned_time"] = timezone.now().time()
                    lead_kwargs["assigned_by_name"] = assigned_name

                    if Lead and hasattr(Lead, 'assigned_to') and assign_user:
                        lead_kwargs["assigned_to"] = assign_user
                        
                    if Lead and hasattr(Lead, 'assigned_by') and assign_user:
                        lead_kwargs["assigned_by"] = assign_user

            except Exception as e:
                logger.warning(f"Error setting self-assignment: {e}")

        # Save the lead
        if not Lead:
            messages.error(request, "Lead model not available; cannot save.")
            return redirect("app5:lead")

        try:
            with transaction.atomic():
                model_field_names = {f.name for f in Lead._meta.get_fields()}

                safe_kwargs = {}
                for k, v in lead_kwargs.items():
                    if k in model_field_names:
                        safe_kwargs[k] = v
                    else:
                        # Try common alternate mappings
                        if k == 'ownerName' and 'owner_name' in model_field_names:
                            safe_kwargs['owner_name'] = v
                        elif k == 'phoneNo' and 'phone_no' in model_field_names:
                            safe_kwargs['phone_no'] = v
                        elif k == 'marketedBy' and 'marketed_by' in model_field_names:
                            safe_kwargs['marketed_by'] = v
                        elif k == 'assigned_to_name' and 'assigned_to_name' in model_field_names:
                            safe_kwargs['assigned_to_name'] = v
                        elif k == 'assigned_by_name' and 'assigned_by_name' in model_field_names:
                            safe_kwargs['assigned_by_name'] = v

                lead = Lead.objects.create(**safe_kwargs)
                
                # ✅ SET CREATED_BY - THIS IS THE KEY ADDITION
                if current_user:
                    lead.created_by = current_user
                    lead.save(update_fields=['created_by'])

                # ✅ NEW: Extract and save requirement items from form
                requirements_json = data.get('requirements_data', '[]')
                logger.info(f"Requirements JSON from form: {requirements_json}")
                
                try:
                    import json
                    from decimal import Decimal
                    requirements_list = json.loads(requirements_json) if requirements_json else []
                    
                    # Import RequirementItem model
                    try:
                        from .models import RequirementItem
                    except:
                        try:
                            RequirementItem = apps.get_model('app5', 'RequirementItem')
                        except:
                            RequirementItem = None
                    
                    # Create RequirementItem objects for each requirement
                    if RequirementItem and requirements_list:
                        for req_data in requirements_list:
                            RequirementItem.objects.create(
                                lead=lead,
                                item_id=req_data.get('item_id'),
                                item_name=req_data.get('item_name', ''),
                                ticket_number=lead.ticket_number if hasattr(lead, 'ticket_number') else f'TKT-{lead.id}',
                                owner_name=lead.ownerName,
                                phone_no=lead.phoneNo,
                                email=lead.email if lead.email else '',
                                section=req_data.get('section', ''),
                                unit=req_data.get('unit', ''),
                                price=Decimal(str(req_data.get('price', 0))),
                                quantity=int(req_data.get('quantity', 1)),
                            )
                        
                        logger.info(f"✅ Created {len(requirements_list)} requirement items for lead {lead.id}")
                    
                except json.JSONDecodeError as e:
                    logger.warning(f"Could not parse requirements JSON: {e}")
                except Exception as e:
                    logger.error(f"Error creating requirement items: {e}", exc_info=True)

            assignment_msg = "self-assigned" if assignment_type == "self_assigned" else "submitted for assignment"
            ticket_info = getattr(lead, "ticket_number", getattr(lead, "id", ""))

            messages.success(
                request,
                f"Lead saved successfully and {assignment_msg}! Ticket Number: {ticket_info}"
            )
            return redirect("app5:lead_report")

        except Exception as e:
            logger.error(f"Error saving lead: {e}", exc_info=True)
            messages.error(request, f"Error saving lead: {str(e)}")
            
            # On POST error, re-render with form data preserved
            # Get context and render the form again
            context = get_lead_form_context(existing_firms, active_leads_data, active_users)
            # ✅ ADD API DATA TO CONTEXT FOR RE-RENDER
            context['api_customer_data'] = api_customer_data
            context['api_data_count'] = len(api_customer_data)
            context['items_by_section'] = get_items_by_section()
            context['campaigns'] = campaigns  # ✅ ADD CAMPAIGNS
            return render(request, "lead_form.html", context)

    # ============================
    # ✅ GET REQUEST - PREPARE CONTEXT
    # ============================
    # Get context data
    context = get_lead_form_context(existing_firms, active_leads_data, active_users)
    
    # ✅ ADD API CUSTOMER DATA TO CONTEXT
    context['api_customer_data'] = api_customer_data
    context['api_data_count'] = len(api_customer_data)
    
    # ✅ ADD CAMPAIGNS TO CONTEXT
    context['campaigns'] = campaigns
    
    # ✅ ADD ITEMS BY SECTION
    try:
        context['items_by_section'] = get_items_by_section()
    except Exception as e:
        logger.error(f"Error getting items by section: {e}")
        context['items_by_section'] = {}
    
    # ✅ ADD CURRENT USER INFO
    context['current_user'] = current_user
    context['current_user_name'] = current_user_name
    
    logger.info(f"📋 Final context prepared - API customers: {len(api_customer_data)}, Firms: {len(existing_firms)}, Campaigns: {len(campaigns)}")
    
    return render(request, "lead_form.html", context)


def get_user_filtered_leads(user, queryset=None):
    """
    Filter leads based on user permissions.
    """
    from .models import Lead
    import logging
    logger = logging.getLogger(__name__)
    
    if queryset is None:
        queryset = Lead.objects.all()
    
    if not user:
        logger.warning("No user provided - returning empty queryset")
        return queryset.none()
    
    # ✅ ADMIN CHECK
    is_admin = False
    
    if getattr(user, 'is_superuser', False):
        is_admin = True
        logger.info(f"User {user} is Django superuser - showing ALL leads")
    elif getattr(user, 'is_staff', False):
        is_admin = True
        logger.info(f"User {user} is staff - showing ALL leads")
    elif hasattr(user, 'user_level'):
        user_level = str(getattr(user, 'user_level', '')).strip()
        
        admin_levels = [
            'admin_level',
            'normal',
            '4level',
            '5level',
        ]
        
        if user_level in admin_levels:
            is_admin = True
            logger.info(f"User {user} has admin level '{user_level}' - showing ALL leads")
    
    if is_admin:
        logger.info(f"✅ ADMIN USER: {user} - Returning ALL {queryset.count()} leads")
        return queryset
    
    user_name = getattr(user, 'name', None) or \
                getattr(user, 'username', None) or \
                str(user)
    
    logger.info(f"👤 REGULAR USER: {user_name} - Filtering leads...")
    
    filtered_queryset = queryset.filter(
        Q(created_by=user) | 
        Q(assigned_to_name=user_name) |
        Q(marketedBy=user_name)
    ).distinct()
    
    logger.info(f"✅ REGULAR USER: {user_name} - Showing {filtered_queryset.count()} filtered leads")
    
    return filtered_queryset


def get_items_by_section():
    """Helper function to load items grouped by section"""
    import logging
    logger = logging.getLogger(__name__)
    
    items_by_section = {}
    
    try:
        from purchase_order.models import Item as POItem

        po_items = POItem.objects.filter(is_active=True).order_by('section', 'name')
        
        logger.info(f"✅ Fetched {po_items.count()} items from purchase_order")
        
        for item in po_items:
            section_raw = (item.section or 'GENERAL').upper().strip()
            
            section = section_raw
            if 'HARDWARE' in section_raw:
                section = 'HARDWARE'
            elif 'SOFTWARE' in section_raw:
                section = 'SOFTWARE'
            elif 'PAPER' in section_raw or 'ROLL' in section_raw:
                section = 'PAPER_ROLLS'
            elif not section_raw or section_raw == '':
                section = 'GENERAL'
            
            if section not in items_by_section:
                items_by_section[section] = []
            
            section_display = section.replace('_', ' ').title()
            
            items_by_section[section].append({
                "id": item.id,
                "name": item.name,
                "section": section,
                "section_display": section_display,
                "unit": item.unit_of_measure or "pcs",
                "price": float(item.mrp or 0),
                "hsn": item.hsn_code or "",
                "description": item.description or "",
            })
        
        logger.info(f"✅ Items grouped into {len(items_by_section)} sections: {list(items_by_section.keys())}")
        
    except Exception as e:
        logger.error(f"❌ Could not load purchase_order items: {e}", exc_info=True)
        items_by_section = {
            "HARDWARE": [
                {"id": 1, "name": "Computer", "section": "HARDWARE", "section_display": "Hardware", 
                 "unit": "pcs", "price": 50000.0, "hsn": "8471", "description": "Desktop Computer"},
                {"id": 2, "name": "Printer", "section": "HARDWARE", "section_display": "Hardware", 
                 "unit": "pcs", "price": 15000.0, "hsn": "8443", "description": "Laser Printer"},
            ],
            "SOFTWARE": [
                {"id": 3, "name": "Accounting Software", "section": "SOFTWARE", "section_display": "Software", 
                 "unit": "license", "price": 25000.0, "hsn": "8523", "description": "Financial Accounting"},
            ],
            "GENERAL": [
                {"id": 4, "name": "Office Chair", "section": "GENERAL", "section_display": "General", 
                 "unit": "pcs", "price": 5000.0, "hsn": "9401", "description": "Ergonomic Chair"},
            ]
        }
    
    return items_by_section


def get_lead_form_context(existing_firms, active_leads_data, active_users):
    """Helper function to get lead form context"""
    import logging
    from django.utils import timezone
    logger = logging.getLogger(__name__)
    
    # Initialize if None
    if existing_firms is None:
        existing_firms = []
    if active_leads_data is None:
        active_leads_data = []
    if active_users is None:
        active_users = []
    
    context = {}
    
    try:
        # ✅ FIXED: Districts - try app5 first, then app1 as fallback
        districts_loaded = False
        districts_qs = None
        try:
            from app5.models import District
            districts_qs = District.objects.all().order_by('name')
            districts_loaded = True
            logger.info(f"✅ Using districts from app5.models")
        except Exception as e1:
            logger.debug(f"Could not load districts from app5.models: {e1}")
            try:
                from app1.models import District
                districts_qs = District.objects.all().order_by('name')
                districts_loaded = True
                logger.info(f"✅ Using districts from app1.models")
            except Exception as e2:
                logger.debug(f"Could not load districts from app1.models: {e2}")
        
        if districts_loaded and districts_qs:
            context['districts'] = [
                {
                    'id': district.id,
                    'name': district.name,
                    'state': getattr(district, 'state', '') if hasattr(district, 'state') else ''
                } 
                for district in districts_qs
            ]
            logger.info(f"✅ Loaded {len(context['districts'])} districts")
        else:
            context['districts'] = []
    except Exception as e:
        logger.error(f"Error loading districts: {e}")
        context['districts'] = []

    try:
        # States
        from app5.models import StateMaster
        states_qs = StateMaster.objects.all().order_by('name')
        context['states'] = [
            {
                'id': state.id,
                'name': state.name,
                'code': getattr(state, 'code', '') if hasattr(state, 'code') else ''
            }
            for state in states_qs
        ]
        logger.info(f"✅ Loaded {len(context['states'])} states")
    except Exception as e:
        logger.debug(f"Could not load states: {e}")
        context['states'] = []

    try:
        # Departments
        from purchase_order.models import Department
        context['departments'] = Department.objects.filter(is_active=True).order_by('name')
        logger.info(f"✅ Loaded {context['departments'].count()} departments")
    except Exception as e:
        logger.debug(f"Could not load departments: {e}")
        context['departments'] = []

    try:
        # Business Natures
        from app5.models import BusinessNature
        context['business_natures'] = BusinessNature.objects.all().order_by('name')
        logger.info(f"✅ Loaded {context['business_natures'].count()} business natures")
    except Exception as e:
        logger.debug(f"Could not load business natures: {e}")
        context['business_natures'] = []

    try:
        # References
        from app5.models import Reference
        context['references'] = Reference.objects.all().order_by('ref_name')
        logger.info(f"✅ Loaded {context['references'].count()} references")
    except Exception as e:
        logger.debug(f"Could not load references: {e}")
        context['references'] = []

    try:
        # ✅ FIXED: Campaigns with proper formatting
        from campaign.models import Campaigning
        campaigns = Campaigning.objects.filter(is_deleted=False).order_by('-campaign_unique_id')[:100]
        
        # Format campaigns for dropdown
        formatted_campaigns = []
        for campaign in campaigns:
            display_name = f"{campaign.campaign_unique_id} - {campaign.campaign_name}"
            if campaign.software_name:
                display_name += f" ({campaign.software_name})"
            if campaign.status:
                display_name += f" [{campaign.status.title()}]"
            
            formatted_campaigns.append({
                'id': campaign.id,
                'campaign_unique_id': campaign.campaign_unique_id,
                'campaign_name': campaign.campaign_name,
                'display_name': display_name,
                'software_name': campaign.software_name or '',
                'status': campaign.status or '',
            })
        
        context['campaigns'] = formatted_campaigns
        context['campaigns_raw'] = campaigns  # Keep raw queryset if needed
        
        # Calculate campaign counts
        context['active_campaigns_count'] = campaigns.filter(status='active').count()
        context['completed_campaigns_count'] = campaigns.filter(status='completed').count()
        context['draft_campaigns_count'] = campaigns.filter(status='draft').count()
        
        logger.info(f"✅ Loaded {len(formatted_campaigns)} campaigns")
        logger.info(f"✅ Active: {context['active_campaigns_count']}, Completed: {context['completed_campaigns_count']}, Draft: {context['draft_campaigns_count']}")
        
    except Exception as e:
        logger.debug(f"Could not load campaigns: {e}")
        context['campaigns'] = []
        context['campaigns_raw'] = []
        context['active_campaigns_count'] = 0
        context['completed_campaigns_count'] = 0
        context['draft_campaigns_count'] = 0

    # Pass other data
    context['existing_firms'] = existing_firms
    context['active_leads_data'] = active_leads_data
    context['active_users'] = active_users
    context['today'] = timezone.now().date()
    
    # ✅ FLAT LIST OF ALL ITEMS
    try:
        from purchase_order.models import Item as POItem
        all_items = POItem.objects.filter(is_active=True).order_by('name')
        context['items'] = all_items
        logger.info(f"✅ Loaded {all_items.count()} items for template")
    except Exception as e:
        logger.warning(f"Could not load all items: {e}")
        context['items'] = []
    
    return context


@login_required
def lead_creation_view(request):
    """
    Show Lead Creation Form with active leads listed in directory (left column)
    """
    from .models import Lead, District, BusinessNature, StateMaster
    from purchase_order.models import Department
    from app1.models import User
    import logging
    
    logger = logging.getLogger(__name__)

    # ✅ GET CURRENT USER
    current_user = None
    if request.session.get('custom_user_id'):
        try:
            current_user = User.objects.get(id=request.session['custom_user_id'])
        except User.DoesNotExist:
            logger.warning(f"User with ID {request.session['custom_user_id']} not found")
    elif request.user and request.user.is_authenticated:
        current_user = request.user

    # ✅ GET FILTERED ACTIVE LEADS
    active_leads_qs = Lead.objects.filter(status__iexact='Active')
    
    if current_user:
        active_leads_qs = get_user_filtered_leads(current_user, active_leads_qs)
        logger.info(f"User {current_user.name}: Showing {active_leads_qs.count()} filtered leads")
    else:
        active_leads_qs = active_leads_qs.none()
        logger.warning("No current user - showing no leads")
    
    active_leads_data = active_leads_qs.order_by('-created_at')[:25]

    context = {
        'districts': District.objects.all().order_by('name'),
        'states': StateMaster.objects.all().order_by('name'),
        'business_natures': BusinessNature.objects.all().order_by('name'),
        'active_users': User.objects.filter(status='active').order_by('name'),
        'departments': Department.objects.filter(is_active=True).order_by('name'),
        'active_leads_data': active_leads_data,
    }
    return render(request, 'lead_form.html', context)






# -----------------------
# Lead report view
# -----------------------
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone
import datetime

# UPDATED lead_report_view function with user-based filtering
# Replace the existing lead_report_view function in your views.py with this code

def lead_report_view(request):
    LeadModel = Lead
    
    # ============================================================
    # USER-BASED FILTERING - CRITICAL SECTION
    # ============================================================
    # Get the current user from session
    current_user = None
    current_user_name = None
    
    if request.session.get('custom_user_id'):
        try:
            from app1.models import User
            current_user = User.objects.get(id=request.session['custom_user_id'])
            current_user_name = getattr(current_user, "name", current_user.username if hasattr(current_user, 'username') else str(current_user))
        except User.DoesNotExist:
            pass
    
    # Start with all leads
    leads_qs = LeadModel.objects.all().order_by("-created_at") if hasattr(LeadModel, "created_at") else LeadModel.objects.all()
    
    # Apply user-level filtering
    if current_user:
        user_level = getattr(current_user, 'user_level', None)
        
        # User levels that see ALL leads:
        # - 'normal' (Admin)
        # - 'admin_level' (Super Admin)
        # - '4level' (Superuser)
        admin_levels = ['normal', 'admin_level', '4level']
        
        # Regular user levels that see ONLY their own leads:
        # - '3level' (User)
        # - '5level' (Branch User)
        # - Any other level not in admin_levels
        
        if user_level not in admin_levels:
            # Filter to show only leads created by this user OR assigned to this user
            from django.db.models import Q
            leads_qs = leads_qs.filter(
                Q(created_by=current_user) | 
                Q(assigned_to_name=current_user_name) |
                Q(marketedBy=current_user_name)
            )
    # ============================================================
    # END USER-BASED FILTERING
    # ============================================================

    # Get filter parameters
    status_filter = request.GET.get('status', '').strip()
    campaign_filter = request.GET.get('campaign', '').strip()
    branch_filter = request.GET.get('branch', '').strip()
    search_query = request.GET.get('search', '').strip()
    start_date = request.GET.get('start_date', '').strip()
    end_date = request.GET.get('end_date', '').strip()
    row_count = request.GET.get('row_count', '10').strip()
    
    # ---------------- FILTERS ----------------
    if status_filter:
        leads_qs = leads_qs.filter(status=status_filter)

    # Campaign Filter
    if campaign_filter:
        # Campaign is stored as text field (campaign_unique_id), not FK
        if hasattr(LeadModel, 'campaign'):
            leads_qs = leads_qs.filter(campaign=campaign_filter)

    # Branch Filter (stored in requirement field)
    if branch_filter:
        # Branch name is stored in requirement field as text
        if hasattr(LeadModel, 'requirement'):
            leads_qs = leads_qs.filter(requirement__icontains=branch_filter)

    if search_query:
        from django.db.models import Q
        leads_qs = leads_qs.filter(
            Q(ownerName__icontains=search_query) |
            Q(phoneNo__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(ticket_number__icontains=search_query) |
            Q(name__icontains=search_query) |
            Q(firstName__icontains=search_query) |
            Q(lastName__icontains=search_query) |
            Q(place__icontains=search_query) |
            Q(individualPlace__icontains=search_query) |
            Q(refFrom__icontains=search_query)
        )

    if start_date:
        try:
            s = timezone.datetime.strptime(start_date, "%Y-%m-%d").date()
            leads_qs = leads_qs.filter(created_at__date__gte=s)
        except ValueError:
            pass

    if end_date:
        try:
            e = timezone.datetime.strptime(end_date, "%Y-%m-%d").date()
            leads_qs = leads_qs.filter(created_at__date__lte=e)
        except ValueError:
            pass

    # ---------------- COUNTS ----------------
    # NOTE: Counts are based on the filtered queryset (user's own leads for regular users)
    if current_user and getattr(current_user, 'user_level', None) not in ['normal', 'admin_level', '4level']:
        # For regular users, show counts from their filtered leads only
        from django.db.models import Q
        user_leads = LeadModel.objects.filter(
            Q(created_by=current_user) | 
            Q(assigned_to_name=current_user_name) |
            Q(marketedBy=current_user_name)
        )
        total_leads = user_leads.count()
        active_leads = user_leads.filter(status="Active").count()
        inactive_leads = user_leads.filter(status="Inactive").count()
        installed_leads = user_leads.filter(status="Installed").count()
        business_leads = user_leads.filter(customerType="Business").count()
        individual_leads = user_leads.filter(customerType="Individual").count()
        today_leads = user_leads.filter(created_at__date=timezone.now().date()).count()
    else:
        # For admin users, show all leads counts
        total_leads = LeadModel.objects.count()
        active_leads = LeadModel.objects.filter(status="Active").count()
        inactive_leads = LeadModel.objects.filter(status="Inactive").count()
        installed_leads = LeadModel.objects.filter(status="Installed").count()
        business_leads = LeadModel.objects.filter(customerType="Business").count()
        individual_leads = LeadModel.objects.filter(customerType="Individual").count()
        today_leads = LeadModel.objects.filter(created_at__date=timezone.now().date()).count()

    filtered_count = leads_qs.count()
    has_filters = bool(status_filter or campaign_filter or branch_filter or 
                       search_query or start_date or end_date)

    # ---------------- GET CAMPAIGNS AND BRANCHES FOR DROPDOWNS ----------------
    campaigns = []
    branches = []
    current_campaign_name = ""
    current_branch_name = ""
    
    # Try to get campaigns from Campaigning model
    try:
        from campaign.models import Campaigning
        # FIXED: Filter non-deleted campaigns and order by most recent
        campaigns = Campaigning.objects.filter(
            is_deleted=False
        ).order_by('-created_at')  # Most recent first
        
        # Get the current campaign name for display
        if campaign_filter:
            try:
                campaign_obj = Campaigning.objects.filter(
                    campaign_unique_id=campaign_filter,
                    is_deleted=False
                ).first()
                if campaign_obj:
                    current_campaign_name = campaign_obj.campaign_name
                else:
                    current_campaign_name = campaign_filter  # Show the ID if campaign not found
            except (ValueError, TypeError):
                current_campaign_name = campaign_filter
    except ImportError:
        campaigns = []
        if campaign_filter:
            current_campaign_name = campaign_filter
    
    # Try to get branches from Department model (branches are stored in requirement field)
    try:
        from purchase_order.models import Department
        branches = Department.objects.all().order_by('name')
        
        if branch_filter:
            try:
                branch_obj = Department.objects.get(id=int(branch_filter))
                current_branch_name = branch_obj.name
            except (Department.DoesNotExist, ValueError, TypeError):
                current_branch_name = branch_filter
    except ImportError:
        branches = []
        if branch_filter:
            current_branch_name = branch_filter

    # ---------------- AUTO-SET TODAY'S DATE FILTER ----------------
    auto_set_today = False
    if not start_date and not end_date:
        auto_set_today = True
        today = timezone.now().date()
        start_date = today.strftime("%Y-%m-%d")
        end_date = today.strftime("%Y-%m-%d")
        
        leads_qs = leads_qs.filter(created_at__date=today)
        filtered_count = leads_qs.count()

    # ---------------- CREATE CAMPAIGN MAPPING FOR ENRICHMENT ----------------
    campaign_map = {}
    try:
        from campaign.models import Campaigning
        for camp in Campaigning.objects.filter(is_deleted=False):
            campaign_map[camp.campaign_unique_id] = {
                'name': camp.campaign_name,
                'id': camp.campaign_unique_id,
                'status': camp.status
            }
    except Exception as e:
        # If Campaigning model doesn't exist or error occurs
        print(f"Error creating campaign map: {e}")
        campaign_map = {}

    # ---------------- PAGINATION WITH ROW COUNT ----------------
    if row_count == 'all':
        # Show all rows without pagination
        leads = leads_qs
        paginator = None
        per_page = None
    else:
        try:
            per_page = int(row_count)
            if per_page <= 0:
                per_page = 10
        except ValueError:
            per_page = 10
        
        paginator = Paginator(leads_qs, per_page)
        page_number = request.GET.get("page")
        leads = paginator.get_page(page_number)

    # ---------------- ENRICH LEADS WITH CAMPAIGN AND BRANCH NAMES ----------------
    # IMPORTANT: Do this AFTER pagination to ensure we enrich the actual displayed leads
    for lead in leads:
        # Add campaign display name
        if hasattr(lead, 'campaign') and lead.campaign:
            campaign_info = campaign_map.get(lead.campaign)
            if campaign_info:
                lead.campaign_display_name = campaign_info['name']
                lead.campaign_status = campaign_info.get('status', '')
            else:
                # Campaign might be deleted or doesn't exist
                lead.campaign_display_name = lead.campaign
                lead.campaign_status = ''
        else:
            lead.campaign_display_name = None
            lead.campaign_status = ''
        
        # Add branch display name
        if hasattr(lead, 'requirement') and lead.requirement:
            lead.branch_display_name = lead.requirement
        else:
            lead.branch_display_name = None

    # ---------------- CONTEXT ----------------
    context = {
        "leads": leads,
        "total_leads": total_leads,
        "active_leads": active_leads,
        "inactive_leads": inactive_leads,
        "installed_leads": installed_leads,
        "business_leads": business_leads,
        "individual_leads": individual_leads,
        "today_leads": today_leads,
        "filtered_count": filtered_count,
        "has_filters": has_filters,
        
        # Filter values for display
        "current_status_filter": status_filter,
        "current_campaign_filter": campaign_filter,
        "current_branch_filter": branch_filter,
        "current_campaign_name": current_campaign_name,
        "current_branch_name": current_branch_name,
        "current_search_query": search_query,
        "current_start_date": start_date if not auto_set_today else '',
        "current_end_date": end_date if not auto_set_today else '',
        "current_row_count": row_count if row_count != 'all' else 'all',
        "auto_set_today": auto_set_today,
        
        # Dropdown data - CRITICAL: These must be present for the template
        "campaigns": campaigns,  # Contains all non-deleted campaigns
        "branches": branches,
        
        # Pagination info
        "paginator": paginator,
        
        # User info for debugging (optional)
        "current_user_name": current_user_name,
        "is_admin": current_user and getattr(current_user, 'user_level', None) in ['normal', 'admin_level', '4level'],
    }

    return render(request, "lead_report.html", context)





# -----------------------
# Lead detail API
# -----------------------
def lead_detail_api(request, lead_id):
    lead = get_object_or_404(Lead, id=lead_id)
    return JsonResponse({
        "id": lead.id,
        "ticket_number": getattr(lead, "ticket_number", None),
        "owner_name": lead.ownerName,
        "phone_number": lead.phoneNo,
        "email": lead.email,
        "customer_type": lead.customerType,
        "firm_name": lead.name,
        "first_name": lead.firstName,
        "last_name": lead.lastName,
        "business_address": lead.address,
        "individual_address": lead.individualAddress,
        "place": lead.place,
        "individual_place": lead.individualPlace,
        "district": getattr(lead, "District", None),
        "individual_district": lead.individualDistrict,
        "state": getattr(lead, "State", None),
        "individual_state": lead.individualState,
        "pin_code": lead.pinCode,
        "individual_pin_code": lead.individualPinCode,
        "status": lead.status,
        "reference_from": lead.refFrom,
        "business_nature": lead.business,
        "marketed_by": lead.marketedBy,
        "consultant": lead.Consultant,
        "branch": lead.requirement,
        "notes": lead.details,
        "requirementsJson": json.dumps(requirements),
        "date": lead.date.strftime('%Y-%m-%d') if getattr(lead, "date", None) else None,
        "created_at": lead.created_at.strftime('%Y-%m-%d %H:%M:%S') if getattr(lead, "created_at", None) else None,
        "updated_at": lead.updated_at.strftime('%Y-%m-%d %H:%M:%S') if getattr(lead, "updated_at", None) else None
    })


# -----------------------
# Lead edit (view + save)
# -----------------------

import requests
import json
from django.conf import settings
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

def lead_edit(request, lead_id):
    """
    View to edit a specific lead with user-level based access control.
    - Regular users (3level/5level) can only edit leads created by or assigned to them
    - Admin users (normal/admin_level/4level) can edit any lead
    - Superusers can edit any lead
    """
    
    # ========== USER AUTHENTICATION & ACCESS CONTROL ==========
    current_user = None
    
    # Determine current user and check permissions
    if request.user.is_superuser:
        # Superuser can edit any lead
        current_user = User.objects.filter(user_level='admin_level').first()
        lead = get_object_or_404(Lead, id=lead_id)
        logger.info(f"Superuser accessing lead {lead_id}")
        
    elif request.session.get('custom_user_id'):
        # Get the custom user from session
        current_user = User.objects.get(id=request.session['custom_user_id'])
        
        # CRITICAL: Check if user has permission to edit this lead
        if current_user.user_level in ['3level', '5level']:
            # Regular users can ONLY edit leads created by them or assigned to them
            from django.db.models import Q
            
            # First check if the lead exists at all
            try:
                lead_exists = Lead.objects.get(id=lead_id)
                logger.info(f"Lead {lead_id} exists. created_by: {lead_exists.created_by}, assigned_to_name: {lead_exists.assigned_to_name}")
                logger.info(f"Current user: {current_user.name} (ID: {current_user.id}), Level: {current_user.user_level}")
            except Lead.DoesNotExist:
                logger.error(f"Lead {lead_id} does not exist in database")
                messages.error(request, f"Lead #{lead_id} not found.")
                return redirect('app5:lead_report')
            
            # Build filter condition
            user_condition = Q(created_by=current_user)
            
            # Also check if assigned to them by name
            if current_user.name:
                user_condition |= Q(assigned_to_name__iexact=current_user.name)
                logger.info(f"Checking if lead is assigned to: {current_user.name}")
            
            # Try to get the lead with permission check
            try:
                lead = Lead.objects.get(user_condition, id=lead_id)
                logger.info(f"✅ User {current_user.name} granted access to lead {lead_id}")
            except Lead.DoesNotExist:
                # Lead exists but user doesn't have permission
                logger.warning(f"❌ User {current_user.name} (ID: {current_user.id}) denied access to lead {lead_id}")
                logger.warning(f"   Lead created_by_id: {lead_exists.created_by_id}, assigned_to_name: '{lead_exists.assigned_to_name}'")
                
                messages.error(
                    request, 
                    f"You don't have permission to access this lead. "
                    f"This lead is not created by you or assigned to you."
                )
                return redirect('app5:lead_report')
        else:
            # Admin users can edit any lead
            lead = get_object_or_404(Lead, id=lead_id)
            logger.info(f"Admin user {current_user.name} accessing lead {lead_id}")
    else:
        # No user logged in, redirect to login
        messages.error(request, "Please log in to access this page.")
        return redirect('login')
    
    # ========== GET QUOTATION FOR THIS LEAD ==========
    quotation = None
    try:
        quotation = Quotation.objects.filter(lead=lead).first()
    except Exception as e:
        logger.error(f"Error getting quotation for lead {lead_id}: {e}")
        quotation = None
    
    # ========== API INTEGRATION (existing code) ==========
    API_URL = "https://accmaster.imcbs.com/api/sync/rrc-clients/"
    api_customer_data = []
    api_data_count = 0
    
    try:
        headers = {'Content-Type': 'application/json'}
        response = requests.get(API_URL, headers=headers, timeout=10)
        
        if response.status_code == 200:
            api_data = response.json()
            
            if isinstance(api_data, list):
                api_customer_data = api_data
            elif isinstance(api_data, dict) and 'data' in api_data:
                api_customer_data = api_data['data']
            elif isinstance(api_data, dict) and 'clients' in api_data:
                api_customer_data = api_data['clients']
            else:
                api_customer_data = [api_data] if api_data else []
            
            api_data_count = len(api_customer_data)
            logger.info(f"Successfully fetched {api_data_count} customers from API")
        else:
            logger.error(f"API request failed with status {response.status_code}")
            messages.warning(request, f"Could not fetch customer data from API (Status: {response.status_code})")
            
    except Exception as e:
        logger.error(f"Error connecting to API: {e}")
        messages.warning(request, "Unable to connect to customer database API")
    
    # Standardize API data structure (existing code)
    standardized_api_data = []
    for customer in api_customer_data:
        standardized_customer = {
            'code': str(customer.get('code', customer.get('client_code', customer.get('id', '')))),
            'name': customer.get('name', customer.get('client_name', customer.get('firm_name', ''))),
            'address': customer.get('address', customer.get('address1', '')),
            'address3': customer.get('address3', customer.get('address2', customer.get('location', ''))),
            'branch': customer.get('branch', customer.get('branch_name', '')),
            'district': customer.get('district', customer.get('district_name', '')),
            'state': customer.get('state', customer.get('state_name', '')),
            'mobile': customer.get('mobile', customer.get('phone', customer.get('contact_no', ''))),
            'software': customer.get('software', customer.get('software_name', customer.get('product', ''))),
            'nature': customer.get('nature', customer.get('business_nature', customer.get('industry', ''))),
            'rout': customer.get('rout', customer.get('route', '')),
            'installationdate': customer.get('installationdate', customer.get('install_date', customer.get('created_at', '')))
        }
        standardized_api_data.append(standardized_customer)
    
    # ========== POST REQUEST HANDLING ==========
    if request.method == 'POST':
        # Update lead fields
        lead.ownerName = request.POST.get('ownerName')
        lead.phoneNo = request.POST.get('phoneNo')
        lead.email = request.POST.get('email')
        lead.customerType = 'Business' if request.POST.get('customerTypeToggle') else 'Individual'
        lead.status = request.POST.get('status', 'Active')
        lead.priority = request.POST.get('priority', 'Medium')
        lead.refFrom = request.POST.get('refFrom')
        lead.business = request.POST.get('business')
        
        # ========== FIXED: Handle marketedBy as NAME ==========
        marketed_by_value = request.POST.get('marketedBy')
        if marketed_by_value:
            # Store the name directly
            lead.marketedBy = marketed_by_value.strip()
            # Also store the user ID if we can find it
            try:
                user = User.objects.filter(name=marketed_by_value.strip()).first()
                if user:
                    lead.marketed_by_user = user
            except (AttributeError, Exception) as e:
                logger.debug(f"No user found for name '{marketed_by_value}': {e}")
        else:
            lead.marketedBy = None
            lead.marketed_by_user = None
            
        lead.Consultant = request.POST.get('Consultant')
        
        # ========== FIXED: Handle requirement as NAME ==========
        requirement_value = request.POST.get('requirement')
        if requirement_value:
            # Store the branch name directly
            lead.requirement = requirement_value.strip()
            # Also store the department ID if we can find it
            try:
                department = Department.objects.filter(name=requirement_value.strip()).first()
                if department:
                    lead.department = department
            except (AttributeError, Exception) as e:
                logger.debug(f"No department found for name '{requirement_value}': {e}")
        else:
            lead.requirement = None
            lead.department = None
            
        lead.details = request.POST.get('details')
        lead.date = request.POST.get('date') or lead.date
        
        # Handle campaign field
        campaign_value = request.POST.get('campaign') or request.POST.get('Campaign')
        if hasattr(lead, 'campaign'):
            lead.campaign = campaign_value
        elif hasattr(lead, 'Campaign'):
            lead.Campaign = campaign_value

        # Update customer type specific fields
        if lead.customerType == 'Business':
            lead.name = request.POST.get('name')
            lead.address = request.POST.get('address')
            lead.place = request.POST.get('place')
            lead.District = request.POST.get('District')
            lead.State = request.POST.get('State')
            lead.pinCode = request.POST.get('pinCode')
            # Clear individual fields
            lead.firstName = None
            lead.lastName = None
            lead.individualAddress = None
            lead.individualPlace = None
            lead.individualDistrict = None
            lead.individualState = None
            lead.individualPinCode = None
        else:
            lead.firstName = request.POST.get('firstName')
            lead.lastName = request.POST.get('lastName')
            lead.individualAddress = request.POST.get('individualAddress')
            lead.individualPlace = request.POST.get('individualPlace')
            lead.individualDistrict = request.POST.get('individualDistrict')
            lead.individualState = request.POST.get('individualState')
            lead.individualPinCode = request.POST.get('individualPinCode')
            # Clear business fields
            lead.name = None
            lead.address = None
            lead.place = None
            lead.District = None
            lead.State = None
            lead.pinCode = None

        lead.save()
        
        # ========== SAVE REQUIREMENT ITEMS ==========
        try:
            # Get requirement data from form
            requirement_details_json = request.POST.get('requirement_details', '[]')
            
            logger.info(f"📦 Requirement details JSON: {requirement_details_json}")
            
            try:
                requirements_list = json.loads(requirement_details_json) if requirement_details_json else []
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error: {e}")
                requirements_list = []
            
            if requirements_list:
                logger.info(f"Processing {len(requirements_list)} requirement items for lead {lead.id}")
                
                # Import Item model
                try:
                    from purchase_order.models import Item as POItem
                    ItemModel = POItem
                except ImportError:
                    from .models import Item as App5Item
                    ItemModel = App5Item
                
                # Get existing requirement IDs
                existing_requirement_ids = set()
                for req_data in requirements_list:
                    req_id = req_data.get('id')
                    if req_id and str(req_id).isdigit():
                        existing_requirement_ids.add(int(req_id))
                
                # Delete requirements not in the new list
                if existing_requirement_ids:
                    lead.requirements.exclude(id__in=existing_requirement_ids).delete()
                else:
                    # If no requirement IDs, delete all existing
                    lead.requirements.all().delete()
                
                logger.info(f"Cleaned up old requirements for lead {lead.id}")
                
                # Save each requirement item
                saved_count = 0
                for req_data in requirements_list:
                    try:
                        item_id = req_data.get('item_id')
                        if not item_id:
                            continue
                        
                        # Get the Item
                        item = ItemModel.objects.filter(id=item_id).first()
                        if not item:
                            logger.warning(f"Item with ID {item_id} not found")
                            continue
                        
                        # Parse values
                        try:
                            price = float(req_data.get('price', 0))
                        except (ValueError, TypeError):
                            price = 0.00
                        
                        try:
                            quantity = int(req_data.get('quantity', 1))
                        except (ValueError, TypeError):
                            quantity = 1
                        
                        section = req_data.get('section', 'GENERAL')
                        if not section:
                            section = getattr(item, 'section', 'GENERAL')
                        
                        unit = req_data.get('unit', 'pcs')
                        if not unit:
                            unit = getattr(item, 'unit_of_measure', 'pcs')
                        
                        total = price * quantity
                        
                        # Update or create requirement item
                        req_id = req_data.get('id')
                        if req_id and str(req_id).isdigit():
                            # Update existing
                            req, created = RequirementItem.objects.update_or_create(
                                id=int(req_id),
                                defaults={
                                    'lead': lead,
                                    'item': item,
                                    'item_name': item.name,
                                    'section': section,
                                    'unit': unit,
                                    'price': price,
                                    'quantity': quantity,
                                    'total': total,
                                    'owner_name': lead.ownerName,
                                    'phone_no': lead.phoneNo,
                                    'email': lead.email,
                                    'ticket_number': lead.ticket_number
                                }
                            )
                            logger.info(f"{'Created' if created else 'Updated'} requirement {req.id}")
                        else:
                            # Create new
                            req = RequirementItem.objects.create(
                                lead=lead,
                                item=item,
                                item_name=item.name,
                                section=section,
                                unit=unit,
                                price=price,
                                quantity=quantity,
                                total=total,
                                owner_name=lead.ownerName,
                                phone_no=lead.phoneNo,
                                email=lead.email,
                                ticket_number=lead.ticket_number
                            )
                            logger.info(f"✅ Created new requirement {req.id}")
                        
                        saved_count += 1
                        
                    except Exception as e:
                        logger.error(f"Error saving requirement item: {str(e)}", exc_info=True)
                        continue
                
                if saved_count > 0:
                    logger.info(f"✅ Successfully saved {saved_count} requirement items")
                    messages.success(request, f"Lead and {saved_count} requirement item(s) saved successfully! Ticket: {lead.ticket_number}")
                else:
                    messages.success(request, f"Lead updated successfully! Ticket: {lead.ticket_number}")
            else:
                logger.info("No requirement items to save")
                messages.success(request, f"Lead updated successfully! Ticket: {lead.ticket_number}")
        
        except Exception as e:
            logger.error(f"Error processing requirements: {e}", exc_info=True)
            messages.success(request, f"Lead updated but error saving requirements. Ticket: {lead.ticket_number}")
        
        return redirect('app5:lead_report')

    # ========== GET REQUEST - PREPARE DISPLAY DATA ==========
    
    # Get dropdown options
    business_natures = BusinessNature.objects.all().order_by('name') if BusinessNature is not None else []
    states = StateMaster.objects.all().order_by('name') if StateMaster is not None else []
    districts = District.objects.all().order_by('name') if District is not None else []

    # Get active users
    try:
        user_fields = [f.name for f in User._meta.get_fields()]
        
        if 'status' in user_fields:
            active_users = User.objects.filter(status='active').order_by('name')
        elif 'is_active' in user_fields:
            active_users = User.objects.filter(is_active=True).order_by('name')
        else:
            active_users = User.objects.all().order_by('name')
            
    except Exception as e:
        logger.error(f"Error loading users: {e}")
        active_users = []

    departments = Department.objects.filter(is_active=True).order_by('name') if Department is not None else []
    
    # Get campaigns
    try:
        from campaign.models import Campaigning
        campaigns = Campaigning.objects.filter(is_deleted=False).order_by('-campaign_id')
    except:
        campaigns = []
    
    # Get references
    try:
        from .models import Reference
        references = Reference.objects.all().order_by('ref_name')
    except:
        references = []
    
    # ========== FILTER ACTIVE LEADS BY USER LEVEL ==========
    # Regular users only see leads created by them or assigned to them in the directory
    # Admin users see all leads
    if current_user and current_user.user_level in ['3level', '5level']:
        # Regular users: Only leads created by them or assigned to them
        from django.db.models import Q
        
        user_filter = Q(created_by=current_user)
        
        # Also include leads assigned to them by name
        if current_user.name:
            user_filter |= Q(assigned_to_name__iexact=current_user.name)
        
        active_leads_queryset = Lead.objects.filter(
            user_filter,
            status='Active'
        )
        logger.info(f"Regular user {current_user.name} can see {active_leads_queryset.count()} active leads")
    else:
        # Admin users and superusers: All leads
        active_leads_queryset = Lead.objects.filter(status='Active')
        logger.info(f"Admin user can see {active_leads_queryset.count()} active leads")
    
    active_leads_data = active_leads_queryset.order_by('-created_at')[:50]

    # ========== GET CURRENT SELECTED VALUES FOR DROPDOWNS ==========
    
    # Get current marketedBy value (could be ID or name)
    marketed_by_selected_value = None
    if lead.marketedBy:
        # First check if it's a numeric ID
        try:
            if lead.marketedBy.isdigit():
                user = User.objects.filter(id=int(lead.marketedBy)).first()
                if user:
                    marketed_by_selected_value = user.name
                else:
                    marketed_by_selected_value = lead.marketedBy
            else:
                # It's already a name
                marketed_by_selected_value = lead.marketedBy
        except:
            marketed_by_selected_value = lead.marketedBy
    
    # Get current requirement value (could be ID or name)
    requirement_selected_value = None
    if lead.requirement:
        # First check if it's a numeric ID
        try:
            if lead.requirement.isdigit():
                department = Department.objects.filter(id=int(lead.requirement)).first()
                if department:
                    requirement_selected_value = department.name
                else:
                    requirement_selected_value = lead.requirement
            else:
                # It's already a name
                requirement_selected_value = lead.requirement
        except:
            requirement_selected_value = lead.requirement

    # Get campaign name
    campaign_display = None
    if hasattr(lead, 'campaign') and lead.campaign:
        campaign_display = lead.campaign
    elif hasattr(lead, 'Campaign') and lead.Campaign:
        campaign_display = lead.Campaign

    # ========== ✅ FIX: PROPERLY FORMAT REQUIREMENTS DATA ==========
    requirements_data = []
    requirements_json = "[]"
    
    try:
        # Get all requirements for this lead
        requirements = lead.requirements.all().order_by('created_at')
        
        logger.info(f"📦 Found {requirements.count()} requirements for lead {lead_id}")
        
        # ✅ GET ITEM MODEL
        try:
            from purchase_order.models import Item as POItem
            ItemModel = POItem
        except ImportError:
            from .models import Item as App5Item
            ItemModel = App5Item
        
        for req in requirements:
            # ✅ GET ACTUAL ITEM FROM DATABASE TO GET CURRENT PRICE & UNIT
            item_price = float(req.price) if req.price is not None else 0.00
            item_unit = req.unit or 'pcs'
            
            # If we have an item reference, get its current details
            if req.item:
                try:
                    current_item = ItemModel.objects.get(id=req.item.id)
                    # Use saved price/unit, but have current item data available
                    if item_price == 0.00 and hasattr(current_item, 'mrp'):
                        item_price = float(current_item.mrp or 0)
                    if not item_unit and hasattr(current_item, 'unit_of_measure'):
                        item_unit = current_item.unit_of_measure or 'pcs'
                except ItemModel.DoesNotExist:
                    logger.warning(f"Item {req.item.id} not found")
            
            # Calculate total
            quantity_val = int(req.quantity) if req.quantity is not None else 1
            total_val = item_price * quantity_val
            
            req_dict = {
                'id': req.id,
                'item_id': req.item.id if req.item else None,
                'item_name': req.item_name or '',
                'section': req.section or 'GENERAL',
                'unit': item_unit,
                'price': item_price,
                'quantity': quantity_val,
                'total': total_val,
            }
            
            requirements_data.append(req_dict)
            
            logger.debug(f"  Item: {req.item_name}, Unit: {item_unit}, Price: ₹{item_price}, Qty: {quantity_val}, Total: ₹{total_val}")
        
        # Convert to JSON
        requirements_json = json.dumps(requirements_data, cls=DjangoJSONEncoder)
        
        logger.info(f"✅ Successfully prepared {len(requirements_data)} requirements for template")
    
    except Exception as e:
        logger.error(f"❌ Error preparing requirements data: {e}", exc_info=True)
        requirements_data = []
        requirements_json = "[]"

    # Prepare lead_data dictionary
    lead_data = {
        'id': lead.id,
        'ownerName': lead.ownerName,
        'phoneNo': lead.phoneNo,
        'email': lead.email,
        'customerType': lead.customerType,
        'status': lead.status,
        'priority': lead.priority,
        'refFrom': lead.refFrom,
        'business': lead.business,
        'Consultant': lead.Consultant,
        'details': lead.details,
        'date': lead.date,
        'ticket_number': getattr(lead, 'ticket_number', lead.id),
        
        # Business fields
        'name': lead.name,
        'address': lead.address,
        'place': lead.place,
        'District': lead.District,
        'State': lead.State,
        'pinCode': lead.pinCode,
        
        # Individual fields
        'firstName': lead.firstName,
        'lastName': lead.lastName,
        'individualAddress': lead.individualAddress,
        'individualPlace': lead.individualPlace,
        'individualDistrict': lead.individualDistrict,
        'individualState': lead.individualState,
        'individualPinCode': lead.individualPinCode,
        
        # ========== FIXED: Use resolved names for form values ==========
        'marketedBy': marketed_by_selected_value or '',  # User name for form value
        'marketed_by_name': marketed_by_selected_value or '',  # For display
        'requirement': requirement_selected_value or '',  # Department name for form value
        'branch_name': requirement_selected_value or '',  # For display
        'campaign': campaign_display or '',  # For form value
        'campaign_display': campaign_display or '',  # For display
        
        # ✅ ADD REQUIREMENTS
        'requirement_ids': ','.join([str(r['id']) for r in requirements_data if r.get('id')]),
        'requirement_details_json': requirements_json,
    }
    
    # Get existing firms
    existing_firms = Lead.objects.filter(
        customerType='Business'
    ).exclude(
        name__isnull=True
    ).exclude(
        name=''
    ).values_list(
        'name', flat=True
    ).distinct()

    # Get items grouped by section
    items_by_section = {}
    try:
        from purchase_order.models import Item as POItem
        all_items = POItem.objects.filter(is_active=True).order_by('section', 'name')
        
        for item in all_items:
            section = item.section if item.section else 'GENERAL'
            if section not in items_by_section:
                items_by_section[section] = []
            items_by_section[section].append(item)
            
        logger.info(f"✅ Loaded {all_items.count()} items in {len(items_by_section)} sections")
    except Exception as e:
        logger.error(f"Error loading items: {e}")
        items_by_section = {}

    # ========== PREPARE CONTEXT ==========
    context = {
        'lead_data': lead_data,
        'lead': lead,
        'quotation': quotation,
        'business_natures': business_natures,
        'states': states,
        'districts': districts,
        'active_users': active_users,
        'departments': departments,
        'campaigns': campaigns,
        'references': references,
        'active_leads_data': active_leads_data,
        'marketed_by_name': marketed_by_selected_value,
        'branch_name': requirement_selected_value,
        'campaign_name': campaign_display,
        'today': timezone.now().date(),
        'existing_firms': existing_firms,
        'api_customer_data': standardized_api_data,
        'api_data_count': api_data_count,
        'items_by_section': items_by_section,
        'requirements_data': requirements_data,
        'current_user': current_user,  # Add current user to context
    }
    
    return render(request, "lead_form_edit.html", context)


from django.shortcuts import get_object_or_404, redirect
from django.http import JsonResponse, HttpResponseNotAllowed
from django.contrib import messages
from django.views.decorators.http import require_POST
from .models import Lead  # adjust if your model name or import path differs
import logging

logger = logging.getLogger(__name__)

@require_POST
def lead_delete(request, lead_id):
    """
    Delete a Lead by ID and all associated RequirementItems.
    Works for both normal form POST and AJAX (fetch/XHR) requests.
    """
    try:
        logger.debug("Delete request received for lead ID: %s", lead_id)
        lead = get_object_or_404(Lead, id=lead_id)
        ticket_number = getattr(lead, "ticket_number", str(lead.id))
        owner_name = lead.ownerName
        
        # 🔥 USE ATOMIC TRANSACTION TO ENSURE COMPLETE DELETION
        with transaction.atomic():
            # ✅ DELETE ALL ASSOCIATED REQUIREMENTS FIRST
            # Method 1: Delete by foreign key relationship
            deleted_by_fk = RequirementItem.objects.filter(lead=lead).delete()
            logger.info(f"Deleted {deleted_by_fk[0]} requirements via FK relationship")
            
            # Method 2: Delete by ticket_number (backup cleanup)
            deleted_by_ticket = RequirementItem.objects.filter(
                ticket_number=ticket_number
            ).delete()
            logger.info(f"Deleted {deleted_by_ticket[0]} requirements via ticket_number")
            
            # Method 3: Delete by owner name and phone (final cleanup for orphaned records)
            deleted_by_contact = RequirementItem.objects.filter(
                owner_name=owner_name,
                phone_no=lead.phoneNo
            ).delete()
            logger.info(f"Deleted {deleted_by_contact[0]} requirements via contact info")
            
            # ✅ NOW DELETE THE LEAD
            lead.delete()
            logger.info("Lead %s (ID %s) deleted successfully", ticket_number, lead_id)
        
        # Calculate total requirements deleted
        total_requirements_deleted = (
            deleted_by_fk[0] + 
            deleted_by_ticket[0] + 
            deleted_by_contact[0]
        )

        success_message = f"✅ Lead {ticket_number} deleted successfully!"
        if total_requirements_deleted > 0:
            success_message += f" ({total_requirements_deleted} requirement(s) also removed)"
        
        messages.success(request, success_message)

        # If AJAX, return JSON
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                "success": True, 
                "message": success_message,
                "requirements_deleted": total_requirements_deleted
            })

        # Fallback for normal POST
        return redirect('app5:lead_report')

    except Exception as e:
        logger.exception("Error deleting lead ID %s: %s", lead_id, e)
        
        error_message = f"Error deleting lead: {str(e)}"
        
        # AJAX -> JSON error
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({"success": False, "error": error_message}, status=500)

        # Non-AJAX fallback
        messages.error(request, error_message)
        return redirect('app5:lead_report')



# --- Top-level imports for app5/views.py (one place only) ---
from django.apps import apps
from django.shortcuts import render, redirect, get_object_or_404, reverse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import transaction
import logging

logger = logging.getLogger(__name__)
User = get_user_model()


# --- lead list view (safe select_related) ---
@login_required
def lead_assign_list_view(request):
    """
    Robust list view for lead assignments.
    - Uses select_related only when assigned_to/assigned_by are real FK fields.
    - Never accesses attributes without a safe check to avoid AttributeError.
    - Adds `display_assigned_to` and `display_assigned_by` attributes to each lead
      for the template to use (works for FK or string/snapshot fields).
    """
    LeadModel = apps.get_model('app5', 'Lead')

    # Detect many-to-one FK names on the model (safe at runtime)
    fk_names = {f.name for f in LeadModel._meta.get_fields() if getattr(f, "many_to_one", False)}
    related_fields = [name for name in ("assigned_to", "assigned_by") if name in fk_names]

    try:
        if related_fields:
            leads_qs = LeadModel.objects.select_related(*related_fields).all().order_by("-id")
        else:
            leads_qs = LeadModel.objects.all().order_by("-id")
    except Exception as e:
        logger.warning("lead_assign_list_view - queryset exception: %s", e)
        leads_qs = LeadModel.objects.all().order_by("-id")

    # build safe display names for template
    def _user_display_from_obj(u):
        """Return best display name for a user-like object (fk instance)."""
        if not u:
            return None
        # try get_full_name()
        try:
            if hasattr(u, "get_full_name"):
                full = u.get_full_name()
                if full and full.strip():
                    return full.strip()
        except Exception:
            pass
        # try first+last
        first = getattr(u, "first_name", "") or ""
        last = getattr(u, "last_name", "") or ""
        if (first or last):
            name = (first + " " + last).strip()
            if name:
                return name
        # fallback to other common fields
        return getattr(u, "name", None) or getattr(u, "username", None) or getattr(u, "email", None) or None

    safe_leads = []
    for lead in leads_qs:
        # Assigned To (try FK object first, then snapshot fields)
        assigned_to_display = None
        if hasattr(lead, "assigned_to"):
            try:
                at_obj = getattr(lead, "assigned_to", None)
                assigned_to_display = _user_display_from_obj(at_obj)
            except Exception:
                assigned_to_display = None

        if not assigned_to_display:
            # fallback snapshot/string fields you might have on the model
            assigned_to_display = (
                getattr(lead, "assigned_to_name", None) or
                getattr(lead, "assigned_to_str", None) or
                getattr(lead, "assigned_to_username", None) or
                None
            )

        # Assigned By (try FK object first, then snapshot fields)
        assigned_by_display = None
        if hasattr(lead, "assigned_by"):
            try:
                ab_obj = getattr(lead, "assigned_by", None)
                assigned_by_display = _user_display_from_obj(ab_obj)
            except Exception:
                assigned_by_display = None

        if not assigned_by_display:
            assigned_by_display = (
                getattr(lead, "assigned_by_name", None) or
                getattr(lead, "assigned_by_str", None) or
                None
            )

        # Final fallbacks
        if not assigned_to_display:
            assigned_to_display = "Not Assigned"
        if not assigned_by_display:
            assigned_by_display = "System"

        # Attach to object for template usage
        # (we can attach new attributes to the instance safely at runtime)
        setattr(lead, "display_assigned_to", assigned_to_display)
        setattr(lead, "display_assigned_by", assigned_by_display)

        safe_leads.append(lead)

    context = {"leads": safe_leads}
    return render(request, "lead_assign_list.html", context)




# --- assign view ---
@login_required
def assign_lead_view(request):
    """
    GET: show assignment form (unassigned leads + users)
    POST: assign selected lead to selected user and save snapshot names (if model has fields).
    Defensive: uses apps.get_model, checks for fields before setting, and wraps save in a transaction.
    """
    # Resolve models dynamically to avoid circular imports
    LeadModel = apps.get_model('app5', 'Lead')
    try:
        UserModel = apps.get_model('app1', 'User')
    except Exception:
        # fallback: try to import directly (if configured differently)
        try:
            from app1.models import User as UserModel  # type: ignore
        except Exception:
            UserModel = None

    def _display_name(u):
        """Return a readable display name for a user object."""
        if not u:
            return "Unknown"
        try:
            # prefer custom model's name, then get_full_name, then username/email
            if hasattr(u, 'name') and getattr(u, 'name'):
                return getattr(u, 'name')
            if hasattr(u, 'get_full_name'):
                full = u.get_full_name()
                if full:
                    return full
        except Exception:
            pass
        first = getattr(u, 'first_name', '') or ''
        last = getattr(u, 'last_name', '') or ''
        if first or last:
            return (first + ' ' + last).strip()
        return getattr(u, 'username', None) or getattr(u, 'email', None) or f'User #{getattr(u, "id", "?" )}'

    # --------------------
    # GET: render form
    # --------------------
    if request.method == "GET":
        # Find unassigned leads - IMPROVED FILTERING LOGIC
        unassigned_leads = LeadModel.objects.none()
        
        try:
            # Order preference: created_at, id
            order_by_created = '-created_at' if hasattr(LeadModel, 'created_at') else '-id'

            # STRATEGY 1: Check for FK assignment fields (most reliable)
            fk_assignment_fields = ['assigned_to', 'user', 'assigned_user', 'assigned']
            for fld in fk_assignment_fields:
                if hasattr(LeadModel, fld):
                    # Check if field exists and is a ForeignKey or similar
                    field = LeadModel._meta.get_field(fld)
                    if getattr(field, 'is_relation', False):
                        unassigned_leads = LeadModel.objects.filter(**{f"{fld}__isnull": True})
                        logger.info(f"Found unassigned leads using FK field '{fld}': {unassigned_leads.count()}")
                        break

            # STRATEGY 2: If no FK fields found, check string/snapshot fields
            if not unassigned_leads.exists():
                string_assignment_fields = ['assigned_to_str', 'assigned_to_name', 'assigned_user_name']
                for fld in string_assignment_fields:
                    if hasattr(LeadModel, fld):
                        unassigned_leads = LeadModel.objects.filter(
                            models.Q(**{f"{fld}__isnull": True}) | 
                            models.Q(**{f"{fld}": ""}) |
                            models.Q(**{f"{fld}__iexact": "not assigned"}) |
                            models.Q(**{f"{fld}__iexact": "unassigned"})
                        )
                        if unassigned_leads.exists():
                            logger.info(f"Found unassigned leads using string field '{fld}': {unassigned_leads.count()}")
                            break

            # STRATEGY 3: Check status field for unassigned status
            if not unassigned_leads.exists() and hasattr(LeadModel, 'status'):
                unassigned_leads = LeadModel.objects.filter(
                    models.Q(status__isnull=True) |
                    models.Q(status='') |
                    models.Q(status__iexact='unassigned') |
                    models.Q(status__iexact='new') |
                    models.Q(status__iexact='pending')
                )
                if unassigned_leads.exists():
                    logger.info(f"Found unassigned leads using status field: {unassigned_leads.count()}")

            # STRATEGY 4: Check assignment_type field
            if not unassigned_leads.exists() and hasattr(LeadModel, 'assignment_type'):
                unassigned_leads = LeadModel.objects.filter(
                    models.Q(assignment_type__isnull=True) |
                    models.Q(assignment_type='') |
                    models.Q(assignment_type__iexact='unassigned')
                )
                if unassigned_leads.exists():
                    logger.info(f"Found unassigned leads using assignment_type: {unassigned_leads.count()}")

            # FINAL FALLBACK: If still no results, show recent leads with debug info
            if not unassigned_leads.exists():
                all_leads = LeadModel.objects.all().order_by(order_by_created)[:50]
                logger.warning(f"No unassigned leads found with standard filters. Showing {all_leads.count()} recent leads for debugging.")
                
                # Debug: log field information for first few leads
                for i, lead in enumerate(all_leads[:5]):
                    logger.debug(f"Lead {i+1}: ID={lead.id}, Ticket={getattr(lead, 'ticket_number', 'N/A')}")
                    logger.debug(f"  - assigned_to: {getattr(lead, 'assigned_to', 'N/A')}")
                    logger.debug(f"  - assigned_to_name: {getattr(lead, 'assigned_to_name', 'N/A')}")
                    logger.debug(f"  - status: {getattr(lead, 'status', 'N/A')}")
                    logger.debug(f"  - assignment_type: {getattr(lead, 'assignment_type', 'N/A')}")
                
                unassigned_leads = all_leads

            # Apply ordering
            unassigned_leads = unassigned_leads.order_by(order_by_created)

        except Exception as e:
            logger.error(f"Error filtering unassigned leads: {e}", exc_info=True)
            try:
                unassigned_leads = LeadModel.objects.all().order_by('-id')[:50]
            except Exception:
                unassigned_leads = LeadModel.objects.all() if hasattr(LeadModel, 'objects') else []

        # Users â€” try to use your custom User model and sensible filters
        try:
            if UserModel is not None:
                # try common active/status fields
                if hasattr(UserModel, 'status'):
                    users = UserModel.objects.filter(status='active').order_by('name')
                elif hasattr(UserModel, 'is_active'):
                    users = UserModel.objects.filter(is_active=True).order_by('name')
                else:
                    users = UserModel.objects.all().order_by('name')
            else:
                users = []
        except Exception as e:
            logger.warning("Could not fetch users from app1.User: %s", e)
            # fallback to any model named User in installed apps (Django's)
            from django.contrib.auth import get_user_model
            AuthUser = get_user_model()
            try:
                users = AuthUser.objects.filter(is_active=True).order_by('username')
            except Exception:
                users = AuthUser.objects.all().order_by('id')

        # Final debug logging
        logger.info(f"Final unassigned leads count: {unassigned_leads.count()}")
        logger.info(f"Available users count: {len(users)}")

        return render(request, "lead_assign_form.html", {
            "unassigned_leads": unassigned_leads, 
            "users": users
        })

    # --------------------
    # POST: perform assignment
    # --------------------
    if request.method == "POST":
        lead_identifier = (
            request.POST.get("lead_id")
            or request.POST.get("lead")
            or request.POST.get("lead_pk")
            or request.POST.get("ticket_no")
            or request.POST.get("ticket")
        )
        assigned_to_id = request.POST.get("assigned_to") or request.POST.get("user")

        if not lead_identifier:
            messages.error(request, "Please select a lead.")
            return redirect(reverse('app5:assign_lead'))

        # Resolve lead: try PK first (if numeric), else ticket_number when available
        lead = None
        try:
            if str(lead_identifier).isdigit():
                lead = get_object_or_404(LeadModel, pk=int(lead_identifier))
            else:
                # attempt ticket_number fallback
                if hasattr(LeadModel, 'ticket_number'):
                    lead = get_object_or_404(LeadModel, ticket_number=lead_identifier)
                else:
                    lead = get_object_or_404(LeadModel, pk=lead_identifier)
        except Exception as e:
            messages.error(request, f"Selected lead not found: {e}")
            return redirect(reverse('app5:assign_lead'))

        # Check if lead is already assigned (prevent reassignment through URL manipulation)
        if hasattr(lead, 'assigned_to') and getattr(lead, 'assigned_to') is not None:
            messages.warning(request, f"This lead is already assigned to {_display_name(getattr(lead, 'assigned_to'))}.")
            return redirect(reverse('app5:assign_lead'))
        
        if hasattr(lead, 'assigned_to_name') and getattr(lead, 'assigned_to_name'):
            messages.warning(request, f"This lead is already assigned to {getattr(lead, 'assigned_to_name')}.")
            return redirect(reverse('app5:assign_lead'))

        if not assigned_to_id:
            messages.error(request, "Please select a user to assign.")
            return redirect(reverse('app5:assign_lead'))

        # Resolve assigned user using custom User model if possible, else Django user
        assigned_user = None
        try:
            if UserModel is not None:
                # try numeric pk
                if str(assigned_to_id).isdigit():
                    assigned_user = UserModel.objects.filter(pk=int(assigned_to_id)).first()
                else:
                    # try userid / username / email
                    lookup = { 'userid': assigned_to_id } if hasattr(UserModel, 'userid') else { 'username': assigned_to_id }
                    assigned_user = UserModel.objects.filter(**lookup).first()
            # fallback to Django auth user
            if not assigned_user:
                from django.contrib.auth import get_user_model
                AuthUser = get_user_model()
                if str(assigned_to_id).isdigit():
                    assigned_user = AuthUser.objects.filter(pk=int(assigned_to_id)).first()
                else:
                    assigned_user = AuthUser.objects.filter(username=assigned_to_id).first()
        except Exception as e:
            logger.exception("Error resolving assigned user: %s", e)
            messages.error(request, f"Selected user not found: {e}")
            return redirect(reverse('app5:assign_lead'))

        if not assigned_user:
            messages.error(request, "Selected user not found.")
            return redirect(reverse('app5:assign_lead'))

        now = timezone.now()

        # Try to resolve an appropriate 'assigned_by' object from your custom User model if possible
        assigned_by_obj = None
        try:
            if UserModel is not None and request.user and getattr(request.user, 'is_authenticated', False):
                # prefer matching by userid == request.user.username if present
                if hasattr(UserModel, 'userid'):
                    assigned_by_obj = UserModel.objects.filter(userid=request.user.username).first()
                # else try by username
                if not assigned_by_obj and hasattr(UserModel, 'username'):
                    assigned_by_obj = UserModel.objects.filter(username=request.user.username).first()
        except Exception:
            assigned_by_obj = None

        # Start atomic transaction to avoid partial saves
        try:
            with transaction.atomic():
                # Attempt to set FK fields if present (try several possible fk-names)
                fk_field_set = False
                for fk_field in ('assigned_to', 'user', 'assigned_user', 'assigned'):
                    if hasattr(lead, fk_field):
                        try:
                            setattr(lead, fk_field, assigned_user)
                            fk_field_set = True
                            logger.info(f"Set FK field '{fk_field}' to user {assigned_user.id}")
                        except Exception as e:
                            logger.debug("Could not set %s FK: %s", fk_field, e)

                # Attempt to set assigned_by FK (if model has)
                for by_field in ('assigned_by', 'assigned_by_user', 'assigned_by_id'):
                    if hasattr(lead, by_field):
                        try:
                            # prefer assigned_by_obj (custom User), else use request.user if it's compatible
                            if assigned_by_obj:
                                setattr(lead, by_field, assigned_by_obj)
                            else:
                                setattr(lead, by_field, request.user)
                            logger.info(f"Set assigned_by field '{by_field}'")
                        except Exception as e:
                            logger.debug("Could not set %s FK: %s", by_field, e)

                # Also write snapshot name/string fields if they exist (safer for audit)
                try:
                    if hasattr(lead, "assigned_to_name"):
                        lead.assigned_to_name = _display_name(assigned_user)
                        logger.info(f"Set assigned_to_name to '{_display_name(assigned_user)}'")
                except Exception as e:
                    logger.debug("Could not set assigned_to_name: %s", e)

                try:
                    if hasattr(lead, "assigned_to_str"):
                        lead.assigned_to_str = _display_name(assigned_user)
                except Exception as e:
                    logger.debug("Could not set assigned_to_str: %s", e)

                try:
                    if hasattr(lead, "assigned_by_name"):
                        lead.assigned_by_name = _display_name(assigned_by_obj or request.user)
                except Exception as e:
                    logger.debug("Could not set assigned_by_name: %s", e)

                # set assigned date/time fields if they exist (try date then datetime)
                if hasattr(lead, 'assigned_date'):
                    try:
                        # if assigned_date is a DateField, set date()
                        field_val = now.date()
                        setattr(lead, 'assigned_date', field_val)
                    except Exception:
                        try:
                            setattr(lead, 'assigned_date', now)
                        except Exception as e2:
                            logger.debug("Could not set assigned_date: %s", e2)

                if hasattr(lead, 'assigned_time'):
                    try:
                        setattr(lead, 'assigned_time', now.time())
                    except Exception as e:
                        logger.debug("Could not set assigned_time: %s", e)

                # âœ… FIXED: Only update assignment_type, NOT the main status
                # This keeps the lead status as "Active" even after assignment
                if hasattr(lead, 'assignment_type'):
                    try:
                        lead.assignment_type = 'assigned'
                    except Exception as e:
                        logger.debug("Could not update assignment_type field: %s", e)

                # âœ… STATUS REMAINS UNCHANGED - No code here to modify lead.status

                # Save the lead
                lead.save()
                logger.info(f"Successfully assigned lead {getattr(lead, 'ticket_number', lead.id)} to {_display_name(assigned_user)}")
                
        except Exception as e:
            logger.exception("Error while assigning lead: %s", e)
            messages.error(request, f"Failed to assign lead: {e}")
            return redirect(reverse('app5:assign_lead'))

        # Success message: prefer ticket_number if available
        lead_label = getattr(lead, 'ticket_number', None) or getattr(lead, 'firm_name', None) or getattr(lead, 'id', None)
        messages.success(request, f"Lead #{lead_label} assigned to {_display_name(assigned_user)}.")
        return redirect(reverse('app5:lead_assign_list'))


# ------- edit lead view -------
@login_required
def edit_lead_view(request, lead_id):
    """
    Edit an existing lead assignment.
    """
    LeadModel = apps.get_model('app5', 'Lead')

    # load lead (support either numeric id or ticket number)
    try:
        if str(lead_id).isdigit():
            lead = get_object_or_404(LeadModel, id=int(lead_id))
        else:
            if hasattr(LeadModel, 'ticket_number'):
                lead = get_object_or_404(LeadModel, ticket_number=lead_id)
            else:
                lead = get_object_or_404(LeadModel, id=lead_id)
    except Exception as e:
        messages.error(request, f"Lead not found: {e}")
        return redirect('app5:lead_assign_list')

    logger.debug("Editing lead %s - %s", lead_id, getattr(lead, 'ticket_number', lead.pk))

    # Build users list for template
    users_qs = User.objects.filter(is_active=True).order_by('id')
    users = []

    for u in users_qs:
        # Safe way to get display name
        display_name = getattr(u, 'name', None)
        if not display_name:
            display_name = getattr(u, 'full_name', None)
        if not display_name and hasattr(u, 'get_full_name'):
            display_name = u.get_full_name()
        if not display_name:
            display_name = getattr(u, 'email', 'Unknown User')

        users.append({'id': u.id, 'name': display_name})
        logger.debug("Available user for edit - ID: %s, Name: %s", u.id, display_name)

    if request.method == 'POST':
        assign_to_id = request.POST.get('assign_to') or request.POST.get('assigned_to') or request.POST.get('user')
        logger.debug("Edit form - assign_to_id: %s", assign_to_id)

        if not assign_to_id:
            messages.error(request, "Please select a user to assign.")
            return redirect('app5:edit_lead', lead_id=lead_id)

        try:
            assigned_to_user = User.objects.get(id=int(assign_to_id))
            user_name = getattr(assigned_to_user, 'name', f'User {assigned_to_user.id}')
            logger.debug("Edit - Found user: ID %s, Name: %s", assigned_to_user.id, user_name)
        except (User.DoesNotExist, ValueError) as e:
            logger.debug("Edit - User lookup failed: %s", e)
            messages.error(request, "Selected assignee not found or inactive.")
            return redirect('app5:edit_lead', lead_id=lead_id)

        # assigned_by: try session custom_user_id else request.user
        assigned_by_user = None
        custom_user_id = request.session.get('custom_user_id')
        if custom_user_id:
            try:
                assigned_by_user = User.objects.get(id=int(custom_user_id))
            except (User.DoesNotExist, ValueError):
                assigned_by_user = None

        try:
            # Use the User instance directly if model supports it
            try:
                lead.assigned_to = assigned_to_user
            except Exception:
                pass

            try:
                lead.assigned_by = assigned_by_user or request.user
            except Exception:
                pass

            now = timezone.now()
            if hasattr(lead, 'assigned_date'):
                try:
                    lead.assigned_date = now.date()
                except Exception:
                    lead.assigned_date = now
            if hasattr(lead, 'assigned_time'):
                try:
                    lead.assigned_time = now.time()
                except Exception:
                    pass
            if hasattr(lead, 'status'):
                lead.status = 'assigned'
            if hasattr(lead, 'assignment_type'):
                lead.assignment_type = 'assigned'

            # Also set snapshot name fields if present
            if hasattr(lead, "assigned_to_name"):
                lead.assigned_to_name = getattr(assigned_to_user, 'name', str(assigned_to_user.pk))
            if hasattr(lead, "assigned_by_name"):
                lead.assigned_by_name = getattr(assigned_by_user or request.user, 'name', str((assigned_by_user or request.user).pk))

            lead.save()
            logger.debug("Lead edit successful")
            messages.success(request, "Lead assignment updated successfully!")
            return redirect('app5:lead_assign_list')
        except Exception as e:
            logger.exception("Error updating lead assignment: %s", e)
            messages.error(request, f"Error updating lead assignment: {str(e)}")
            return redirect('app5:edit_lead', lead_id=lead_id)

    context = {'users': users, 'lead': lead}
    # Render the same lead_assign_form but now with context for editing
    return render(request, 'lead_assign_form.html', context)


# ------- delete lead view -------
@login_required
def delete_lead_view(request, lead_id):
    """View to delete a lead assignment - handles both POST and GET"""
    LeadModel = apps.get_model('app5', 'Lead')
    try:
        # support numeric pk or ticket_number
        if str(lead_id).isdigit():
            lead = get_object_or_404(LeadModel, id=int(lead_id))
        else:
            if hasattr(LeadModel, 'ticket_number'):
                lead = get_object_or_404(LeadModel, ticket_number=lead_id)
            else:
                lead = get_object_or_404(LeadModel, id=lead_id)

        ticket_number = getattr(lead, 'ticket_number', lead.pk)
        customer_name = getattr(lead, 'ownerName', getattr(lead, 'customer', 'Unknown'))
        lead.delete()

        messages.success(request, f'Lead assignment {ticket_number} for {customer_name} deleted successfully!')
        return redirect('app5:lead_assign_list')

    except Exception as e:
        logger.exception("Error deleting lead: %s", e)
        messages.error(request, f'Error deleting lead: {str(e)}')
        return redirect('app5:lead_assign_list')


def lead_assign_edit(request, lead_id):
    """
    Edit lead assignment - matches the URL name used in template
    """
    LeadModel = apps.get_model('app5', 'Lead')
    
    # Load lead
    try:
        if str(lead_id).isdigit():
            lead = get_object_or_404(LeadModel, id=int(lead_id))
        else:
            if hasattr(LeadModel, 'ticket_number'):
                lead = get_object_or_404(LeadModel, ticket_number=lead_id)
            else:
                lead = get_object_or_404(LeadModel, id=lead_id)
    except Exception as e:
        messages.error(request, f"Lead not found: {e}")
        return redirect('app5:lead_assign_list')

    # Get active users for dropdown
    try:
        from app1.models import User as AppUser
        users = AppUser.objects.filter(status='active').order_by('name')
    except Exception:
        from django.contrib.auth import get_user_model
        UserModel = get_user_model()
        users = UserModel.objects.filter(is_active=True).order_by('username')

    if request.method == 'POST':
        assigned_to_id = request.POST.get('assigned_to')
        status = request.POST.get('status', 'assigned')
        
        if not assigned_to_id:
            messages.error(request, "Please select a user to assign.")
            return redirect('app5:lead_assign_edit', lead_id=lead_id)

        try:
            # Get the user to assign
            assigned_user = users.get(id=int(assigned_to_id))
            
            # Update lead assignment
            lead.assigned_to = assigned_user
            lead.assigned_to_name = getattr(assigned_user, 'name', 
                                          getattr(assigned_user, 'username', 
                                                  f'User {assigned_user.id}'))
            
            # Set assigned_by to current user
            if request.session.get('custom_user_id'):
                try:
                    current_user = users.get(id=request.session['custom_user_id'])
                    lead.assigned_by = current_user
                    lead.assigned_by_name = getattr(current_user, 'name', 
                                                  getattr(current_user, 'username', 
                                                          f'User {current_user.id}'))
                except Exception:
                    pass
            
            # Update dates
            now = timezone.now()
            lead.assigned_date = now.date()
            lead.assigned_time = now.time()
            
            # Update status if provided
            if status:
                lead.status = status
            
            lead.save()
            
            messages.success(request, f"Lead assignment updated successfully!")
            return redirect('app5:lead_assign_list')
            
        except Exception as e:
            logger.error(f"Error updating lead assignment: {e}")
            messages.error(request, f"Error updating assignment: {str(e)}")
            return redirect('app5:lead_assign_edit', lead_id=lead_id)

    # GET request - show edit form
    context = {
        'lead': lead,
        'users': users,
    }
    return render(request, 'lead_assign_edit.html', context)


def lead_detail(request, lead_id):
    lead = get_object_or_404(Lead, id=lead_id)

    data = {
        "id": lead.id,
        "customer_name": lead.customer_name,
        "phone_number": lead.phone_number,
        "email": lead.email,
        "address": lead.address,
        "district": lead.district,
        "state": lead.state,
        "business_type": lead.business_type,
        "company_name": lead.company_name,
        "gst_number": lead.gst_number,
    }

    return JsonResponse({"success": True, "data": data})




    









from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.serializers.json import DjangoJSONEncoder
from .models import Lead, RequirementItem, Item  # Make sure to import Item here
import json
def requirement_form(request):
    """Handle requirement form - both GET (display) and POST (save)"""
    import logging
    logger = logging.getLogger(__name__)
    
    # POST request - save the form
    if request.method == 'POST':
        try:
            # Get form data
            owner_name = request.POST.get('owner_name', '').strip()
            phone_no = request.POST.get('phone_no', '').strip()
            ticket_number = request.POST.get('ticket_number', '').strip()
            priority = request.POST.get('priority', 'Medium').strip()
            status = request.POST.get('status', 'Active').strip()
            email = request.POST.get('email', '').strip()
            company = request.POST.get('company', '').strip()
            place = request.POST.get('place', '').strip()
            requirement_ids_str = request.POST.get('requirement_ids', '').strip()
            
            logger.info(f"🔥 Processing requirement form")
            logger.info(f"  - Owner: {owner_name}")
            logger.info(f"  - Phone: {phone_no}")
            logger.info(f"  - Ticket: {ticket_number}")
            logger.info(f"  - Priority: {priority}")
            logger.info(f"  - Status: {status}")
            
            # 🔥 CRITICAL VALIDATION
            if not owner_name:
                messages.error(request, '❌ Owner name is required')
                return redirect('app5:requirement_list')
            
            if not phone_no:
                messages.error(request, '❌ Phone number is required')
                return redirect('app5:requirement_list')
            
            if not ticket_number:
                messages.error(request, '❌ Ticket number is required. Please select a lead from the directory.')
                return redirect('app5:requirement_list')
            
            # Get sections and items data
            sections = request.POST.getlist('section[]')
            item_ids = request.POST.getlist('item_id[]')
            units = request.POST.getlist('unit[]')
            prices = request.POST.getlist('price[]')
            quantities = request.POST.getlist('qty[]')
            
            logger.info(f"📦 Form data - Items: {len(item_ids)}, Sections: {len(sections)}")
            
            # Validate we have items
            if not item_ids or not any(item_ids):
                messages.error(request, '❌ No items selected. Please add at least one item.')
                return redirect('app5:requirement_list')
            
            # ✅ Determine which Item model to use
            try:
                from purchase_order.models import Item as POItem
                ItemModel = POItem
                logger.info("Using purchase_order.Item model")
            except ImportError:
                from .models import Item as App5Item
                ItemModel = App5Item
                logger.info("Using app5.Item model")
            
            # Process existing requirement IDs
            existing_req_ids = []
            if requirement_ids_str:
                existing_req_ids = [rid.strip() for rid in requirement_ids_str.split(',') if rid.strip()]
            
            logger.info(f"Existing requirement IDs: {existing_req_ids}")
            
            # Process each requirement item
            requirement_items = []
            errors = []
            
            for i in range(len(item_ids)):
                if not item_ids[i]:  # Skip empty items
                    continue
                
                try:
                    # Get the Item
                    item = ItemModel.objects.filter(id=item_ids[i]).first()
                    if not item:
                        error_msg = f'Item with ID {item_ids[i]} not found'
                        logger.error(error_msg)
                        errors.append(error_msg)
                        continue
                    
                    # Get section safely
                    section_value = sections[i] if i < len(sections) else 'GENERAL'
                    if not section_value:
                        section_value = getattr(item, 'section', 'GENERAL')
                    
                    # Calculate total
                    try:
                        price = float(prices[i]) if i < len(prices) and prices[i] else 0.00
                    except (ValueError, TypeError):
                        price = 0.00
                    
                    try:
                        quantity = int(quantities[i]) if i < len(quantities) and quantities[i] else 1
                    except (ValueError, TypeError):
                        quantity = 1
                    
                    total = price * quantity
                    unit = units[i] if i < len(units) else getattr(item, 'unit_of_measure', 'pcs')
                    
                    logger.info(f"  Item {i+1}: {item.name}, Price: {price}, Qty: {quantity}, Total: {total}")
                    
                    # 🔥 CREATE OR UPDATE REQUIREMENT ITEM
                    if i < len(existing_req_ids) and existing_req_ids[i]:
                        # Update existing
                        try:
                            requirement_item = RequirementItem.objects.get(id=existing_req_ids[i])
                            requirement_item.item_name = item.name
                            requirement_item.owner_name = owner_name
                            requirement_item.phone_no = phone_no
                            requirement_item.ticket_number = ticket_number  # 🔥 ENSURE THIS IS SET
                            requirement_item.section = section_value
                            requirement_item.unit = unit
                            requirement_item.price = price
                            requirement_item.quantity = quantity
                            requirement_item.total = total
                            requirement_item.email = email
                            requirement_item.save()
                            logger.info(f"✅ Updated requirement {requirement_item.id}")
                        except RequirementItem.DoesNotExist:
                            # Create new if doesn't exist
                            requirement_item = RequirementItem.objects.create(
                                item_name=item.name,
                                owner_name=owner_name,
                                phone_no=phone_no,
                                ticket_number=ticket_number,  # 🔥 CRITICAL FIELD
                                section=section_value,
                                unit=unit,
                                price=price,
                                quantity=quantity,
                                total=total,
                                email=email
                            )
                            logger.info(f"✅ Created new requirement {requirement_item.id} (ID not found)")
                    else:
                        # Create new requirement item
                        requirement_item = RequirementItem.objects.create(
                            item_name=item.name,
                            owner_name=owner_name,
                            phone_no=phone_no,
                            ticket_number=ticket_number,  # 🔥 CRITICAL FIELD
                            section=section_value,
                            unit=unit,
                            price=price,
                            quantity=quantity,
                            total=total,
                            email=email
                        )
                        logger.info(f"✅ Created new requirement {requirement_item.id}")
                    
                    requirement_items.append(requirement_item)
                    
                except Exception as e:
                    error_msg = f'Error saving item {i+1}: {str(e)}'
                    logger.error(error_msg, exc_info=True)
                    errors.append(error_msg)
                    continue
            
            # 🔥 UPDATE LEAD IF EXISTS
            try:
                lead = Lead.objects.filter(ticket_number=ticket_number).first()
                if lead:
                    # Update lead with latest info
                    if priority:
                        lead.priority = priority
                    if status:
                        lead.status = status
                    lead.save()
                    logger.info(f"✅ Updated lead {ticket_number} - Priority: {priority}, Status: {status}")
            except Exception as e:
                logger.warning(f"Could not update lead: {e}")
            
            # Show results
            if requirement_items:
                messages.success(request, f'✅ Successfully saved {len(requirement_items)} requirement item(s) for Ticket #{ticket_number}')
            
            if errors:
                for error in errors:
                    messages.error(request, error)
            
            if not requirement_items:
                messages.error(request, '❌ No requirement items were saved')
            
            return redirect('app5:requirement_list')
            
        except Exception as e:
            logger.error(f"❌ Error saving requirements: {e}", exc_info=True)
            messages.error(request, f'Error saving requirements: {str(e)}')
            return redirect('app5:requirement_list')
    
    # GET request - redirect to requirement_list
    else:
        return redirect('app5:requirement_list')




            # Add this to your app5/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Sum
import json
import logging

logger = logging.getLogger(__name__)

def edit_requirement(request, lead_id):
    """
    Display requirement edit page for a specific lead
    Load existing requirements and allow editing
    """
    try:
        # Get the lead
        lead = get_object_or_404(Lead, id=lead_id)
        
        # Get phone number - try different possible field names
        phone_value = getattr(lead, 'phoneNo', None) or getattr(lead, 'phone_no', None) or getattr(lead, 'phone', None) or getattr(lead, 'phone_number', None) or "-"
        
        # Get owner name
        owner_name = getattr(lead, 'ownerName', None) or getattr(lead, 'owner_name', None) or getattr(lead, 'firstName', None) or getattr(lead, 'name', None) or "Unknown"
        
        # Get ticket number
        ticket_number = getattr(lead, 'ticket_number', None) or getattr(lead, 'ticketNumber', None) or getattr(lead, 'ticket', None) or "-"
        
        logger.info(f"📝 Loading edit page for Lead: {ticket_number} - {owner_name}")
        
        # Get existing requirements for this lead
        requirements = RequirementItem.objects.filter(ticket_number=ticket_number).order_by('created_at')
        
        requirements_count = requirements.count()
        logger.info(f"Found {requirements_count} existing requirements")
        
        # ===== GET ACTIVE LEADS FOR DIRECTORY =====
        # Fetch all leads (you might want to filter by status or date)
        # Since there's no is_active field, fetch all leads and limit to recent ones
        active_leads = Lead.objects.all().order_by('-created_at', '-date')[:50]
        
        # If you have a status field, you can filter like:
        # active_leads = Lead.objects.filter(status__in=['Active', 'Follow Up']).order_by('-created_at')[:50]
        
        # Enhance each lead with requirements count
        for lead_item in active_leads:
            # Get ticket number for this lead
            lead_ticket = getattr(lead_item, 'ticket_number', None) or getattr(lead_item, 'ticketNumber', None) or getattr(lead_item, 'ticket', None)
            
            if lead_ticket:
                lead_item.requirements_count = RequirementItem.objects.filter(
                    ticket_number=lead_ticket
                ).count()
            else:
                lead_item.requirements_count = 0
            
            # Ensure all required attributes exist
            if not hasattr(lead_item, 'ownerName'):
                lead_item.ownerName = getattr(lead_item, 'owner_name', None) or getattr(lead_item, 'firstName', None) or getattr(lead_item, 'name', None) or "Unknown"
            
            if not hasattr(lead_item, 'phoneNo'):
                lead_item.phoneNo = getattr(lead_item, 'phone_no', None) or getattr(lead_item, 'phone', None) or getattr(lead_item, 'phone_number', None) or ""
            
            if not hasattr(lead_item, 'priority'):
                lead_item.priority = getattr(lead_item, 'priority', 'Medium')
            
            if not hasattr(lead_item, 'status'):
                lead_item.status = getattr(lead_item, 'status', 'Active')
            
            if not hasattr(lead_item, 'company'):
                lead_item.company = getattr(lead_item, 'company', '') or getattr(lead_item, 'business', '')
            
            if not hasattr(lead_item, 'place'):
                lead_item.place = getattr(lead_item, 'place', '') or getattr(lead_item, 'District', '') or getattr(lead_item, 'State', '')
        
        # Get active users for employee directory
        try:
            from django.contrib.auth.models import User
            active_users = User.objects.filter(is_active=True).order_by('username')[:20]
        except:
            active_users = []
        
        # Calculate section summary
        section_summary = {}
        for req in requirements:
            section = req.section or 'GENERAL'
            section_summary[section] = section_summary.get(section, 0) + 1
        
        # Get items
        try:
            from purchase_order.models import Item as POItem
            items = POItem.objects.filter(is_active=True).order_by('section', 'name')
            logger.info("✅ Using purchase_order.Item model")
        except ImportError:
            from .models import Item as App5Item
            items = App5Item.objects.all().order_by('name')
            logger.info("✅ Using app5.Item model")
        
        # Prepare requirements data
        requirements_data = []
        for req in requirements:
            # Find matching item
            item_id = None
            item_name = req.item_name or ''
            
            if item_name and items.exists():
                try:
                    matching_item = items.filter(name__iexact=item_name).first()
                    if not matching_item:
                        matching_item = items.filter(name__icontains=item_name).first()
                    if matching_item:
                        item_id = matching_item.id
                        item_name = matching_item.name
                except Exception as e:
                    logger.warning(f"Could not find matching item: {e}")
            
            requirements_data.append({
                'id': req.id,
                'item_id': item_id,
                'item_name': item_name,
                'section': req.section or 'GENERAL',
                'unit': req.unit or 'pcs',
                'price': float(req.price) if req.price is not None else 0.00,
                'quantity': int(req.quantity) if req.quantity is not None else 1,
                'total': float(req.total) if req.total is not None else 0.00,
                'ticket_number': req.ticket_number,
                'owner_name': req.owner_name,
                'phone_no': req.phone_no,
            })
        
        # Prepare items data
        items_data = []
        for item in items:
            items_data.append({
                'id': item.id,
                'name': item.name,
                'unit_of_measure': item.unit_of_measure or 'pcs',
                'mrp': float(item.mrp) if item.mrp is not None else 0.00,
                'section': item.section or 'GENERAL',
            })
        
        # Convert to JSON
        requirements_json = json.dumps(requirements_data)
        items_json = json.dumps(items_data)
        
        # Create a safe lead dict for template
        lead_data = {
            'id': lead.id,
            'ownerName': owner_name,
            'phoneNo': phone_value,
            'ticket_number': ticket_number,
            'priority': getattr(lead, 'priority', 'Medium'),
            'created_date': getattr(lead, 'created_at', None) or getattr(lead, 'date', None),
            'email': getattr(lead, 'email', ''),
            'company': getattr(lead, 'company', '') or getattr(lead, 'business', ''),
            'place': getattr(lead, 'place', '') or getattr(lead, 'District', '') or getattr(lead, 'State', ''),
            'status': getattr(lead, 'status', 'Active'),
        }
        
        context = {
            'lead': lead,  # Original lead object
            'lead_data': lead_data,  # Safe dictionary with all needed fields
            'requirements': requirements,
            'requirements_json': requirements_json,
            'requirements_count': requirements_count,
            'section_summary': section_summary,
            'items': items,
            'items_json': items_json,
            'lead_id': lead_id,
            'current_lead_id': lead_id,  # For highlighting current lead
            'active_leads': active_leads,  # For directory
            'active_users': active_users,  # For employee directory
            'leads_count': active_leads.count(),  # For showing count
        }
        
        return render(request, 'requirement_edit.html', context)
        
    except Exception as e:
        logger.error(f"❌ Error loading edit page: {str(e)}", exc_info=True)
        messages.error(request, f'Error loading requirements: {str(e)}')
        return redirect('app5:requirement_list')
    
    

def update_requirement(request, lead_id):
    """
    Handle requirement update for a specific lead
    Save updated requirements to database
    """
    if request.method != 'POST':
        return redirect('app5:edit_requirement', lead_id=lead_id)
    
    try:
        # Get the lead
        lead = get_object_or_404(Lead, id=lead_id)
        
        logger.info(f"💾 Updating requirements for Lead: {lead.ticket_number}")
        
        # Get form data
        sections = request.POST.getlist('section[]')
        item_ids = request.POST.getlist('item_id[]')
        units = request.POST.getlist('unit[]')
        prices = request.POST.getlist('price[]')
        quantities = request.POST.getlist('qty[]')
        requirement_ids = request.POST.getlist('requirement_id[]')
        
        logger.info(f"Processing {len(item_ids)} items")
        
        # Track which requirements were updated
        updated_ids = set()
        
        # ✅ Determine which Item model to use
        try:
            from purchase_order.models import Item as POItem
            ItemModel = POItem
        except ImportError:
            from .models import Item as App5Item
            ItemModel = App5Item
        
        # Process each item
        for i in range(len(item_ids)):
            if not item_ids[i]:
                continue
            
            try:
                # Get the item
                item = ItemModel.objects.filter(id=item_ids[i]).first()
                if not item:
                    logger.warning(f"⚠️ Item {item_ids[i]} not found")
                    continue
                
                # Parse values
                section = sections[i] if i < len(sections) else 'GENERAL'
                unit = units[i] if i < len(units) else 'pcs'
                price = float(prices[i]) if i < len(prices) and prices[i] else 0.00
                quantity = int(quantities[i]) if i < len(quantities) and quantities[i] else 1
                total = price * quantity
                
                # Check if we're updating existing or creating new
                if i < len(requirement_ids) and requirement_ids[i]:
                    # Update existing requirement
                    try:
                        req = RequirementItem.objects.get(id=requirement_ids[i])
                        req.item_name = item.name
                        req.section = section
                        req.unit = unit
                        req.price = price
                        req.quantity = quantity
                        req.total = total
                        req.save()
                        
                        updated_ids.add(int(requirement_ids[i]))
                        logger.debug(f"✅ Updated requirement {req.id}")
                        
                    except RequirementItem.DoesNotExist:
                        # Create new if doesn't exist
                        req = RequirementItem.objects.create(
                            item_name=item.name,
                            owner_name=lead.ownerName,
                            phone_no=lead.phoneNo,
                            section=section,
                            unit=unit,
                            price=price,
                            quantity=quantity,
                            total=total
                        )
                        updated_ids.add(req.id)
                        logger.info(f"✅ Created new requirement {req.id}")
                else:
                    # Create new requirement
                    req = RequirementItem.objects.create(
                        item_name=item.name,
                        owner_name=lead.ownerName,
                        phone_no=lead.phoneNo,
                        section=section,
                        unit=unit,
                        price=price,
                        quantity=quantity,
                        total=total
                    )
                    updated_ids.add(req.id)
                    logger.info(f"✅ Created new requirement {req.id}")
                    
            except Exception as e:
                logger.error(f"❌ Error processing item {i+1}: {e}")
                continue
        
        # Delete requirements that were removed
        existing_requirements = RequirementItem.objects.filter(
            owner_name=lead.ownerName,
            phone_no=lead.phoneNo
        )
        
        deleted_count = 0
        for req in existing_requirements:
            if req.id not in updated_ids:
                req.delete()
                deleted_count += 1
                logger.info(f"🗑️ Deleted requirement {req.id}")
        
        # Success message
        update_count = len(updated_ids)
        message = f'✅ Successfully updated {update_count} requirement(s)'
        if deleted_count > 0:
            message += f' and deleted {deleted_count} item(s)'
        
        messages.success(request, message)
        logger.info(f"✅ Requirements updated - Updated: {update_count}, Deleted: {deleted_count}")
        
        return redirect('app5:requirement_list')
        
    except Exception as e:
        logger.error(f"❌ Error updating requirements: {e}", exc_info=True)
        messages.error(request, f'Error updating requirements: {str(e)}')
        return redirect('app5:edit_requirement', lead_id=lead_id)


from django.http import JsonResponse
from purchase_order.models import Item as POItem

def get_item_details(request):
    item_name = request.GET.get("item_name", "")

    try:
        item = POItem.objects.get(name=item_name, is_active=True)
        return JsonResponse({
            "success": True,
            "unit": item.unit_of_measure,
            "price": float(item.purchase_price),
        })
    except POItem.DoesNotExist:
        return JsonResponse({"success": False})
    
def get_lead_data(request, lead_id):
    try:
        lead = Lead.objects.get(id=lead_id)
        lead_data = {
            'id': lead.id,
            'ownerName': lead.ownerName,
            'phoneNo': lead.phoneNo,
            'email': lead.email,
            'status': lead.status,
            'customerType': lead.customerType,
            'name': lead.name,
            'address': lead.address,
            'place': lead.place,
            'District': lead.District,
            'State': lead.State,
            'pinCode': lead.pinCode,
            'firstName': lead.firstName,
            'individualAddress': lead.individualAddress,
            'individualPlace': lead.individualPlace,
            'individualDistrict': lead.individualDistrict,
            'individualState': lead.individualState,
            'individualPinCode': lead.individualPinCode,
            'date': lead.date.strftime('%Y-%m-%d') if lead.date else '',
            'refFrom': lead.refFrom,
            'business': lead.business,
            'marketedBy': lead.marketedBy,
            'Consultant': lead.Consultant,
            'requirement': lead.requirement,
            'details': lead.details,
        }
        return JsonResponse(lead_data)
    except Lead.DoesNotExist:
        return JsonResponse({'error': 'Lead not found'}, status=404)







# Add these imports at the top if not present
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import IntegrityError
from .models import BusinessNature


# In views.py, update the business nature views:

def business_nature_list(request):
    natures = BusinessNature.objects.all()
    # Remove 'app5/' prefix since your template is in the main templates directory
    return render(request, 'business_nature_list.html', {'natures': natures})

def business_nature_create(request):
    """Create a new Business Nature"""
    if request.method == 'POST':
        name = request.POST.get('name', '').strip().upper()  # Convert to uppercase
        description = request.POST.get('description', '')
        
        try:
            BusinessNature.objects.create(
                name=name,
                description=description
            )
            messages.success(request, f'Business nature "{name}" created successfully!')
            return redirect('app5:business_nature_list')
        except IntegrityError:
            messages.error(request, f'Business nature "{name}" already exists!')
        except Exception as e:
            messages.error(request, f'Error creating business nature: {str(e)}')
    
    return render(request, 'bussiness_nature_form.html', {
        'title': 'Create Business Nature'
    })

def business_nature_edit(request, id):
    """Edit an existing Business Nature"""
    nature = get_object_or_404(BusinessNature, id=id)
    
    if request.method == 'POST':
        name = request.POST.get('name', '').strip().upper()  # Convert to uppercase
        description = request.POST.get('description', '')
        
        try:
            # Check for duplicate name (excluding current object)
            if BusinessNature.objects.filter(name=name).exclude(id=id).exists():
                messages.error(request, f'Business nature "{name}" already exists!')
            else:
                nature.name = name
                nature.description = description
                nature.save()
                messages.success(request, f'Business nature "{name}" updated successfully!')
                return redirect('app5:business_nature_list')
        except Exception as e:
            messages.error(request, f'Error updating business nature: {str(e)}')
    
    # GET request - show form with existing data
    return render(request, 'bussiness_nature_form.html', {
        'nature': nature,
        'title': 'Edit Business Nature'
    })


def business_nature_delete(request, pk):
    nature = get_object_or_404(BusinessNature, pk=pk)
    
    # Handle both POST and GET for backward compatibility
    if request.method in ["POST", "GET"]:
        nature_name = nature.name
        nature.delete()
        messages.success(request, f'Business nature "{nature_name}" deleted successfully!')
        return redirect('app5:business_nature_list')
    
    messages.error(request, 'Invalid request method.')
    return redirect('app5:business_nature_list')


# state master
# Add these imports at the top if not already present
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import StateMaster

# Update your state views in views.py

def state_list(request):
    """Display all states in the list"""
    states = StateMaster.objects.all().order_by('name')
    
    # Get counts for statistics
    total_states = states.count()
    
    context = {
        'states': states,
        'total_states': total_states,
    }
    return render(request, 'state_master_list.html', context)

# In the state_master_create function, update the name processing:
def state_master_create(request):
    """Handle state creation form"""
    if request.method == 'POST':
        name = request.POST.get('stateName', '').strip().upper()  # Add .upper() here
        description = request.POST.get('stateDescription', '').strip()
        
        # Validate required fields
        if not name:
            messages.error(request, 'State name is required')
            return render(request, 'state_master_form.html', {
                'state_name': name,
                'description': description
            })
        
        # Check for duplicate state name
        if StateMaster.objects.filter(name__iexact=name).exists():
            messages.error(request, f'State "{name}" already exists!')
            return render(request, 'state_master_form.html', {
                'state_name': name,
                'description': description
            })
        
        try:
            # Create new state
            state = StateMaster.objects.create(
                name=name,  # This will now be in uppercase
                description=description
            )
            
            messages.success(request, f'State "{name}" created successfully!')
            return redirect('app5:state_master_list')
            
        except Exception as e:
            messages.error(request, f'Error creating state: {str(e)}')
            return render(request, 'state_master_form.html', {
                'state_name': name,
                'description': description
            })
    
    # GET request - show empty form
    return render(request, 'state_master_form.html')

# Add these additional state management views

# In the state_master_edit function, update the name processing:
def state_master_edit(request, id):
    """Edit an existing state"""
    state = get_object_or_404(StateMaster, id=id)
    
    if request.method == 'POST':
        name = request.POST.get('stateName', '').strip().upper()  # Add .upper() here
        description = request.POST.get('stateDescription', '').strip()
        
        # Validate required fields
        if not name:
            messages.error(request, 'State name is required')
            return render(request, 'state_master_form.html', {
                'state': state,
                'state_name': name,
                'description': description,
                'is_edit': True
            })
        
        # Check for duplicate state name (excluding current state)
        if StateMaster.objects.filter(name__iexact=name).exclude(id=id).exists():
            messages.error(request, f'State "{name}" already exists!')
            return render(request, 'state_master_form.html', {
                'state': state,
                'state_name': name,
                'description': description,
                'is_edit': True
            })
        
        try:
            # Update state
            state.name = name  # This will now be in uppercase
            state.description = description
            state.save()
            
            messages.success(request, f'State "{name}" updated successfully!')
            return redirect('app5:state_master_list')
            
        except Exception as e:
            messages.error(request, f'Error updating state: {str(e)}')
            return render(request, 'state_master_form.html', {
                'state': state,
                'state_name': name,
                'description': description,
                'is_edit': True
            })
    
    # GET request - show form with existing data
    return render(request, 'state_master_form.html', {
        'state': state,
        'is_edit': True
    })
def state_master_delete(request, id):
    """Delete a state"""
    state = get_object_or_404(StateMaster, id=id)
    
    if request.method == 'POST':
        state_name = state.name
        state.delete()
        messages.success(request, f'State "{state_name}" deleted successfully!')
        return redirect('app5:state_master_list')
    
    # If not POST, show confirmation page (optional)
    return render(request, 'state_confirm_delete.html', {'state': state})



def _generate_unique_lead_ticket():
    today_str = timezone.now().strftime("%Y%m%d")
    base_prefix = f"TKT-{today_str}-"
    counter = 1
    
    while True:
        ticket_no = f"{base_prefix}{counter:04d}"
        if not Lead.objects.filter(ticket_number=ticket_no).exists():
            return ticket_no
        counter += 1


# views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Q
from .models import Reference

def reference_list(request):
    search_query = request.GET.get('search', '')
    
    if search_query:
        references = Reference.objects.filter(
            Q(ref_name__icontains=search_query) |
            Q(description__icontains=search_query)
        ).order_by('id')
        if references.exists():
            messages.info(request, f'Found {references.count()} reference(s) matching "{search_query}"')
        else:
            messages.info(request, f'No references found matching "{search_query}"')
    else:
        references = Reference.objects.all().order_by('id')
    
    return render(request, 'reference_master_list.html', {# Make sure this path is correct
        'references': references,
        'search_query': search_query
    })

def reference_add(request):
    if request.method == 'POST':
        ref_name = request.POST.get('ref_name')
        description = request.POST.get('description')
        
        if ref_name:
            # Check if reference with same name already exists
            if Reference.objects.filter(ref_name=ref_name).exists():
                messages.error(request, f'A reference with name "{ref_name}" already exists.')
            else:
                reference = Reference.objects.create(
                    ref_name=ref_name,
                    description=description
                )
                messages.success(request, f'Reference "{reference.ref_name}" added successfully!')
                return redirect('app5:reference_list')
        else:
            messages.error(request, 'Reference name is required.')
    
    # FIX: Remove 'app5/' from the template path
    return render(request, 'reference_master_form.html', {})

def reference_edit(request, id):
    reference = get_object_or_404(Reference, id=id)
    
    if request.method == 'POST':
        ref_name = request.POST.get('ref_name')
        description = request.POST.get('description')
        
        if ref_name:
            # Check if another reference with same name exists (excluding current one)
            if Reference.objects.filter(ref_name=ref_name).exclude(id=id).exists():
                messages.error(request, f'A reference with name "{ref_name}" already exists.')
            else:
                reference.ref_name = ref_name
                reference.description = description
                reference.save()
                messages.success(request, f'Reference "{reference.ref_name}" updated successfully!')
                return redirect('app5:reference_list')
        else:
            messages.error(request, 'Reference name is required.')
    
    # FIX: Remove 'app5/' from the template path
    return render(request, 'reference_master_form.html', {'reference': reference})

def reference_delete(request, id):
    reference = get_object_or_404(Reference, id=id)
    
    if request.method == 'POST':
        reference_name = reference.ref_name
        reference.delete()
        messages.success(request, f'Reference "{reference_name}" deleted successfully!')
        return redirect('app5:reference_list')  # Changed from 'reference_master_list' to 'reference_list'
    
    messages.error(request, 'Invalid request method. Please use the delete button from the list.')
    return redirect('app5:reference_list')  # Changed from 'reference_master_list' to 'reference_list'



def event_form(request):
    return render(request, 'event_form.html')


# Replace your existing quotation views with this complete version

from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from django.contrib import messages
from django.utils import timezone
from django.core import serializers
from decimal import Decimal
import json
import logging

from purchase_order.models import Item, Department
from .models import Lead, Quotation, QuotationItem
from app1.models import User

logger = logging.getLogger(__name__)


# ============================================================================
# QUOTATION LIST VIEW - Display form to create quotations
# ============================================================================
def quotation_list_view(request):
    """
    Display quotation form with active leads, employees, and items
    """
    # ✅ GET ACTIVE LEADS (for quotation form)
    lead_tickets = []  # Renamed from active_leads for template compatibility
    try:
        leads_qs = Lead.objects.filter(status__iexact='Active').order_by('-created_at')[:50]
        
        for lead in leads_qs:
            # Get proper ticket number
            ticket_number = getattr(lead, 'ticket_number', None)
            if not ticket_number:
                ticket_number = f"TKT-{lead.id:06d}"  # Format with leading zeros
            
            # Get owner name (handle both field names)
            owner_name = getattr(lead, 'ownerName', None) or getattr(lead, 'owner_name', 'Unknown')
            
            # Get phone number (handle both field names)
            phone_number = getattr(lead, 'phoneNo', None) or getattr(lead, 'phone_number', '')
            
            # Get company name if business customer
            company_name = ''
            if getattr(lead, 'customerType', '') == 'Business':
                company_name = getattr(lead, 'name', '') or getattr(lead, 'company_name', '')
            
            # Get address (handle multiple address fields)
            address = getattr(lead, 'address', '')
            if not address and getattr(lead, 'customerType', '') == 'Individual':
                address = getattr(lead, 'individualAddress', '')
            
            lead_tickets.append({
                'id': lead.id,
                'ticket_number': ticket_number,
                'owner_name': owner_name,
                'phone_number': phone_number,
                'email': getattr(lead, 'email', '') or '',
                'address': address or '',
                'company_name': company_name,
                'status': getattr(lead, 'status', 'Active'),
                'customerType': getattr(lead, 'customerType', ''),
                'place': getattr(lead, 'place', ''),
                'business': getattr(lead, 'business', ''),
                'priority': getattr(lead, 'priority', 'Medium'),
                'created_at': lead.created_at if hasattr(lead, 'created_at') else None,
            })
        
        logger.info(f"✅ Loaded {len(lead_tickets)} active leads for quotation")
        
    except Exception as e:
        logger.error(f"❌ Error loading leads: {e}", exc_info=True)
        lead_tickets = []
    
    # ✅ GET ACTIVE EMPLOYEES/USERS
    active_employees = []
    try:
        # Try to get users with status field
        user_fields = [f.name for f in User._meta.get_fields()]
        
        if 'status' in user_fields:
            users_qs = User.objects.filter(status='active').order_by('name')
        elif 'is_active' in user_fields:
            users_qs = User.objects.filter(is_active=True).order_by('name')
        else:
            users_qs = User.objects.all().order_by('name')
        
        for user in users_qs:
            active_employees.append({
                'id': user.id,
                'name': getattr(user, 'name', f'User {user.id}'),
                'department': getattr(user, 'department', ''),
                'designation': getattr(user, 'designation', ''),
                'phone': getattr(user, 'phone_number', '') or getattr(user, 'phone', ''),
            })
        
        logger.info(f"✅ Loaded {len(active_employees)} active employees for quotation")
        
    except Exception as e:
        logger.error(f"❌ Error loading employees: {e}")
        active_employees = []
    
    # ✅ GET ITEMS FROM PURCHASE_ORDER
    items = []
    try:
        items = Item.objects.filter(is_active=True).order_by('section', 'name')
        logger.info(f"✅ Loaded {items.count()} items for quotation")
    except Exception as e:
        logger.error(f"❌ Error loading items: {e}")
        items = []
    
    # ✅ GET DEPARTMENTS (if needed for filtering)
    departments = []
    try:
        departments = Department.objects.filter(is_active=True).order_by('name')
    except Exception as e:
        logger.debug(f"No departments available: {e}")
    
    # Calculate counts
    leads_count = len(lead_tickets)
    employees_count = len(active_employees)
    items_count = items.count() if hasattr(items, 'count') else len(items)
    
    # Debug: Check lead data
    if lead_tickets:
        first_lead = lead_tickets[0]
        logger.info(f"📅 First lead ticket: {first_lead.get('ticket_number')} - {first_lead.get('owner_name')}")
        logger.info(f"📅 First lead created_at: {first_lead.get('created_at')}")
        logger.info(f"📅 First lead phone: {first_lead.get('phone_number')}")
    
    context = {
        'lead_tickets': lead_tickets,  # Changed from active_leads to lead_tickets
        'active_employees': active_employees,
        'items': items,
        'departments': departments,
        'leads_count': leads_count,
        'employees_count': employees_count,
        'items_count': items_count,
    }
    
    logger.info(f"📊 Quotation List Context: {leads_count} leads, {employees_count} employees, {items_count} items")
    
    return render(request, 'quotation_list.html', context)


# ============================================================================
# QUOTATION FORM VIEW - Display saved quotations
# ============================================================================
from django.db.models import Sum  # ADD THIS IMPORT

def quotation_form_view(request):
    """
    Display saved quotations in quotation_form.html
    Shows all quotations with their items
    """
    try:
        logger.info("🔍 Entering quotation_form_view")
        
        # Get all quotations with related data - FIXED JOIN
        quotations = Quotation.objects.select_related(
            'lead'  # Make sure this is correct foreign key name
        ).prefetch_related(
            'items'
        ).order_by('-created_at')

        # ✅ GET DEPARTMENTS FOR BRANCH SELECTION
        departments = Department.objects.filter(is_active=True).order_by('name')
        logger.info(f"🏢 Loaded {departments.count()} active departments")
        
        # DEBUG: Check if we're getting any data
        logger.info(f"📊 Quotations QuerySet: {quotations}")
        
        # Force evaluation to see actual data
        quotation_list = list(quotations)
        logger.info(f"📊 Quotation list count: {len(quotation_list)}")
        
        # Log each quotation with lead info
        for i, q in enumerate(quotation_list[:5]):
            lead_info = f"{q.lead.ownerName}" if q.lead else "No Lead"
            logger.info(f"  {i+1}. {q.quotation_number} - {lead_info} - ₹{q.grand_total} - Status: {q.status}")
        
        # Get active leads for the directory
        active_leads = []
        try:
            leads_qs = Lead.objects.filter(
                status__iexact='Active'
            ).order_by('-created_at')[:50]
            
            for lead in leads_qs:
                active_leads.append({
                    'id': lead.id,
                    'ownerName': lead.ownerName or '',
                    'phoneNo': lead.phoneNo or '',
                    'email': lead.email or '',
                    'ticket_number': getattr(lead, 'ticket_number', f'TKT-{lead.id}'),
                    'status': lead.status or 'Active',
                    'priority': getattr(lead, 'priority', 'Medium'),
                    'place': lead.place or '',
                    'business': lead.business or '',
                    'customerType': lead.customerType or '',
                    'created_at': lead.created_at if hasattr(lead, 'created_at') else lead.date,
                })
            
            logger.info(f"📋 Loaded {len(active_leads)} active leads")
            
        except Exception as e:
            logger.error(f"❌ Error loading leads: {e}")
            active_leads = []
        
        # Get active users
        active_users = []
        try:
            user_fields = [f.name for f in User._meta.get_fields()]
            
            if 'status' in user_fields:
                users_qs = User.objects.filter(status='active').order_by('name')
            elif 'is_active' in user_fields:
                users_qs = User.objects.filter(is_active=True).order_by('name')
            else:
                users_qs = User.objects.all().order_by('name')
            
            for user in users_qs:
                active_users.append({
                    'id': user.id,
                    'name': getattr(user, 'name', f'User {user.id}'),
                    'department': getattr(user, 'department', ''),
                    'designation': getattr(user, 'designation', ''),
                })
        except Exception as e:
            logger.error(f"❌ Error loading users: {e}")
            active_users = []
        
        # Calculate statistics
        total_quotations = len(quotation_list)
        
        # ✅ UPDATED CONTEXT - INCLUDES DEPARTMENTS
        context = {
            'quotations': quotation_list,  # Pass the evaluated list
            'leads': active_leads,
            'active_users': active_users,
            'departments': departments,  # ✅ ADDED: Departments for branch selection
            'total_quotations': total_quotations,
            'leads_count': len(active_leads),
        }
        
        logger.info(f"✅ Context prepared with {total_quotations} quotations and {departments.count()} departments")
        
        return render(request, 'quotation_form.html', context)
        
    except Exception as e:
        logger.error(f"❌ Error in quotation_form_view: {e}", exc_info=True)
        
        # Return empty context but show error
        # ✅ INCLUDE EMPTY DEPARTMENTS IN ERROR CASE TOO
        return render(request, 'quotation_form.html', {
            'quotations': [],
            'leads': [],
            'active_users': [],
            'departments': [],  # ✅ ADDED: Empty departments list
            'total_quotations': 0,
            'leads_count': 0,
            'error_message': f'Error loading quotations: {str(e)}'
        })

# ============================================================================
# QUOTATION SUBMIT - Save quotation to database
# ============================================================================

# Fixed quotation_submit function for views.py
# This replaces the existing quotation_submit function in your views.py file

import json
import logging
from decimal import Decimal, InvalidOperation
from datetime import datetime, timedelta
from django.http import JsonResponse
from django.db import transaction
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

# Import models
from app5.models import Lead, Quotation, QuotationItem
from purchase_order.models import Item
from app1.models import User

logger = logging.getLogger(__name__)


@csrf_exempt  # Add this if you're having CSRF token issues
def quotation_submit(request):
    """
    Handle quotation submission from quotation_list.html
    Save quotation and items to database
    """
    if request.method != 'POST':
        logger.warning(f"❌ Invalid request method: {request.method}")
        return JsonResponse({
            'success': False,
            'message': 'Invalid request method. Only POST requests are allowed.'
        }, status=405)
    
    try:
        # Parse JSON data
        data = json.loads(request.body)
        logger.info(f"📝 Received quotation submission request")
        logger.debug(f"Raw data keys: {list(data.keys())}")
        
        # Extract main quotation data
        # NOTE: Frontend sends 'lead_ticket_id' but we need 'lead_id'
        lead_id = data.get('lead_id') or data.get('lead_ticket_id')  # ✅ FIXED: Accept both field names
        notes = data.get('notes', '').strip()
        items_data = data.get('items', [])
        
        # Financial totals
        try:
            subtotal = Decimal(str(data.get('subtotal', 0)))
            total_discount = Decimal(str(data.get('total_discount', 0)))
            total_tax = Decimal(str(data.get('total_tax', 0)))
            grand_total = Decimal(str(data.get('grand_total', 0)))
        except (InvalidOperation, ValueError) as e:
            logger.error(f"❌ Invalid decimal values in financial totals: {e}")
            return JsonResponse({
                'success': False,
                'message': f'Invalid financial values: {str(e)}'
            }, status=400)
        
        logger.debug(f"📊 Totals - Subtotal: {subtotal}, Discount: {total_discount}, Tax: {total_tax}, Grand Total: {grand_total}")
        logger.debug(f"📦 Items count: {len(items_data)}")
        
        # ========== VALIDATION ==========
        validation_errors = []
        
        # Validate lead
        if not lead_id:
            validation_errors.append('Please select a lead from the directory')
        
        # Validate items
        if not items_data or len(items_data) == 0:
            validation_errors.append('Please add at least one item to the quotation')
        else:
            # Validate each item
            invalid_items = []
            for idx, item in enumerate(items_data):
                item_id = item.get('item_id')
                item_name = item.get('item_name')
                
                if not item_id or not item_name:
                    invalid_items.append(idx + 1)
                
                # Additional item validation
                try:
                    quantity = Decimal(str(item.get('quantity', 0)))
                    if quantity <= 0:
                        validation_errors.append(f'Item {idx + 1}: Quantity must be greater than 0')
                    
                    sales_price = Decimal(str(item.get('sales_price', 0)))
                    unit_price = Decimal(str(item.get('unit_price', 0)))
                    if sales_price < 0 or unit_price < 0:
                        validation_errors.append(f'Item {idx + 1}: Price cannot be negative')
                except (InvalidOperation, ValueError) as e:
                    validation_errors.append(f'Item {idx + 1}: Invalid numeric value - {str(e)}')
            
            if invalid_items:
                validation_errors.append(f'Please select an item for rows: {", ".join(map(str, invalid_items))}')
        
        # Validate totals
        if grand_total <= 0:
            validation_errors.append('Grand total must be greater than 0')
        
        # Return validation errors if any
        if validation_errors:
            logger.warning(f"❌ Validation errors: {validation_errors}")
            return JsonResponse({
                'success': False,
                'message': '\n'.join(validation_errors),
                'validation_errors': validation_errors
            }, status=400)
        
        # ========== LEAD PROCESSING ==========
        try:
            lead = Lead.objects.get(id=lead_id)
            logger.info(f"✅ Found lead: {lead.ticket_number} - {lead.ownerName}")
        except Lead.DoesNotExist:
            logger.error(f"❌ Lead {lead_id} not found")
            return JsonResponse({
                'success': False,
                'message': f'Lead not found (ID: {lead_id})',
                'lead_id': lead_id
            }, status=404)
        
        # Get client information from lead
        client_name = lead.ownerName or lead.display_name or "Unknown Client"
        client_phone = lead.phoneNo or "N/A"
        client_email = lead.email or None
        
        # Get company name from lead if business type
        company_name = None
        if lead.customerType == 'Business':
            company_name = lead.name or lead.business or lead.ownerName
        
        logger.debug(f"👤 Client info - Name: {client_name}, Phone: {client_phone}, Email: {client_email}")
        
        # ========== USER AUTHENTICATION ==========
        current_user = None
        user_info = "Anonymous"
        
        # Try to get user from session first (most reliable for custom auth)
        if request.session.get('custom_user_id'):
            try:
                current_user = User.objects.get(id=request.session['custom_user_id'])
                user_info = f"{current_user.name} (Session ID: {current_user.id})"
                logger.info(f"👤 User from session: {user_info}")
            except User.DoesNotExist:
                logger.warning(f"⚠️ Session user {request.session.get('custom_user_id')} not found")
        
        # Fallback to Django authenticated user
        if not current_user and request.user and request.user.is_authenticated:
            try:
                # Try to get user by userid or name from the authenticated user
                authenticated_username = request.user.username
                
                # Since your custom User model doesn't have username, try name
                current_user = User.objects.filter(name=authenticated_username).first()
                
                if not current_user:
                    # Try to get by userid
                    current_user = User.objects.filter(userid=authenticated_username).first()
                
                if current_user:
                    user_info = f"{current_user.name} (ID: {current_user.id})"
                    logger.info(f"👤 User from Django auth: {user_info}")
                    
            except Exception as e:
                logger.warning(f"⚠️ Could not get user from request.user: {e}")
        
        if not current_user:
            logger.info(f"👤 No authenticated user found, creating as anonymous")
        
        # ========== QUOTATION CREATION ==========
        quotation_date = timezone.now().date()
        valid_until = quotation_date + timedelta(days=30)  # Valid for 30 days
        
        # Generate quotation number and save to database
        with transaction.atomic():
            # Get last quotation number
            from django.db.models import Max
            last_quote = Quotation.objects.aggregate(Max('id'))['id__max'] or 0
            
            # Generate sequential quotation number
            quotation_number = f"QT-{quotation_date.strftime('%Y%m%d')}-{(last_quote + 1):04d}"
            
            logger.info(f"🔢 Generated quotation number: {quotation_number}")
            
            # Create quotation
            quotation = Quotation.objects.create(
                lead=lead,
                client_name=client_name,
                client_phone=client_phone,
                client_email=client_email,
                company_name=company_name,
                quotation_date=quotation_date,
                valid_until=valid_until,
                quotation_number=quotation_number,
                notes=notes if notes else None,
                subtotal=subtotal,
                total_discount=total_discount,
                total_tax=total_tax,
                grand_total=grand_total,
                status='draft',
                created_by=current_user
            )
            
            logger.info(f"✅ Created quotation record: {quotation.id} - {quotation.quotation_number}")
            
            # ========== QUOTATION ITEMS CREATION ==========
            items_created = 0
            total_line_total = Decimal('0')
            item_errors = []
            
            for idx, item_data in enumerate(items_data):
                try:
                    item_id = item_data.get('item_id')
                    item = None
                    
                    # Try to get item from purchase order
                    if item_id:
                        try:
                            # ✅ FIXED: Use purchase_order.models.Item
                            item = Item.objects.get(id=item_id)
                            logger.debug(f"  🛒 Found PO item: {item.name} (ID: {item.id})")
                        except Item.DoesNotExist:
                            logger.warning(f"  ⚠️ Purchase order item {item_id} not found, using provided data")
                    
                    # Extract item data with proper error handling
                    try:
                        quantity = Decimal(str(item_data.get('quantity', 1)))
                        sales_price = Decimal(str(item_data.get('sales_price', 0)))
                        unit_price = Decimal(str(item_data.get('unit_price', 0)))
                        discount_percentage = Decimal(str(item_data.get('discount', 0)))
                        tax_percentage = Decimal(str(item_data.get('tax', 0)))
                        line_total = Decimal(str(item_data.get('total', 0)))
                        entry_rate = Decimal(str(item_data.get('entry_rate', 0)))
                    except (InvalidOperation, ValueError) as e:
                        raise ValueError(f"Invalid numeric value in item data: {str(e)}")
                    
                    # Validate item data
                    if quantity <= 0:
                        raise ValueError(f"Invalid quantity: {quantity}")
                    
                    if line_total <= 0:
                        logger.warning(f"  ⚠️ Item {idx+1} has zero or negative line total: {line_total}")
                    
                    # Calculate derived values
                    base_price = sales_price if sales_price > 0 else unit_price
                    discount_amount = (base_price * quantity) * (discount_percentage / 100)
                    amount_after_discount = (base_price * quantity) - discount_amount
                    tax_amount = amount_after_discount * (tax_percentage / 100)
                    
                    # Get item details
                    item_name = item_data.get('item_name', '')
                    if not item_name and item:
                        item_name = item.name
                    if not item_name:
                        item_name = 'Unknown Item'
                    
                    description = item_data.get('description', '')
                    if not description and item and hasattr(item, 'description') and item.description:
                        description = item.description
                    
                    unit = item_data.get('unit', 'pcs')
                    if not unit and item and hasattr(item, 'unit_of_measure') and item.unit_of_measure:
                        unit = item.unit_of_measure
                    
                    hsn_code = item_data.get('hsn_code', '')
                    if not hsn_code and item and hasattr(item, 'hsn_code') and item.hsn_code:
                        hsn_code = item.hsn_code
                    
                    section = item_data.get('section', '')
                    
                    # Create quotation item
                    quotation_item = QuotationItem.objects.create(
                        quotation=quotation,
                        item=item,
                        item_name=item_name,
                        description=description or f"{item_name} - {section}" if section else item_name,
                        quantity=quantity,
                        unit=unit,
                        entry_rate=entry_rate,
                        sales_price=sales_price,
                        unit_price=unit_price,
                        discount_percentage=discount_percentage,
                        discount_amount=discount_amount,
                        tax_percentage=tax_percentage,
                        tax_amount=tax_amount,
                        line_total=line_total,
                        hsn_code=hsn_code,
                        order=idx
                    )
                    
                    items_created += 1
                    total_line_total += line_total
                    
                    logger.debug(f"  📦 Created item {idx+1}: {quotation_item.item_name} "
                                f"(Qty: {quantity}, Price: ₹{base_price}, Total: ₹{line_total})")
                    
                except Exception as e:
                    logger.error(f"❌ Error creating item {idx+1}: {e}", exc_info=True)
                    item_errors.append(f"Item {idx+1}: {str(e)}")
                    raise  # Re-raise to trigger transaction rollback
            
            # Verify totals match (allow small rounding differences)
            total_discrepancy = abs(total_line_total - grand_total)
            if total_discrepancy > Decimal('0.10'):  # Allow 10 cents difference for rounding
                logger.warning(f"⚠️ Line totals ({total_line_total}) don't match grand total ({grand_total}) "
                              f"Difference: {total_discrepancy}")
                
                # Update quotation totals to match line totals
                quotation.grand_total = total_line_total
                quotation.subtotal = total_line_total - total_tax
                quotation.save()
                
                logger.info(f"🔄 Updated quotation totals to match line items")
        
        # ========== POST-CREATION UPDATES ==========
        # Update lead with quotation info
        lead_updated = False
        try:
            if hasattr(lead, 'details'):
                if lead.details:
                    lead.details = f"Quotation created: {quotation_number} ({quotation_date})\n" + lead.details
                else:
                    lead.details = f"Quotation created: {quotation_number} ({quotation_date})"
                lead.save()
                lead_updated = True
                logger.debug(f"✅ Updated lead details with quotation info")
        except Exception as e:
            logger.warning(f"⚠️ Could not update lead details: {e}")
        
        # ========== SUCCESS RESPONSE ==========
        response_data = {
            'success': True,
            'message': f'✅ Quotation {quotation.quotation_number} created successfully!',
            'quotation': {
                'id': quotation.id,
                'quotation_number': quotation.quotation_number,
                'date': quotation_date.strftime('%Y-%m-%d'),
                'valid_until': valid_until.strftime('%Y-%m-%d'),
                'status': 'draft',
                'client_name': client_name,
                'client_phone': client_phone,
                'items_count': items_created,
                'subtotal': float(subtotal),
                'total_discount': float(total_discount),
                'total_tax': float(total_tax),
                'grand_total': float(grand_total),
                'created_by': user_info,
            },
            'redirect_url': '/app5/quotation/',  # ✅ FIXED: Redirect to list page instead of form
            'metadata': {
                'lead_updated': lead_updated,
                'items_processed': items_created,
                'user': user_info,
                'timestamp': timezone.now().isoformat()
            }
        }
        
        logger.info(f"🎉 Quotation {quotation.quotation_number} created successfully with {items_created} items")
        logger.info(f"📊 Totals - Subtotal: ₹{subtotal}, Tax: ₹{total_tax}, Grand Total: ₹{grand_total}")
        
        return JsonResponse(response_data)
        
    except json.JSONDecodeError as e:
        logger.error(f"❌ Invalid JSON data: {e}")
        logger.debug(f"Request body: {request.body[:500] if request.body else 'Empty'}...")
        
        return JsonResponse({
            'success': False,
            'message': 'Invalid JSON data. Please check your input.',
            'error_detail': str(e)
        }, status=400)
    
    except Lead.DoesNotExist as e:
        logger.error(f"❌ Lead not found: {e}")
        return JsonResponse({
            'success': False,
            'message': 'Lead not found. Please select a valid lead.',
            'error_detail': str(e)
        }, status=404)
    
    except Item.DoesNotExist as e:
        logger.error(f"❌ Item not found: {e}")
        return JsonResponse({
            'success': False,
            'message': 'One or more items not found in the system.',
            'error_detail': str(e)
        }, status=404)
    
    except Exception as e:
        logger.error(f"❌ Unexpected error during quotation submission: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': f'An unexpected error occurred: {str(e)}',
            'error_detail': str(e)
        }, status=500)


# ============================================================================
# API ENDPOINTS
# ============================================================================

def get_quotation_items_api(request):
    """API endpoint to get items for quotation form"""
    try:
        items = Item.objects.filter(is_active=True).order_by('name')
        
        items_data = []
        for item in items:
            items_data.append({
                'id': item.id,
                'name': item.name,
                'unit_of_measure': item.unit_of_measure,
                'mrp': float(item.mrp) if item.mrp else 0,
                'purchase_price': float(item.purchase_price) if item.purchase_price else 0,
                'cost': float(item.cost) if item.cost else 0,
                'tax_percentage': float(item.tax_percentage) if item.tax_percentage else 0,
                'hsn_code': item.hsn_code or '',
                'description': item.description or '',
                'section': item.section,
                'department': item.department.name if item.department else 'N/A'
            })
        
        return JsonResponse({
            'success': True,
            'items': items_data
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


def quotation_detail_api(request, quotation_id):
    """
    API endpoint to get quotation details
    """
    try:
        quotation = get_object_or_404(
            Quotation.objects.prefetch_related('items'),
            id=quotation_id
        )
        
        # Build quotation data
        quotation_data = {
            'id': quotation.id,
            'quotation_number': quotation.quotation_number,
            'client_name': quotation.client_name,
            'client_phone': quotation.client_phone,
            'client_email': quotation.client_email or '',
            'company_name': quotation.company_name or '',
            'quotation_date': quotation.quotation_date.strftime('%Y-%m-%d'),
            'valid_until': quotation.valid_until.strftime('%Y-%m-%d'),
            'status': quotation.status,
            'status_display': quotation.get_status_display(),
            'subtotal': float(quotation.subtotal),
            'total_discount': float(quotation.total_discount),
            'total_tax': float(quotation.total_tax),
            'grand_total': float(quotation.grand_total),
            'notes': quotation.notes or '',
            'created_at': quotation.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'items': []
        }
        
        # Add lead info if available
        if quotation.lead:
            quotation_data['lead'] = {
                'id': quotation.lead.id,
                'ticket_number': quotation.lead.ticket_number,
                'priority': quotation.lead.priority,
            }
        
        # Add items
        for item in quotation.items.all():
            quotation_data['items'].append({
                'id': item.id,
                'item_name': item.item_name,
                'description': item.description or '',
                'quantity': float(item.quantity),
                'unit': item.unit,
                'entry_rate': float(item.entry_rate),
                'sales_price': float(item.sales_price),
                'unit_price': float(item.unit_price),
                'discount_percentage': float(item.discount_percentage),
                'tax_percentage': float(item.tax_percentage),
                'line_total': float(item.line_total),
                'hsn_code': item.hsn_code or '',
            })
        
        return JsonResponse({
            'success': True,
            'quotation': quotation_data
        })
        
    except Quotation.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Quotation not found'
        }, status=404)
    
    except Exception as e:
        logger.error(f"Error getting quotation details: {e}")
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)


@csrf_exempt
def quotation_delete(request, quotation_id):
    """
    Delete a quotation
    """
    if request.method != 'DELETE':
        return JsonResponse({
            'success': False,
            'message': 'Invalid request method. Use DELETE.'
        }, status=405)
    
    try:
        quotation = get_object_or_404(Quotation, id=quotation_id)
        quotation_number = quotation.quotation_number
        
        # Delete quotation (items will be cascade deleted)
        quotation.delete()
        
        logger.info(f"✅ Deleted quotation: {quotation_number}")
        
        return JsonResponse({
            'success': True,
            'message': f'Quotation {quotation_number} deleted successfully'
        })
        
    except Quotation.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': f'Quotation {quotation_id} not found'
        }, status=404)
        
    except Exception as e:
        logger.error(f"Error deleting quotation: {e}")
        return JsonResponse({
            'success': False,
            'message': f'Error deleting quotation: {str(e)}'
        }, status=500)


@csrf_exempt
def quotation_update_status(request, quotation_id):
    """
    Update quotation status
    """
    if request.method != 'POST':
        return JsonResponse({
            'success': False,
            'message': 'Invalid request method'
        }, status=405)
    
    try:
        data = json.loads(request.body)
        new_status = data.get('status')
        
        if not new_status:
            return JsonResponse({
                'success': False,
                'message': 'Status is required'
            }, status=400)
        
        quotation = get_object_or_404(Quotation, id=quotation_id)
        old_status = quotation.status
        quotation.status = new_status
        quotation.save()
        
        logger.info(f"✅ Updated quotation {quotation.quotation_number} status: {old_status} → {new_status}")
        
        return JsonResponse({
            'success': True,
            'message': f'Status updated to {new_status}',
            'status': new_status
        })
        
    except Exception as e:
        logger.error(f"Error updating quotation status: {e}")
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)
    
    # views.py
def edit_quotation(request, quotation_id):
    try:
        quotation = Quotation.objects.get(id=quotation_id)
        quotation_items = QuotationItem.objects.filter(quotation=quotation)
        items = Item.objects.all()  # From purchase order app
        leads = Lead.objects.filter(status='Active')
        
        context = {
            'quotation': quotation,
            'quotation_items': quotation_items,
            'items': items,
            'active_leads': leads,
            'leads_count': leads.count(),
        }
        return render(request, 'quotation_edit.html', context)
    except Quotation.DoesNotExist:
        messages.error(request, 'Quotation not found')
        return redirect('app5:quotation_list')
    
def update_quotation(request, pk):
    """
    Update quotation via AJAX - FIXED VERSION
    Properly handles form data and saves all changes
    """
    if request.method != 'POST':
        return JsonResponse({
            'success': False,
            'message': 'Invalid request method. Use POST.'
        }, status=405)
    
    try:
        # ========== PARSE REQUEST DATA ==========
        try:
            data = json.loads(request.body)
            logger.info(f"📝 Updating quotation {pk}")
            logger.debug(f"Received data: {data}")
        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON decode error: {e}")
            return JsonResponse({
                'success': False,
                'message': 'Invalid JSON data'
            }, status=400)
        
        # ========== GET QUOTATION ==========
        try:
            quotation = Quotation.objects.select_related('lead').get(id=pk)
            logger.info(f"✅ Found quotation: {quotation.quotation_number}")
        except Quotation.DoesNotExist:
            logger.error(f"❌ Quotation {pk} not found")
            return JsonResponse({
                'success': False,
                'message': f'Quotation with ID {pk} not found'
            }, status=404)
        
        # ========== START ATOMIC TRANSACTION ==========
        with transaction.atomic():
            # ---------- UPDATE LEAD (if changed) ----------
            lead_id = data.get('lead_id')
            if lead_id and str(lead_id) != str(quotation.lead.id if quotation.lead else None):
                try:
                    new_lead = Lead.objects.get(id=lead_id)
                    old_lead_name = quotation.lead.ownerName if quotation.lead else "Unknown"
                    
                    quotation.lead = new_lead
                    quotation.client_name = new_lead.ownerName or ''
                    quotation.client_phone = new_lead.phoneNo or ''
                    quotation.client_email = new_lead.email or ''
                    
                    if new_lead.customerType == 'Business':
                        quotation.company_name = new_lead.business or new_lead.name or ''
                    
                    logger.info(f"✅ Lead changed: {old_lead_name} → {new_lead.ownerName}")
                except Lead.DoesNotExist:
                    logger.warning(f"⚠️ Lead {lead_id} not found, keeping existing lead")
                    return JsonResponse({
                        'success': False,
                        'message': f'Lead with ID {lead_id} not found'
                    }, status=404)
            
            # ---------- UPDATE NOTES ----------
            if 'notes' in data:
                quotation.notes = data.get('notes', '').strip()
                logger.debug("✅ Updated notes")
            
            # ---------- UPDATE STATUS ----------
            new_status = data.get('status')
            if new_status and new_status in ['draft', 'sent', 'accepted', 'expired']:
                quotation.status = new_status
                logger.info(f"✅ Status updated to: {new_status}")
            
            # ---------- HANDLE DELETED ITEMS ----------
            deleted_items = data.get('deleted_items', [])
            deleted_count = 0
            
            # Clean up deleted_items array
            deleted_items = [str(item_id) for item_id in deleted_items if item_id not in [None, '', 'null', 'undefined']]
            
            for item_id in deleted_items:
                try:
                    item_id_int = int(item_id)
                    quotation_item = QuotationItem.objects.get(
                        id=item_id_int, 
                        quotation=quotation
                    )
                    item_name = quotation_item.item_name
                    quotation_item.delete()
                    deleted_count += 1
                    logger.info(f"🗑️ Deleted item: {item_name} (ID: {item_id})")
                except (ValueError, TypeError):
                    logger.warning(f"⚠️ Invalid item ID format: {item_id}")
                    continue
                except QuotationItem.DoesNotExist:
                    logger.warning(f"⚠️ Item {item_id} not found for deletion")
                    continue
            
            if deleted_count > 0:
                logger.info(f"✅ Deleted {deleted_count} item(s)")
            
            # ---------- PROCESS ITEMS ----------
            items_data = data.get('items', [])
            logger.info(f"📦 Processing {len(items_data)} items")
            
            # Track processed items
            existing_item_ids = set(
                QuotationItem.objects.filter(quotation=quotation)
                .values_list('id', flat=True)
            )
            updated_item_ids = set()
            created_count = 0
            updated_count = 0
            
            # Process each item
            for index, item_data in enumerate(items_data):
                try:
                    quotation_item_id = item_data.get('id')
                    item_object_id = item_data.get('item_id')
                    
                    logger.debug(f"Item {index+1}: quotation_item_id={quotation_item_id}, item_object_id={item_object_id}")
                    
                    # ========== VALIDATION ==========
                    if not item_object_id:
                        logger.warning(f"⚠️ Skipping item {index+1}: No item_object_id")
                        continue
                    
                    # Get the Item object
                    try:
                        item = Item.objects.get(id=item_object_id)
                    except Item.DoesNotExist:
                        logger.error(f"❌ Item {item_object_id} not found in purchase_order")
                        continue
                    
                    # ========== EXTRACT VALUES ==========
                    try:
                        quantity = Decimal(str(item_data.get('quantity', 1)))
                        entry_rate = Decimal(str(item_data.get('entry_rate', 0)))
                        sales_price = Decimal(str(item_data.get('sales_price', 0)))
                        unit_price = Decimal(str(item_data.get('unit_price', 0)))
                        discount = Decimal(str(item_data.get('discount', 0)))
                        tax = Decimal(str(item_data.get('tax', 0)))
                        total = Decimal(str(item_data.get('total', 0)))
                        
                        # Validate values
                        if quantity <= 0:
                            logger.warning(f"⚠️ Invalid quantity for item {index+1}: {quantity}")
                            continue
                        
                        if sales_price <= 0 and unit_price <= 0:
                            logger.warning(f"⚠️ Both prices are 0 for item {index+1}, using MRP")
                            sales_price = Decimal(str(item.mrp or 0))
                        
                    except (ValueError, TypeError, InvalidOperation) as e:
                        logger.error(f"❌ Error parsing numbers for item {index+1}: {e}")
                        continue
                    
                    # ========== CALCULATE ADDITIONAL FIELDS ==========
                    base_price = sales_price if sales_price > 0 else unit_price
                    discount_amount = (base_price * quantity) * (discount / 100) if discount > 0 else Decimal('0')
                    amount_after_discount = (base_price * quantity) - discount_amount
                    tax_amount = amount_after_discount * (tax / 100) if tax > 0 else Decimal('0')
                    
                    # Prepare item values
                    item_values = {
                        'item': item,
                        'item_name': item.name,
                        'description': item.description or '',
                        'quantity': quantity,
                        'unit': item.unit_of_measure,
                        'entry_rate': entry_rate,
                        'sales_price': sales_price,
                        'unit_price': unit_price,
                        'discount_percentage': discount,
                        'tax_percentage': tax,
                        'line_total': total,
                        'discount_amount': discount_amount,
                        'tax_amount': tax_amount,
                        'hsn_code': item.hsn_code or '',
                        'order': index
                    }
                    
                    # ========== CREATE OR UPDATE ITEM ==========
                    if quotation_item_id and str(quotation_item_id).isdigit():
                        # UPDATE EXISTING ITEM
                        try:
                            quotation_item = QuotationItem.objects.get(
                                id=int(quotation_item_id),
                                quotation=quotation
                            )
                            
                            # Update all fields
                            for key, value in item_values.items():
                                setattr(quotation_item, key, value)
                            
                            quotation_item.save()
                            updated_item_ids.add(int(quotation_item_id))
                            updated_count += 1
                            
                            logger.debug(f"✅ Updated item {index+1}: {item.name}")
                            
                        except QuotationItem.DoesNotExist:
                            # Item was supposed to exist but doesn't - create new
                            logger.warning(f"⚠️ QuotationItem {quotation_item_id} not found, creating new")
                            quotation_item = QuotationItem.objects.create(
                                quotation=quotation,
                                **item_values
                            )
                            updated_item_ids.add(quotation_item.id)
                            created_count += 1
                            logger.info(f"✅ Created new item {index+1}: {item.name}")
                    else:
                        # CREATE NEW ITEM
                        quotation_item = QuotationItem.objects.create(
                            quotation=quotation,
                            **item_values
                        )
                        updated_item_ids.add(quotation_item.id)
                        created_count += 1
                        logger.info(f"✅ Created new item {index+1}: {item.name}")
                
                except Exception as e:
                    logger.error(f"❌ Error processing item {index+1}: {e}", exc_info=True)
                    continue
            
            # ---------- DELETE ORPHANED ITEMS ----------
            # Items that existed but aren't in the updated list
            deleted_item_ids = set(int(x) for x in deleted_items if str(x).isdigit())
            orphaned_items = existing_item_ids - updated_item_ids - deleted_item_ids
            
            if orphaned_items:
                orphan_count = 0
                for item_id in orphaned_items:
                    try:
                        orphan_item = QuotationItem.objects.get(id=item_id, quotation=quotation)
                        orphan_name = orphan_item.item_name
                        orphan_item.delete()
                        orphan_count += 1
                        logger.info(f"🗑️ Deleted orphaned item: {orphan_name} (ID: {item_id})")
                    except QuotationItem.DoesNotExist:
                        pass
                
                if orphan_count > 0:
                    logger.info(f"✅ Deleted {orphan_count} orphaned item(s)")
            
            # ---------- RECALCULATE TOTALS ----------
            subtotal = Decimal(str(data.get('subtotal', 0)))
            total_discount = Decimal(str(data.get('total_discount', 0)))
            total_tax = Decimal(str(data.get('total_tax', 0)))
            grand_total = Decimal(str(data.get('grand_total', 0)))
            
            # If totals are 0, recalculate from items
            if grand_total <= 0:
                quotation_items = QuotationItem.objects.filter(quotation=quotation)
                
                if quotation_items.exists():
                    subtotal = Decimal('0')
                    total_discount = Decimal('0')
                    total_tax = Decimal('0')
                    
                    for item in quotation_items:
                        item_subtotal = item.line_total / (1 + item.tax_percentage/100) if item.tax_percentage else item.line_total
                        subtotal += item_subtotal
                        total_discount += item.discount_amount
                        total_tax += item.tax_amount
                    
                    grand_total = subtotal + total_tax
                    
                    logger.info(f"💰 Recalculated totals - Subtotal: ₹{subtotal:.2f}, Tax: ₹{total_tax:.2f}, Grand Total: ₹{grand_total:.2f}")
                else:
                    subtotal = Decimal('0')
                    total_discount = Decimal('0')
                    total_tax = Decimal('0')
                    grand_total = Decimal('0')
                    logger.warning("⚠️ No items in quotation after update")
            
            # Update quotation totals
            quotation.subtotal = subtotal
            quotation.total_discount = total_discount
            quotation.total_tax = total_tax
            quotation.grand_total = grand_total
            
            # Save quotation
            quotation.updated_at = timezone.now()
            quotation.save()
            
            logger.info(f"✅ Quotation {quotation.quotation_number} updated successfully")
            logger.info(f"📊 Summary - Created: {created_count}, Updated: {updated_count}, Deleted: {deleted_count}")
        
        # ========== SUCCESS RESPONSE ==========
        return JsonResponse({
            'success': True,
            'message': '✅ Quotation updated successfully',
            'quotation': {
                'id': quotation.id,
                'quotation_number': quotation.quotation_number,
                'status': quotation.status,
                'subtotal': float(quotation.subtotal),
                'total_discount': float(quotation.total_discount),
                'total_tax': float(quotation.total_tax),
                'grand_total': float(quotation.grand_total),
                'items_count': QuotationItem.objects.filter(quotation=quotation).count(),
                'updated_at': quotation.updated_at.isoformat() if quotation.updated_at else timezone.now().isoformat()
            },
            'summary': {
                'items_created': created_count,
                'items_updated': updated_count,
                'items_deleted': deleted_count + len(orphaned_items) if 'orphaned_items' in locals() else deleted_count
            }
        })
        
    except Exception as e:
        logger.error(f"❌ Error updating quotation {pk}: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': f'Error updating quotation: {str(e)}',
            'error_type': type(e).__name__
        }, status=500)



def download_quotation(request, quotation_id):
    quotation = get_object_or_404(Quotation, id=quotation_id)
    
    # Get branch/department ID from request parameter
    branch_id = request.GET.get('branch_id') or request.GET.get('department_id')
    branch = None
    
    # Try to get department from purchase_order app
    try:
        from purchase_order.models import Department
        
        if branch_id and branch_id.isdigit():
            # Try to get the selected department
            try:
                department = Department.objects.get(id=int(branch_id), is_active=True)
                branch = {
                    'id': department.id,
                    'name': department.name,
                    'code': f"DEPT-{department.id:03d}",
                    'address': department.address or '',
                    'city': department.city or '',
                    'state': department.state or '',
                    'pincode': department.pincode or '',
                    'contact_number': department.contact_number or '',
                    'alternate_number': department.alternate_number or '',
                    'email': department.email or '',
                    'gst_number': department.gst_number or '',
                    # ✅ FIXED: Properly handle logo URL
                    'logo_url': department.logo.url if department.logo else '',
                    'has_logo': bool(department.logo),
                    'type': 'department',
                }
            except Department.DoesNotExist:
                branch = get_default_department()
        else:
            branch = get_default_department()
            
    except ImportError:
        branch = get_fallback_branch(branch_id)
    
    # Get all items for this quotation
    items = quotation.items.all()
    
    # Calculate totals (existing code)
    subtotal = 0
    total_tax = 0
    grand_total = 0
    
    for item in items:
        sale_price = getattr(item, 'sales_price', 0) or 0
        quantity = getattr(item, 'quantity', 1) or 1
        item_total = quantity * sale_price
        subtotal += item_total
        
        if hasattr(item, 'tax_percentage'):
            tax_percentage = getattr(item, 'tax_percentage', 0) or 0
            item_tax = (item_total * tax_percentage) / 100
            total_tax += item_tax
    
    discount_amount = getattr(quotation, 'discount_amount', 0) or 0
    shipping_charges = getattr(quotation, 'shipping_charges', 0) or 0
    grand_total = subtotal + total_tax - discount_amount + shipping_charges
    
    def format_currency(value):
        return f"₹{value:,.2f}"
    
    # Build complete address string
    if branch:
        address_parts = []
        if branch.get('address'):
            address_parts.append(branch['address'])
        if branch.get('city'):
            address_parts.append(branch['city'])
        if branch.get('state'):
            address_parts.append(branch['state'])
        if branch.get('pincode'):
            address_parts.append(f"PIN: {branch['pincode']}")
        
        branch['full_address_display'] = ', '.join(address_parts)
        
        contact_info = []
        if branch.get('contact_number'):
            contact_info.append(f"📞 {branch['contact_number']}")
        if branch.get('alternate_number'):
            contact_info.append(f" / {branch['alternate_number']}")
        if branch.get('email'):
            contact_info.append(f"✉️ {branch['email']}")
        if branch.get('gst_number'):
            contact_info.append(f"📋 GST: {branch['gst_number']}")
        
        branch['contact_info'] = ' | '.join(contact_info)
    
    context = {
        'quotation': quotation,
        'branch': branch,
        'items': items,
        'subtotal': format_currency(subtotal),
        'subtotal_raw': subtotal,
        'total_tax': format_currency(total_tax),
        'total_tax_raw': total_tax,
        'discount_amount': format_currency(discount_amount),
        'discount_amount_raw': discount_amount,
        'shipping_charges': format_currency(shipping_charges) if shipping_charges > 0 else None,
        'shipping_charges_raw': shipping_charges,
        'grand_total': format_currency(grand_total),
        'grand_total_raw': grand_total,
        'item_count': items.count(),
        'today': timezone.now().date(),
        'valid_until': getattr(quotation, 'valid_until', None) or (timezone.now() + timezone.timedelta(days=30)).date(),
        'quotation_number': getattr(quotation, 'quotation_number', f"QT-{quotation.id:06d}"),
        'client_name': getattr(quotation, 'client_name', ''),
        'client_email': getattr(quotation, 'client_email', ''),
        'client_phone': getattr(quotation, 'client_phone', ''),
        'client_address': getattr(quotation, 'client_address', ''),
        'company_name': branch['name'] if branch else 'Our Company',
        'company_address': branch.get('full_address_display', '') if branch else '',
        'company_contact': branch.get('contact_info', '') if branch else '',
        'company_gst': branch.get('gst_number', '') if branch else '',
    }
    
    return render(request, 'quotation_download.html', context)


def get_default_department():
    """Get the default/fallback department from database"""
    try:
        from purchase_order.models import Department
        
        default_dept = Department.objects.filter(is_active=True).first()
        
        if default_dept:
            return {
                'id': default_dept.id,
                'name': default_dept.name,
                'code': f"DEPT-{default_dept.id:03d}",
                'address': default_dept.address or '',
                'city': default_dept.city or '',
                'state': default_dept.state or '',
                'pincode': default_dept.pincode or '',
                'contact_number': default_dept.contact_number or '',
                'alternate_number': default_dept.alternate_number or '',
                'email': default_dept.email or '',
                'gst_number': default_dept.gst_number or '',
                # ✅ FIXED: Properly handle logo URL
                'logo_url': default_dept.logo.url if default_dept.logo else '',
                'has_logo': bool(default_dept.logo),
                'type': 'department',
            }
    except (ImportError, AttributeError):
        pass
    
    return {
        'name': 'Main Branch',
        'code': 'BR-001',
        'address': '123 Business Street',
        'city': 'City',
        'state': 'State',
        'contact_number': '+91 1234567890',
        'email': 'info@company.com',
        'gst_number': 'GSTINXXXXXXX',
        'logo_url': '',
        'has_logo': False,
        'type': 'default',
    }


def get_fallback_branch(branch_id=None):
    """Fallback branch data when purchase_order app is not available"""
    BRANCHES_DATA = {
        1: {
            'name': 'Main Branch',
            'code': 'BR-001',
            'address': '123 Business Street, City, State 12345',
            'contact_number': '+1 (123) 456-7890',
            'email': 'main@company.com',
            'gst_number': 'GSTINXXXXXXX',
            'type': 'fallback',
        },
        2: {
            'name': 'North Branch',
            'code': 'BR-002',
            'address': '456 North Avenue, Industrial Zone, Delhi 110001',
            'contact_number': '+91 9876543210',
            'email': 'north@company.com',
            'gst_number': 'GSTINXXXXXXX',
            'type': 'fallback',
        },
        3: {
            'name': 'South Branch',
            'code': 'BR-003',
            'address': '789 South Road, Commercial Area, Bangalore 560001',
            'contact_number': '+91 8765432109',
            'email': 'south@company.com',
            'gst_number': 'GSTINXXXXXXX',
            'type': 'fallback',
        },
    }
    
    if branch_id and branch_id.isdigit() and int(branch_id) in BRANCHES_DATA:
        return BRANCHES_DATA[int(branch_id)]
    
    # Default to main branch
    return BRANCHES_DATA.get(1)


def generate_quotation_pdf(context):
    """Generate PDF version of the quotation"""
    from django.http import HttpResponse
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import inch
    from io import BytesIO
    
    # Create a file-like buffer to receive PDF data
    buffer = BytesIO()
    
    # Create the PDF object
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    # Set up document
    p.setTitle(f"Quotation {context.get('quotation_number', '')}")
    
    # Header
    p.setFont("Helvetica-Bold", 16)
    p.drawString(50, height - 50, "QUOTATION")
    p.setFont("Helvetica", 10)
    p.drawString(50, height - 70, f"Quotation #: {context.get('quotation_number', '')}")
    p.drawString(50, height - 85, f"Date: {context.get('today', '').strftime('%d/%m/%Y')}")
    
    # Company/Branch Info
    if context.get('branch'):
        p.setFont("Helvetica-Bold", 12)
        p.drawString(50, height - 120, f"{context['branch'].get('name', '')}")
        p.setFont("Helvetica", 10)
        
        y = height - 135
        if context['branch'].get('full_address_display'):
            p.drawString(50, y, context['branch']['full_address_display'])
            y -= 15
        if context['branch'].get('contact_number'):
            p.drawString(50, y, f"Phone: {context['branch']['contact_number']}")
            y -= 15
        if context['branch'].get('email'):
            p.drawString(50, y, f"Email: {context['branch']['email']}")
            y -= 15
        if context['branch'].get('gst_number'):
            p.drawString(50, y, f"GST: {context['branch']['gst_number']}")
    
    # Client Info
    p.setFont("Helvetica-Bold", 12)
    p.drawString(300, height - 120, "BILL TO:")
    p.setFont("Helvetica", 10)
    p.drawString(300, height - 135, f"{context.get('client_name', '')}")
    
    y = height - 150
    if context.get('client_address'):
        p.drawString(300, y, context['client_address'])
        y -= 15
    if context.get('client_phone'):
        p.drawString(300, y, f"Phone: {context['client_phone']}")
        y -= 15
    if context.get('client_email'):
        p.drawString(300, y, f"Email: {context['client_email']}")
    
    # Table Header
    p.setFont("Helvetica-Bold", 10)
    y_table_start = height - 220
    
    p.drawString(50, y_table_start, "Item")
    p.drawString(250, y_table_start, "Quantity")
    p.drawString(320, y_table_start, "Price")
    p.drawString(380, y_table_start, "Tax")
    p.drawString(450, y_table_start, "Total")
    
    p.line(50, y_table_start - 5, 550, y_table_start - 5)
    
    # Items
    p.setFont("Helvetica", 9)
    y_current = y_table_start - 20
    
    for item in context['items']:
        item_name = getattr(item, 'name', f"Item {item.id}")
        quantity = getattr(item, 'quantity', 1)
        price = getattr(item, 'sales_price', 0) or 0
        tax_percent = getattr(item, 'tax_percentage', 0) or 0
        item_total = quantity * price
        item_tax = (item_total * tax_percent) / 100
        
        # Truncate long item names
        if len(item_name) > 30:
            item_name = item_name[:27] + "..."
        
        p.drawString(50, y_current, item_name)
        p.drawString(250, y_current, str(quantity))
        p.drawString(320, y_current, f"₹{price:,.2f}")
        p.drawString(380, y_current, f"{tax_percent}%")
        p.drawString(450, y_current, f"₹{item_total:,.2f}")
        
        y_current -= 15
        
        # Check for page break
        if y_current < 100:
            p.showPage()
            p.setFont("Helvetica", 9)
            y_current = height - 50
    
    # Totals
    y_totals = y_current - 30
    
    p.setFont("Helvetica-Bold", 10)
    p.drawString(350, y_totals, "Subtotal:")
    p.drawString(450, y_totals, context['subtotal'])
    
    y_totals -= 15
    p.drawString(350, y_totals, "Tax:")
    p.drawString(450, y_totals, context['total_tax'])
    
    if context.get('discount_amount_raw', 0) > 0:
        y_totals -= 15
        p.drawString(350, y_totals, "Discount:")
        p.drawString(450, y_totals, f"-{context['discount_amount']}")
    
    if context.get('shipping_charges_raw', 0) > 0:
        y_totals -= 15
        p.drawString(350, y_totals, "Shipping:")
        p.drawString(450, y_totals, context['shipping_charges'])
    
    y_totals -= 20
    p.setFont("Helvetica-Bold", 12)
    p.drawString(350, y_totals, "GRAND TOTAL:")
    p.drawString(450, y_totals, context['grand_total'])
    
    # Footer
    p.setFont("Helvetica", 8)
    p.drawString(50, 50, "Terms & Conditions:")
    p.drawString(50, 40, "1. Prices are valid for 30 days")
    p.drawString(50, 30, "2. Payment terms: Net 30")
    p.drawString(50, 20, "3. All taxes applicable")
    
    # Validity
    p.drawString(400, 30, f"Valid Until: {context.get('valid_until', '').strftime('%d/%m/%Y')}")
    
    # Close the PDF object cleanly
    p.showPage()
    p.save()
    
    # FileResponse with PDF content
    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    filename = f"quotation_{context.get('quotation_number', quotation_id)}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    return response

    # app5/views.py
# app5/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from .models import Lead

@login_required
def lead_view_detail(request, pk):
    """View-only page for lead details"""
    lead = get_object_or_404(Lead, pk=pk)
    
    # Get user details for marketed_by
    marketed_by_user = None
    if lead.marketedBy:
        try:
            User = get_user_model()
            marketed_by_user = User.objects.filter(name=lead.marketedBy).first()
        except:
            marketed_by_user = None
    
    # Get requirements data
    requirements_data = []
    requirement_ids = []
    
    # Try to get from JSON field first
    if hasattr(lead, 'requirement_details_json') and lead.requirement_details_json:
        import json
        try:
            raw_requirements = json.loads(lead.requirement_details_json)
            # Process and calculate totals
            for req in raw_requirements:
                price = float(req.get('price', 0) or 0)
                quantity = int(req.get('quantity', 1) or 1)
                total = float(req.get('total', 0) or (price * quantity))
                
                requirements_data.append({
                    'item_id': req.get('item_id', ''),
                    'item_name': req.get('item_name', req.get('name', 'Unknown Item')),
                    'section': req.get('section', 'GENERAL'),
                    'unit': req.get('unit', 'pcs'),
                    'price': price,
                    'quantity': quantity,
                    'total': total,
                    'price_display': f"{price:.2f}",
                    'total_display': f"{total:.2f}",
                })
                if req.get('item_id'):
                    requirement_ids.append(str(req['item_id']))
        except:
            requirements_data = []
    
    # Try to get from related model
    elif hasattr(lead, 'requirements') and hasattr(lead.requirements, 'all'):
        raw_requirements = list(lead.requirements.all().values(
            'id', 'item_id', 'item_name', 'section', 'unit', 
            'price', 'quantity', 'total', 'created_at'
        ))
        for req in raw_requirements:
            price = float(req.get('price', 0) or 0)
            quantity = int(req.get('quantity', 1) or 1)
            total = float(req.get('total', 0) or (price * quantity))
            
            requirements_data.append({
                'item_id': req.get('item_id', ''),
                'item_name': req.get('item_name', 'Unknown Item'),
                'section': req.get('section', 'GENERAL'),
                'unit': req.get('unit', 'pcs'),
                'price': price,
                'quantity': quantity,
                'total': total,
                'price_display': f"{price:.2f}",
                'total_display': f"{total:.2f}",
            })
            requirement_ids.append(str(req.get('id', '')))
    
    # Calculate grand total
    grand_total = 0
    if requirements_data:
        grand_total = sum(req['total'] for req in requirements_data)
    
    # Get all models safely
    try:
        from app5.models import (
            Department, BusinessNature, State, District, 
            Reference, Campaign, Item, Section
        )
        
        # Get all related data
        departments = Department.objects.all().order_by('name')
        business_natures = BusinessNature.objects.all().order_by('name')
        states = State.objects.all().order_by('name')
        districts = District.objects.all().order_by('name')
        references = Reference.objects.all().order_by('ref_name')
        campaigns = Campaign.objects.all().order_by('campaign_name')
        
        # Get active users
        User = get_user_model()
        active_users = User.objects.filter(is_active=True).order_by('name')
        
        # Get existing firms (including the current lead's firm)
        existing_firms = Lead.objects.filter(
            customerType='Business'
        ).exclude(name__isnull=True).exclude(name='').values_list('name', flat=True).distinct().order_by('name')
        
        # Get items organized by section for requirements
        items_by_section = {}
        try:
            # Get all sections
            sections = Section.objects.all().order_by('name')
            for section in sections:
                # Get items for this section
                items = Item.objects.filter(section=section).order_by('name')
                if items.exists():
                    items_by_section[section.name] = items
        except:
            # If Section model doesn't exist, fall back to grouping by item section field
            items = Item.objects.all().order_by('name')
            for item in items:
                section_name = getattr(item, 'section', 'GENERAL')
                if not section_name:
                    section_name = 'GENERAL'
                
                if section_name not in items_by_section:
                    items_by_section[section_name] = []
                items_by_section[section_name].append(item)
        
    except Exception as e:
        print(f"Error loading data: {e}")
        departments = []
        business_natures = []
        states = []
        districts = []
        references = []
        campaigns = []
        active_users = []
        existing_firms = []
        items_by_section = {}
    
    # Add API data (if applicable)
    api_customer_data = []
    try:
        # If you have API integration, add your API data fetching logic here
        # For now, we'll leave it empty
        pass
    except:
        api_customer_data = []
    
    # Debug: Print lead data to console
    print(f"Lead Name: {lead.name}")
    print(f"Lead ID: {lead.id}")
    print(f"Lead Type: {lead.customerType}")
    print(f"Owner Name: {lead.ownerName}")
    
    context = {
        'lead': lead,
        'marketed_by_user': marketed_by_user,
        'requirements_data': requirements_data,
        'requirement_ids': ','.join(requirement_ids),
        'grand_total': f"{grand_total:.2f}",
        'is_view_mode': True,
        
        # Form data
        'departments': departments,
        'business_natures': business_natures,
        'states': states,
        'districts': districts,
        'references': references,
        'campaigns': campaigns,
        'active_users': active_users,
        'existing_firms': existing_firms,
        'items_by_section': items_by_section,
        
        # API data
        'api_customer_data': api_customer_data,
        'api_data_count': len(api_customer_data),
        
        # User permissions
        'can_edit': request.user.has_perm('app5.change_lead') or request.user == lead.created_by,
        'can_delete': request.user.has_perm('app5.delete_lead') or request.user == lead.created_by,
    }
    
    return render(request, 'lead_view.html', context)