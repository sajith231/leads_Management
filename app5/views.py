# views.py (updated)

# At the top of views.py, add these imports
from .models import (
    JobCard, JobCardImage, Item, Supplier, 
    WarrantyTicket, WarrantyItemLog, StandbyIssuance,
    ServiceBilling, ServiceItem  # Add these
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

    # ✅ GET Request - USE PURCHASE_ORDER ITEMS
    try:
        # Get items from purchase_order app
        purchase_items = PurchaseItem.objects.filter(is_active=True).order_by('name')
        
        # Get departments for filtering (optional)
        departments = Department.objects.filter(is_active=True).order_by('name')
        
    except Exception as e:
        logger.error(f"Error loading purchase items: {e}")
        # Fallback to app5 items if purchase_order is not available
        from .models import Item as App5Item
        purchase_items = App5Item.objects.filter(is_active=True).order_by('name')
        departments = []
    
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
        'items': purchase_items,  # ✅ Using purchase_order items
        'departments': departments,  # ✅ Optional: for filtering
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
                f"✅ Deleted complete ticket <strong>{ticket_no}</strong> "
                f"for customer <strong>{customer_name}</strong> (Phone: {customer_phone}).<br>"
                f"📋 Deleted {deleted_count} job card(s) for items: <strong>{', '.join(set(deleted_items))}</strong>"
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

        items = request.POST.getlist("items[]")
        serials = request.POST.getlist("serials[]")
        configs = request.POST.getlist("configs[]")

        items_data = []

        for idx, item_name in enumerate(items):
            if not item_name.strip():
                continue

            item_entry = {
                "item": item_name,
                "serial": serials[idx] if idx < len(serials) else "",
                "config": configs[idx] if idx < len(configs) else "",
                "complaints": []
            }

            complaint_descriptions = request.POST.getlist(f"complaints-{idx}[]")
            complaint_notes = request.POST.getlist(f"complaint_notes-{idx}[]")

            for c_idx, description in enumerate(complaint_descriptions):
                if not description.strip():
                    continue
                complaint_entry = {
                    "description": description,
                    "notes": complaint_notes[c_idx] if c_idx < len(complaint_notes) else "",
                    "images": []
                }

                # handle newly uploaded images
                new_images = request.FILES.getlist(f"new_images-{idx}[]")
                for image in new_images:
                    img_obj = JobCardImage.objects.create(
                        jobcard=jobcard,
                        image=image,
                        item_index=idx,
                        complaint_index=c_idx
                    )
                    complaint_entry["images"].append(img_obj.image.url)

                item_entry["complaints"].append(complaint_entry)

            items_data.append(item_entry)

        jobcard.items_data = items_data
        jobcard.save()

        messages.success(request, "Job card updated successfully.")
        return redirect("app5:jobcard_edit", pk=jobcard.pk)

    # --- GET: Show form ---
    # prepare structured items for template
    structured_items = []
    for idx, item in enumerate(jobcard.items_data or []):
        structured_items.append({
            "name": item.get("item", ""),
            "serial": item.get("serial", ""),
            "config": item.get("config", ""),
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

        # ✅ Check only letters/numbers allowed
        import re
        if not re.match(r'^[A-Z0-9 ]+$', name):
            messages.error(request, "Item name must contain only CAPITAL letters and numbers.")
            return redirect("app5:add_item")

        # ✅ Prevent duplicate
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

        # ✅ Check duplicates (exclude current item)
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

# ✅ Updated WhatsApp API credentials
WHATSAPP_API_SECRET = '7b8ae820ecb39f8d173d57b51e1fce4c023e359e'
WHATSAPP_API_ACCOUNT = '1761365422812b4ba287f5ee0bc9d43bbf5bbe87fb68fc4daea92d8'

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
            
            # ✅ SET THE ASSIGNED DATE WHEN ASSIGNING TO TECHNICIAN
            if not jobcard.assigned_date:  # Only set if not already set
                jobcard.assigned_date = timezone.now()
            
            # ✅ UPDATE INDIVIDUAL ITEM STATUSES TO 'sent_technician'
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
            # ✅ SET/UPDATE THE ASSIGNED DATE WHEN TECHNICIAN CHANGES
            jobcard.assigned_date = timezone.now()
        
        jobcard.status = status
        
        # ✅ UPDATE INDIVIDUAL ITEM STATUSES
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
from .models import JobCard, StandbyIssuance        # ✅ from app5
from app2.models import StandbyItem, StandbyImage
 # ✅ from app2
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
from .models import JobCard, JobCardImage, Item, StandbyIssuance          # ✅ only from app5
from app2.models import StandbyItem, StandbyImage
 # ✅ correct app for StandbyItem
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
    
    # ✅ FIXED: Get only "in_stock" standby items with only ORIGINAL images
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
        
        # ✅ UPDATE STANDBY ITEM WITH CUSTOMER DETAILS
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
        # ✅ Get return condition images - FIXED query
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
        # ✅ Get form data
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
            # ✅ Create StandbyReturn record FIRST
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
            
            # ✅ Save return images linked to the StandbyReturn record
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
            
            # ✅ Update item status and details AFTER creating return record
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
            
            # ✅ Try to find and update related issuance (if exists)
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
        
        # ✅ CHECK if is_active field exists
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
        
        # ✅ FILTER: Only include items with warranty='yes' AND not sent to supplier
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
            'items_data': filtered_items,  # ✅ Use filtered items
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
    ✅ USES ONLY purchase_order.Supplier
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
        
        # ✅ GET SUPPLIER FROM PURCHASE_ORDER MODEL
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
                logger.info(f"✅ Found supplier: ID={supplier.id}, Name={supplier.name}, Active={supplier.is_active}")
            else:
                # List all available suppliers for debugging
                all_suppliers = POSupplier.objects.all().values('id', 'name', 'is_active')
                logger.error(f"❌ Supplier {supplier_id} not found. Available suppliers: {list(all_suppliers)}")
                
                error_msg = (
                    f'Supplier with ID {supplier_id} not found. '
                    f'Available suppliers: {", ".join([f"ID {s["id"]}: {s["name"]}" for s in all_suppliers[:5]])}'
                )
                
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
            
            # Find the selected item details from items_data
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
            
            # Check if item has warranty
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
            
            # Update warranty status in items_data
            if item_index is not None and jobcard.items_data:
                jobcard.items_data[item_index]['warranty_status'] = 'sent_to_supplier'
                jobcard.items_data[item_index]['warranty_sent_date'] = timezone.now().isoformat()
                jobcard.items_data[item_index]['warranty_supplier'] = supplier.name
                jobcard.items_data[item_index]['warranty_ticket_no'] = new_ticket_no
                jobcard.items_data[item_index]['warranty_processed'] = True
            
            # ✅ Create warranty ticket with purchase_order supplier
            try:
                warranty_ticket = WarrantyTicket.objects.create(
                    ticket_no=new_ticket_no,
                    jobcard=jobcard,
                    supplier=supplier,  # This is purchase_order.Supplier
                    selected_item=selected_item,
                    item_serial=item_serial,
                    status='submitted',
                    issue_description=f"Warranty claim for {selected_item}",
                    submitted_at=timezone.now()
                )
                logger.info(f"✅ Created warranty ticket: {new_ticket_no}")
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
        
        # Send WhatsApp notification
        if created_tickets:
            try:
                items_list = "\n".join([f"• {item['name']}" for item in processed_items])
                message_text = (
                    f"🔧 *Warranty Items Sent to Supplier*\n\n"
                    f"*Job Card:* {jobcard.ticket_no}\n"
                    f"*Supplier:* {supplier.name}\n"
                    f"*Customer:* {jobcard.customer}\n"
                    f"*Items ({len(processed_items)}):*\n{items_list}\n"
                    f"*Warranty Tickets:* {', '.join(created_tickets)}\n"
                    f"*Date:* {timezone.now().strftime('%d-%m-%Y')}"
                )
                
                if duplicate_items:
                    duplicate_list = "\n".join([
                        f"• {item['item']} (Existing: {', '.join(item['existing_tickets'])})" 
                        for item in duplicate_items
                    ])
                    message_text += f"\n\n⚠️ *Duplicates Skipped:*\n{duplicate_list}"
                
                whatsapp_api_base = "https://app.dxing.in/api/send/whatsapp"
                params = {
                    "secret": "7b8ae820ecb39f8d173d57b51e1fce4c023e359e",
                    "account": "1756959119812b4ba287f5ee0bc9d43bbf5bbe87fb68b9118fcf1af",
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
                f'✅ Created {len(created_tickets)} warranty ticket(s) and sent to {supplier.name}'
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
    
    # ✅ FIXED: Get suppliers with proper error handling
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
        
        # ✅ UPDATE WARRANTY STATUS IN JOBCARD when status indicates return
        if new_status in ['completed', 'approved', 'returned']:
            warranty_ticket.resolved_at = timezone.now()
            
            jobcard = warranty_ticket.jobcard
            item_name = warranty_ticket.selected_item
            
            if hasattr(jobcard, 'items_data') and jobcard.items_data:
                for idx, item in enumerate(jobcard.items_data):
                    if item.get('item') == item_name:
                        # ✅ CHANGE STATUS FROM "sent_to_supplier" TO "returned_from_supplier"
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
        
        # ✅ NEW: Get return details if exists
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
            'return_details': return_details  # ✅ Add return details
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
            
            # ✅ UPDATE WARRANTY STATUS IN JOBCARD ITEMS_DATA
            jobcard = ticket.jobcard
            item_name = ticket.selected_item
            
            if hasattr(jobcard, 'items_data') and jobcard.items_data:
                for idx, item in enumerate(jobcard.items_data):
                    if item.get('item') == item_name:
                        # ✅ CHANGE STATUS FROM "sent_to_supplier" TO "returned_from_supplier"
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
                    
                    # ✅ FIXED: Use the correct model for return images
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
    ✅ FIXED: Amount determines service type (0 = Free, >0 = Payable)
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
            
            # ✅ FIXED: Amount determines service type
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
                
                # ✅ DETERMINE SERVICE TYPE BASED ON AMOUNT
                if charge == 0.00:
                    # Amount is 0 → Free Service
                    service_status = 'Free'
                    free_items_count += 1
                    logger.info(f"Item {i}: {item_names[i]} - Amount: ₹0.00 → FREE SERVICE")
                else:
                    # Amount > 0 → Payable Service
                    service_status = 'Payment'
                    subtotal += charge
                    payable_items_count += 1
                    logger.info(f"Item {i}: {item_names[i]} - Amount: ₹{charge} → PAYABLE - Running Subtotal: ₹{subtotal}")
                
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
            logger.info(f"Subtotal: ₹{subtotal}")
            logger.info(f"Tax (10%): ₹{tax}")
            logger.info(f"Total: ₹{total}")
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
                    f"• {service[0]}: ₹{service[3]:.2f} ({'FREE' if service[3] == 0 else 'PAID'})" 
                    for service in billing_data['services']
                ])
                message_text = (
                    f"📋 *Service Invoice Generated*\n\n"
                    f"*Invoice No:* {billing_data['invoice_no']}\n"
                    f"*Date:* {billing_data['date']}\n"
                    f"*Customer:* {billing_data['customer_name']}\n"
                    f"*Phone:* {billing_data['customer_contact']}\n"
                    f"*Technician:* {billing_data['technician']}\n\n"
                    f"*Services:*\n{items_list}\n\n"
                    f"*Free Services:* {free_items_count}\n"
                    f"*Payable Services:* {payable_items_count}\n"
                    f"*Subtotal:* ₹{billing_data['subtotal']:.2f}\n"
                    f"*Tax (10%):* ₹{billing_data['tax']:.2f}\n"
                    f"*Total Amount Due:* ₹{billing_data['total']:.2f}\n\n"
                    f"*Payment Status:* {billing_data['payment_status'].title()}"
                )
                
                whatsapp_api_base = "https://app.dxing.in/api/send/whatsapp"
                params = {
                    "secret": "7b8ae820ecb39f8d173d57b51e1fce4c023e359e",
                    "account": "1756959119812b4ba287f5ee0bc9d43bbf5bbe87fb68b9118fcf1af",
                    "type": "text",
                    "priority": 1,
                    "recipient": "9946545535",
                    "message": message_text
                }
                requests.get(whatsapp_api_base, params=params, timeout=5)
            except Exception as e:
                logger.debug(f"WhatsApp notification failed: {e}")
            
            success_message = f"✅ Invoice created successfully for ticket {ticket_no}!"
            if free_items_count > 0 and payable_items_count > 0:
                success_message += f" ({free_items_count} free, {payable_items_count} payable - Total: ₹{total})"
            elif free_items_count > 0 and payable_items_count == 0:
                success_message += f" (All {free_items_count} services are FREE)"
            else:
                success_message += f" (Total: ₹{total})"
            
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
                jobcard.service_items_list = [f"{item.item_name} (₹{item.charge})" for item in service_items]
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
    ✅ FIXED: Amount determines service type (0 = Free, >0 = Payable)
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
            
            # ✅ FIXED: Amount determines service type
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
                
                # ✅ DETERMINE SERVICE TYPE BASED ON AMOUNT
                if charge == 0.00:
                    # Amount is 0 → Free Service
                    service_status = 'Free'
                    free_items_count += 1
                    logger.info(f"Item {i}: {item_names[i]} - Amount: ₹0.00 → FREE SERVICE")
                else:
                    # Amount > 0 → Payable Service
                    service_status = 'Payment'
                    subtotal += charge
                    payable_items_count += 1
                    logger.info(f"Item {i}: {item_names[i]} - Amount: ₹{charge} → PAYABLE - Running Subtotal: ₹{subtotal}")
                
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
            logger.info(f"Subtotal: ₹{subtotal}")
            logger.info(f"Tax (10%): ₹{tax}")
            logger.info(f"Total: ₹{total}")
            logger.info("=== EDIT BILLING DEBUG END ===")
            
            # Update billing totals
            service_billing.subtotal = subtotal
            service_billing.tax = tax
            service_billing.total = total
            service_billing.save()
            
            success_message = f"✅ Invoice updated successfully for ticket {ticket_no}!"
            if free_items_count > 0 and payable_items_count > 0:
                success_message += f" ({free_items_count} free, {payable_items_count} payable - Total: ₹{total})"
            elif free_items_count > 0 and payable_items_count == 0:
                success_message += f" (All {free_items_count} services are FREE)"
            else:
                success_message += f" (Total: ₹{total})"
            
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
            "message": f"✅ Invoice for ticket {ticket_no} (Customer: {customer_name}, Phone: {customer_phone}) has been deleted successfully!"
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

@login_required
def lead_form_view(request):
    """
    GET: show form
    POST: create Lead with proper saving of marketedBy, consultant, branch, and
          support for firm-name toggle (existing firm select OR free-text name).
    """
    import logging
    from django.shortcuts import render, redirect, get_object_or_404
    from django.contrib import messages
    from django.contrib.auth import get_user_model
    from django.apps import apps
    from django.utils import timezone
    from django.db import transaction
  


    logger = logging.getLogger(__name__)

    # Resolve user model
    try:
        from app1.models import User as AppUser
        UserModel = AppUser
    except Exception:
        UserModel = get_user_model()

    # Resolve Lead model defensively
    try:
        from .models import Lead
    except Exception:
        try:
            Lead = apps.get_model('app5', 'Lead')  # adjust app label if needed
        except Exception:
            Lead = None

    # ✅ ADDED: Get active leads for directory
    active_leads_data = []
    if Lead:
        try:
            active_leads_data = Lead.objects.filter(status__iexact='Active').order_by('-created_at')[:25]
            logger.info(f"Found {len(active_leads_data)} active leads for directory")
        except Exception as e:
            logger.debug(f"Could not fetch active leads: {e}")
            active_leads_data = []

    # -------------------------
    # Determine active users robustly
    # Build a list of dicts: {'id', 'name', 'department'}
    # -------------------------
    active_users = []
    try:
       active_users = User.objects.filter(status='active').values('id', 'name', 'department', 'designation').order_by('name')
    except Exception:
        user_field_names = []

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
            for rattr in ('department', 'dept', 'designation', 'role', 'position'):
                try:
                    val = getattr(u, rattr, None)
                    if val:
                        role = str(val)
                        break
                except Exception:
                    continue

            active_users.append({
                'id': getattr(u, 'id', None),
                'name': display_name,
                'department': role  # template / JS expects .department
            })

    except Exception as e:
        logger.warning(f"Could not build active_users list: {e}")
        active_users = []

    # Prepare existing firms for dropdown (used on GET and on re-render after failed POST)
    existing_firms = []
    try:
        if Lead:
            existing_firms_qs = Lead.objects.values_list('name', flat=True).distinct().order_by('name')
            # filter out empty / null
            existing_firms = [n for n in existing_firms_qs if n]
    except Exception as e:
        logger.debug(f"Could not fetch existing firms: {e}")
        existing_firms = []

    if request.method == "POST":
        data = request.POST

        assignment_type = data.get("assignmentType", "unassigned")
        # Customer type toggle logic kept as before (Business vs Individual)
        customer_type = "Business" if data.get("customerTypeToggle") else "Individual"

        # ✅ FIXED: Properly resolve marketedBy to user name
        marketed_by_val = data.get("marketedBy")  # This gets the user ID from form or free text
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
                        # if import fails or model not found, fall back to raw value
                        branch_name = requirement_val
                else:
                    # It's already a name
                    branch_name = requirement_val
            except Exception as e:
                logger.warning(f"Error resolving department: {e}")
                branch_name = requirement_val

        # -----------------------
        # Firm name handling
        # The form may submit:
        # - 'existing_name' (select from dropdown) OR
        # - 'name' (free-text input) OR
        # - 'name_hidden' (if JS copied value here)
        # Prefer existing_name if present and non-empty; otherwise use name/name_hidden.
        # -----------------------
        posted_existing_name = (data.get('existing_name') or '').strip()
        posted_name_text = (data.get('name') or data.get('name_hidden') or '').strip()

        if posted_existing_name:
            final_name = posted_existing_name
        else:
            final_name = posted_name_text

        # Build the lead data
        lead_kwargs = {
            "ownerName": data.get("ownerName"),
            "phoneNo": data.get("phoneNo"),
            "email": data.get("email"),
            "customerType": customer_type,
            # Save 'name' only when Business (as in your original logic); otherwise None
            "name": final_name if customer_type == "Business" else None,
            "address": data.get("address") if customer_type == "Business" else None,
            "place": data.get("place") if customer_type == "Business" else None,
            "District": data.get("District") if customer_type == "Business" else None,
            "State": data.get("State") if customer_type == "Business" else None,
            "pinCode": data.get("pinCode") if customer_type == "Business" else None,
            "firstName": data.get("firstName") if customer_type == "Individual" else None,
            "lastName": data.get("lastName") if customer_type == "Individual" else None,
            "individualAddress": data.get("individualAddress") if customer_type == "Individual" else None,
            "individualPlace": data.get("individualPlace") if customer_type == "Individual" else None,
            "individualDistrict": data.get("individualDistrict") if customer_type == "Individual" else None,
            "individualState": data.get("individualState") if customer_type == "Individual" else None,
            "individualPinCode": data.get("individualPinCode") if customer_type == "Individual" else None,
            "date": data.get("date") or None,
            "status": data.get("status") or None,
            "refFrom": data.get("refFrom"),
            "business": data.get("business"),
            "details": data.get("details"),
            # ✅ SAVE AS TEXT/NAME (not FK)
            "marketedBy": marketed_by_name,  # Save the user's name, not ID
            "Consultant": consultant_name,    # Save consultant name
            "requirement": branch_name,       # Save department/branch name
            "assignment_type": assignment_type,
        }

        # ✅ Handle assignment if self-assigned
        if assignment_type == "self_assigned":
            try:
                current_user = None
                if request.session.get('custom_user_id'):
                    try:
                        current_user = UserModel.objects.get(id=request.session['custom_user_id'])
                    except Exception:
                        current_user = None
                elif request.user and request.user.is_authenticated:
                    current_user = request.user

                if current_user:
                    # Store assigned user name
                    assigned_name = getattr(current_user, 'name', None) or \
                                  getattr(current_user, 'username', None) or \
                                  str(current_user)

                    lead_kwargs["assigned_to_name"] = assigned_name
                    lead_kwargs["assigned_date"] = timezone.now().date()
                    lead_kwargs["assigned_time"] = timezone.now().time()

                    # If your model has FK fields, set them too
                    if Lead and hasattr(Lead, 'assigned_to') and current_user:
                        lead_kwargs["assigned_to"] = current_user

            except Exception as e:
                logger.warning(f"Error setting self-assignment: {e}")

        # Save the lead (defensive: check Lead model exists and handle field mismatch)
        if not Lead:
            messages.error(request, "Lead model not available; cannot save.")
            return redirect("app5:lead")

        try:
            with transaction.atomic():
                # If your Lead model uses different field names than provided above,
                # protect against unexpected kwargs by filtering lead_kwargs to model fields.
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
                        # add other aliases here as needed

                lead = Lead.objects.create(**safe_kwargs)

            assignment_msg = "self-assigned" if assignment_type == "self_assigned" else "submitted for assignment"
            ticket_info = getattr(lead, "ticket_number", getattr(lead, "id", ""))

            messages.success(
                request,
                f"Lead saved successfully and {assignment_msg}! Ticket Number: {ticket_info}"
            )
            return redirect("app5:lead_report")

        except Exception as e:
            logger.error(f"Error saving lead: {e}")
            messages.error(request, f"Error saving lead: {str(e)}")
            # fall through to re-render form with previously entered values

    # GET: prepare dropdowns (safe: try/except if not imported)
    try:
        districts = District.objects.all().order_by('name')
    except Exception:
        districts = []

    try:
        business_natures = BusinessNature.objects.all().order_by('name')
    except Exception:
        business_natures = []

    try:
        states = StateMaster.objects.all().order_by('name')
    except Exception:
        states = []

    try:
        from purchase_order.models import Department
        departments = Department.objects.filter(is_active=True).order_by('name')
    except Exception:
        departments = []

    context = {
        'business_natures': business_natures,
        'states': states,
        'districts': districts,
        'active_users': active_users,
        'departments': departments,
        # pass existing firms for the searchable dropdown
        'existing_firms': existing_firms,
        # ✅ ADDED: Active leads data for directory
        'active_leads_data': active_leads_data,
        
    }
    return render(request, "lead_form.html", context)




@login_required
def lead_creation_view(request):
    """
    Show Lead Creation Form with active leads listed in directory (left column)
    """
    from .models import Lead, District, BusinessNature, StateMaster
    from purchase_order.models import Department
    from app1.models import User

    # ✅ Get only active leads for the directory
    active_leads_data = Lead.objects.filter(status__iexact='Active').order_by('-created_at')[:25]

    context = {
        'districts': District.objects.all().order_by('name'),
        'states': StateMaster.objects.all().order_by('name'),
        'business_natures': BusinessNature.objects.all().order_by('name'),
        'active_users': User.objects.filter(is_active=True).order_by('name'),
        'departments': Department.objects.filter(is_active=True).order_by('name'),
        'active_leads_data': active_leads_data,  # passed to template
    }
    return render(request, 'lead_form.html', context)






# -----------------------
# Lead report view
# -----------------------
def lead_report_view(request):
    LeadModel = Lead
    leads = LeadModel.objects.all().order_by("-created_at") if hasattr(LeadModel, "created_at") else LeadModel.objects.all()

    status_filter = request.GET.get('status', '').strip()
    customer_type_filter = request.GET.get('customer_type', '').strip()
    search_query = request.GET.get('search', '').strip()
    start_date = request.GET.get('start_date', '').strip()
    end_date = request.GET.get('end_date', '').strip()

    if status_filter:
        leads = leads.filter(status=status_filter)

    if customer_type_filter:
        leads = leads.filter(customerType=customer_type_filter)

    if search_query:
        leads = leads.filter(
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
            leads = leads.filter(created_at__date__gte=s)
        except ValueError:
            pass

    if end_date:
        try:
            e = timezone.datetime.strptime(end_date, "%Y-%m-%d").date()
            leads = leads.filter(created_at__date__lte=e)
        except ValueError:
            pass

    total_leads = LeadModel.objects.count()
    active_leads = LeadModel.objects.filter(status="Active").count()
    inactive_leads = LeadModel.objects.filter(status="Inactive").count()
    installed_leads = LeadModel.objects.filter(status="Installed").count()
    business_leads = LeadModel.objects.filter(customerType="Business").count()
    individual_leads = LeadModel.objects.filter(customerType="Individual").count()
    today_leads = LeadModel.objects.filter(created_at__date=timezone.now().date()).count()
    filtered_count = leads.count()
    has_filters = bool(status_filter or customer_type_filter or search_query or start_date or end_date)

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
        "current_status_filter": status_filter,
        "current_customer_type_filter": customer_type_filter,
        "current_search_query": search_query,
        "current_start_date": start_date,
        "current_end_date": end_date,
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
        "date": lead.date.strftime('%Y-%m-%d') if getattr(lead, "date", None) else None,
        "created_at": lead.created_at.strftime('%Y-%m-%d %H:%M:%S') if getattr(lead, "created_at", None) else None,
        "updated_at": lead.updated_at.strftime('%Y-%m-%d %H:%M:%S') if getattr(lead, "updated_at", None) else None
    })


# -----------------------
# Lead edit (view + save)
# -----------------------
def lead_edit(request, lead_id):
    lead = get_object_or_404(Lead, id=lead_id)

    if request.method == 'POST':
        lead.ownerName = request.POST.get('ownerName')
        lead.phoneNo = request.POST.get('phoneNo')
        lead.email = request.POST.get('email')
        lead.customerType = 'Business' if request.POST.get('customerTypeToggle') else 'Individual'
        lead.status = request.POST.get('status', 'Active')
        lead.refFrom = request.POST.get('refFrom')
        lead.business = request.POST.get('business')
        lead.marketedBy = request.POST.get('marketedBy')
        lead.Consultant = request.POST.get('Consultant')
        lead.requirement = request.POST.get('requirement')
        lead.details = request.POST.get('details')
        lead.date = request.POST.get('date') or lead.date

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
        messages.success(request, f"Lead updated successfully! Ticket Number: {getattr(lead, 'ticket_number', lead.id)}")
        return redirect('app5:lead_report')

    # GET: prepare dropdowns for edit form
    business_natures = BusinessNature.objects.all().order_by('name') if BusinessNature is not None else []
    states = StateMaster.objects.all().order_by('name') if StateMaster is not None else []
    districts = District.objects.all().order_by('name') if District is not None else []

    # Active users for dropdown (robust)
    active_users = (
        User.objects.filter(is_active=True)
        .order_by('first_name', 'username')
        .only('id', 'first_name', 'last_name', 'username')
    )

    departments = Department.objects.filter(is_active=True).order_by('name') if Department is not None else []

    context = {
        'lead': lead,
        'business_natures': business_natures,
        'states': states,
        'districts': districts,
        'active_users': active_users,
        'departments': departments,
    }
    return render(request, 'lead_form_edit.html', context)
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
    Delete a Lead by ID.
    Works for both normal form POST and AJAX (fetch/XHR) requests.
    """
    try:
        logger.debug("Delete request received for lead ID: %s", lead_id)
        lead = get_object_or_404(Lead, id=lead_id)
        ticket_number = getattr(lead, "ticket_number", str(lead.id))
        lead.delete()
        logger.info("Lead %s (ID %s) deleted successfully", ticket_number, lead_id)

        # Message for UI (non-AJAX request)
        messages.success(request, f"Lead with Ticket Number {ticket_number} deleted successfully!")

        # If AJAX, return JSON
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({"success": True, "message": f"Lead {ticket_number} deleted."})

        # Fallback for normal POST
        return redirect('app5:lead_report')

    except Exception as e:
        logger.exception("Error deleting lead ID %s: %s", lead_id, e)
        # AJAX -> JSON error
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({"success": False, "error": str(e)}, status=500)

        # Non-AJAX fallback
        messages.error(request, f"Error deleting lead: {e}")
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

        # Users — try to use your custom User model and sensible filters
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

                # Optional status/assignment_type updates
                if hasattr(lead, 'status'):
                    try:
                        # only update status if blank or not already 'assigned'
                        current = getattr(lead, 'status', None)
                        if not current or str(current).lower() != 'assigned':
                            lead.status = 'assigned'
                    except Exception as e:
                        logger.debug("Could not update status field: %s", e)
                if hasattr(lead, 'assignment_type'):
                    try:
                        lead.assignment_type = 'assigned'
                    except Exception as e:
                        logger.debug("Could not update assignment_type field: %s", e)

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

# app5/views.py
# app5/views.py
from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db import transaction
import logging

logger = logging.getLogger(__name__)

from .models import Item, RequirementItem, Lead

User = get_user_model()

import logging
from django.shortcuts import render
from django.db.models import Q

logger = logging.getLogger(__name__)

# adjust imports to match your project structure
try:
    # prefer purchase_order Item if available (earlier code used this)
    from purchase_order.models import Item as PurchaseItem
except Exception:
    PurchaseItem = None

from .models import Item as App5Item, Lead  # your app5 models
from app1.models import User  # user model used in your project


# place near the top of views.py with your other imports
import json
import logging

from django.shortcuts import render
from django.db.models import Q
from django.utils import timezone

logger = logging.getLogger(__name__)

def requirement_list(request):
    """
    Robust requirement_list view:
    - Prefer PurchaseItem (purchase_order app) if available, else fallback to local Item.
    - Load active users using common field patterns.
    - Load recent/active leads using common field patterns.
    - Provide both QuerySets (for template iteration) and serialized lists (for JS).
    """
    # ---------- Items (for dropdown) ----------
    items_qs = None
    try:
        # try to import PurchaseItem from purchase_order app
        try:
            from purchase_order.models import Item as PurchaseItem
        except Exception:
            PurchaseItem = None

        # app5's own Item model (fallback)
        try:
            from .models import Item as App5Item
        except Exception:
            App5Item = None

        if PurchaseItem:
            # prefer filtering by is_active if available
            try:
                items_qs = PurchaseItem.objects.filter(is_active=True).order_by("name")
            except Exception:
                items_qs = PurchaseItem.objects.all().order_by("name")
        elif App5Item:
            try:
                items_qs = App5Item.objects.filter(is_active=True).order_by("name")
            except Exception:
                items_qs = App5Item.objects.all().order_by("name")
        else:
            items_qs = []
    except Exception as e:
        logger.exception("Failed to fetch items: %s", e)
        items_qs = []

    # ---------- Active Users (employees) ----------
    active_users_qs = None
    try:
        # prefer local User model import
        try:
            from .models import User
        except Exception:
            # fallback to app1.models used elsewhere in project
            from app1.models import User

        # try common patterns for active users
        try:
            active_users_qs = User.objects.filter(is_active=True).order_by("first_name", "last_name")
        except Exception:
            try:
                active_users_qs = User.objects.filter(status__iexact="active").order_by("first_name", "last_name")
            except Exception:
                # last resort: return all users ordered by name-ish fields
                try:
                    active_users_qs = User.objects.all().order_by("name")
                except Exception:
                    active_users_qs = User.objects.all()
    except Exception as e:
        logger.exception("Failed to load User model or query users: %s", e)
        active_users_qs = User.objects.none() if 'User' in locals() else []

    # serialize active users for JS/template use (defensive)
    active_users = []
    try:
        for u in active_users_qs:
            # build a friendly display name
            display_name = None
            if getattr(u, "name", None):
                display_name = u.name
            elif hasattr(u, "get_full_name"):
                try:
                    display_name = u.get_full_name()
                except Exception:
                    display_name = None
            if not display_name:
                first = getattr(u, "first_name", "") or ""
                last = getattr(u, "last_name", "") or ""
                display_name = (f"{first} {last}").strip() or getattr(u, "username", None) or getattr(u, "email", "") or "Unknown"

            phone = getattr(u, "phone_number", None) or getattr(u, "phone", None) or getattr(u, "mobile", None) or ""
            branch = getattr(u, "branch", "")
            userid = getattr(u, "userid", getattr(u, "username", ""))

            active_users.append({
                "id": getattr(u, "id", None),
                "name": display_name,
                "first_name": getattr(u, "first_name", "") or "",
                "last_name": getattr(u, "last_name", "") or "",
                "username": userid,
                "phone": phone,
                "branch": str(branch) if branch is not None else "",
            })
    except Exception as e:
        logger.exception("Failed to serialize active users: %s", e)
        active_users = []

    # ---------- Active / Recent Leads ----------
    active_leads_qs = None
    try:
        try:
            from .models import Lead
        except Exception:
            from app1.models import Lead

        # try to select active/open leads first, otherwise recent leads
        try:
            active_leads_qs = Lead.objects.filter(Q(status__iexact="active") | Q(status__iexact="open")).order_by("-created_at")[:25]
        except Exception:
            try:
                active_leads_qs = Lead.objects.filter(is_active=True).order_by("-created_at")[:25]
            except Exception:
                # fallback: most recent leads
                if hasattr(Lead, "created_at"):
                    active_leads_qs = Lead.objects.all().order_by("-created_at")[:25]
                else:
                    active_leads_qs = Lead.objects.all().order_by("-id")[:25]
    except Exception as e:
        logger.exception("Failed to load Lead model or query leads: %s", e)
        active_leads_qs = Lead.objects.none() if 'Lead' in locals() else []

    # serialize active leads safely
    active_leads = []
    try:
        for l in active_leads_qs:
            lead_name = getattr(l, "ownerName", None) or getattr(l, "owner_name", None) or getattr(l, "name", None) or getattr(l, "firm_name", None) or ""
            phone = getattr(l, "phoneNo", None) or getattr(l, "phone", None) or getattr(l, "phone_number", None) or ""
            ticket = getattr(l, "ticket_number", None) or getattr(l, "ticket_no", None) or getattr(l, "id", None)
            business = getattr(l, "business", "") or getattr(l, "firm_name", "") or ""

            active_leads.append({
                "id": getattr(l, "id", None),
                "name": lead_name,
                "phone": phone,
                "ticket_number": ticket,
                "business": business,
            })
    except Exception as e:
        logger.exception("Failed to serialize active leads: %s", e)
        active_leads = []

    # ---------- Context & render ----------
    context = {
        "items": items_qs,
        "active_users_qs": active_users_qs,   # template-friendly queryset (if template wants ORM features)
        "active_users": active_users,         # JS-friendly list of dicts
        "active_leads_qs": active_leads_qs,
        "active_leads": active_leads,
        # JSON strings convenient for embedding into JS (use safe|json_script or |safe in template)
        "active_users_json": json.dumps(active_users),
        "active_leads_json": json.dumps(active_leads),
        # optional: server timestamp
        "server_time": timezone.now(),
    }

    return render(request, "requirement_list.html", context)




@transaction.atomic
def requirement_form(request):
    if request.method != "POST":
        return redirect(reverse('app5:requirements_list'))

    owner_name = request.POST.get('owner_name', '').strip()
    phone_no = request.POST.get('phone_no', '').strip()
    email_address = request.POST.get('email_address', '').strip()

    item_ids = request.POST.getlist('item_id[]') or request.POST.getlist('item_id')
    units = request.POST.getlist('unit[]') or request.POST.getlist('unit')
    prices = request.POST.getlist('price[]') or request.POST.getlist('price')

    if not item_ids:
        messages.error(request, "No items were submitted. Please add at least one item.")
        return redirect(reverse('app5:requirements_list'))

    created = 0
    errors = []

    for idx, item_id in enumerate(item_ids):
        if not item_id:
            errors.append(f"Row {idx+1}: no item selected.")
            continue

        try:
            item_obj = Item.objects.get(pk=item_id)
        except Item.DoesNotExist:
            errors.append(f"Row {idx+1}: selected item not found (id={item_id}).")
            continue

        raw_price = prices[idx] if idx < len(prices) else ''
        try:
            price = float(raw_price) if raw_price not in (None, '') else 0.0
        except (ValueError, TypeError):
            price = 0.0
            errors.append(f"Row {idx+1}: invalid price value.")

        unit = units[idx] if idx < len(units) else getattr(item_obj, 'unit', '')

        try:
            RequirementItem.objects.create(
                item=item_obj,
                owner_name=owner_name or None,
                phone_no=phone_no or None,
                email=email_address or None,
                unit=unit,
                price=price,
            )
            created += 1
        except Exception as e:
            logger.exception("Failed to save RequirementItem for item_id=%s: %s", item_id, e)
            errors.append(f"Row {idx+1}: server error saving item.")

    if created:
        messages.success(request, f"Saved {created} requirement item(s).")
    if errors:
        messages.warning(request, "Some rows had issues: " + "; ".join(errors[:5]))
        if len(errors) > 5:
            logger.warning("Additional errors when saving requirement items: %s", errors[5:])

    return redirect(reverse('app5:requirements_list'))


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