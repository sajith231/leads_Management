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
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Lead, RequirementItem
from django.db.models import Sum
from app1.models import District 

# In views.py, update the lead_form_view function:

from app1.models import User   # ✅ Make sure User model is imported

def lead_form_view(request):
    if request.method == "POST":
        data = request.POST

        # Get assignment type
        assignment_type = data.get("assignmentType", "unassigned")
        
        # Detect customer type toggle (Business = checked)
        customer_type = "Business" if data.get("customerTypeToggle") else "Individual"
        

        try:
            lead = Lead.objects.create(
                ownerName=data.get("ownerName"),
                phoneNo=data.get("phoneNo"),
                email=data.get("email"),
                customerType=customer_type,
                assignment_type=assignment_type,
                    # Add this field to your model

                # Business fields
                name=data.get("name") if customer_type == "Business" else None,
                address=data.get("address") if customer_type == "Business" else None,
                place=data.get("place") if customer_type == "Business" else None,
                District=data.get("District") if customer_type == "Business" else None,
                State=data.get("State") if customer_type == "Business" else None,
                pinCode=data.get("pinCode") if customer_type == "Business" else None,

                # Individual fields
                firstName=data.get("firstName") if customer_type == "Individual" else None,
                lastName=data.get("lastName") if customer_type == "Individual" else None,
                individualAddress=data.get("individualAddress") if customer_type == "Individual" else None,
                individualPlace=data.get("individualPlace") if customer_type == "Individual" else None,
                individualDistrict=data.get("individualDistrict") if customer_type == "Individual" else None,
                individualState=data.get("individualState") if customer_type == "Individual" else None,
                individualPinCode=data.get("individualPinCode") if customer_type == "Individual" else None,

                # Lead Info
                date=data.get("date"),
                status=data.get("status"),
                refFrom=data.get("refFrom"),
                business=data.get("business"),
                marketedBy=data.get("marketedBy"),
                Consultant=data.get("Consultant"),
                requirement=data.get("requirement"),
                details=data.get("details"),
                
            )

            # Add success message based on assignment type
            assignment_msg = "self-assigned" if assignment_type == "self_assigned" else "submitted for assignment"
            messages.success(request, f"Lead saved successfully and {assignment_msg}! Ticket Number: {lead.ticket_number}")
            return redirect("app5:lead_report")

        except Exception as e:
            messages.error(request, f"Error saving lead: {str(e)}")
            return redirect("app5:lead")

    # GET request - show empty form
    districts = District.objects.all().order_by('name')
    business_natures = BusinessNature.objects.all().order_by('name')
    states = StateMaster.objects.all().order_by('name')
    active_users = User.objects.filter(status='active').order_by('name')
    
    try:
        from purchase_order.models import Department
        departments = Department.objects.filter(is_active=True).order_by('name')
    except ImportError:
        departments = []

    context = {
        'business_natures': business_natures,
        'states': states,
        'districts': districts,
        'active_users': active_users,
        'departments': departments,
    }

    return render(request, "lead_form.html", context)


def lead_report_view(request):
    """
    Display lead report with filtering and search capabilities
    """
    # Get all leads
    leads = Lead.objects.all().order_by("-created_at")
    
    # Get filter parameters
    status_filter = request.GET.get('status', '')
    customer_type_filter = request.GET.get('customer_type', '')
    search_query = request.GET.get('search', '').strip()
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    
    # Status filter
    if status_filter:
        leads = leads.filter(status=status_filter)
    
    # Customer type filter
    if customer_type_filter:
        leads = leads.filter(customerType=customer_type_filter)
    
    # Search filter (searches across multiple fields including ticket number)
    if search_query:
        leads = leads.filter(
            Q(ownerName__icontains=search_query) |
            Q(phoneNo__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(ticket_number__icontains=search_query) |
            Q(name__icontains=search_query) |  # Firm name for Business
            Q(firstName__icontains=search_query) |
            Q(lastName__icontains=search_query) |
            Q(place__icontains=search_query) |
            Q(individualPlace__icontains=search_query) |
            Q(refFrom__icontains=search_query)
        )
    
    # Date range filter
    if start_date:
        try:
            start_date_obj = timezone.datetime.strptime(start_date, '%Y-%m-%d').date()
            leads = leads.filter(created_at__date__gte=start_date_obj)
        except ValueError:
            # Handle invalid date format
            pass
    
    if end_date:
        try:
            end_date_obj = timezone.datetime.strptime(end_date, '%Y-%m-%d').date()
            # Include the entire end date (up to 23:59:59)
            end_date_obj = end_date_obj + timezone.timedelta(days=1) - timezone.timedelta(seconds=1)
            leads = leads.filter(created_at__date__lte=end_date_obj)
        except ValueError:
            # Handle invalid date format
            pass
    
    # Calculate statistics
    total_leads = Lead.objects.count()
    active_leads = Lead.objects.filter(status="Active").count()
    inactive_leads = Lead.objects.filter(status="Inactive").count()
    installed_leads = Lead.objects.filter(status="Installed").count()
    business_leads = Lead.objects.filter(customerType="Business").count()
    individual_leads = Lead.objects.filter(customerType="Individual").count()
    
    # Calculate today's leads
    today_leads = Lead.objects.filter(
        created_at__date=timezone.now().date()
    ).count()
    
    # Count filtered results
    filtered_count = leads.count()
    
    # Check if any filters are active
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


def lead_detail_api(request, lead_id):
    lead = get_object_or_404(Lead, id=lead_id)
    return JsonResponse({
        "id": lead.id,
        "ticket_number": lead.ticket_number,
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
        "district": lead.District,
        "individual_district": lead.individualDistrict,
        "state": lead.State,
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
        "date": lead.date.strftime('%Y-%m-%d') if lead.date else None,
        "created_at": lead.created_at.strftime('%Y-%m-%d %H:%M:%S') if lead.created_at else None,
        "updated_at": lead.updated_at.strftime('%Y-%m-%d %H:%M:%S') if lead.updated_at else None
    })


from app1.models import User   # ✅ Make sure User model is imported

def lead_edit(request, lead_id):
    lead = get_object_or_404(Lead, id=lead_id)
    
    if request.method == 'POST':
        # Update lead data
        lead.ownerName = request.POST.get('ownerName')
        lead.phoneNo = request.POST.get('phoneNo')
        lead.email = request.POST.get('email')
        lead.customerType = 'Business' if request.POST.get('customerTypeToggle') else 'Individual'
        lead.status = request.POST.get('status', 'Active')
        lead.refFrom = request.POST.get('refFrom')
        lead.business = request.POST.get('business')
        lead.marketedBy = request.POST.get('marketedBy')
        lead.Consultant = request.POST.get('Consultant')
        lead.requirement = request.POST.get('requirement')  # Department ID
        lead.details = request.POST.get('details')
        lead.date = request.POST.get('date') or lead.date
        
        # Update fields based on customer type
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
        messages.success(request, f"Lead updated successfully! Ticket Number: {lead.ticket_number}")
        return redirect('app5:lead_report')
    
    # GET request - Load dropdown data
    business_natures = BusinessNature.objects.all().order_by('name')
    states = StateMaster.objects.all().order_by('name')
    districts = District.objects.all().order_by('name')

    # ✅ Fetch ACTIVE users for dropdown
    active_users = User.objects.filter(status='active').order_by('name')
    
    # ✅ NEW: Fetch all active departments for branch field
    try:
        from purchase_order.models import Department
        departments = Department.objects.filter(is_active=True).order_by('name')
    except ImportError:
        departments = []

    context = {
        'lead': lead,
        'business_natures': business_natures,
        'states': states,
        'districts': districts,
        'active_users': active_users,
        'departments': departments,  # ✅ Added
    }
    
    return render(request, 'lead_form_edit.html', context)




def lead_delete(request, lead_id):
    print(f"Delete request received for lead ID: {lead_id}")  # Debug
    lead = get_object_or_404(Lead, id=lead_id)
    if request.method == 'POST':
        ticket_number = lead.ticket_number
        lead.delete()
        print(f"Lead {ticket_number} deleted successfully")  # Debug
        messages.success(request, f"Lead with Ticket Number {ticket_number} deleted successfully!")
        return redirect('app5:lead_report')
    return redirect('app5:lead_report')


def lead_assign_list_view(request):
    leads = Lead.objects.select_related('assigned_to').all()  # or your actual queryset/filtering
    leads_display = []
    for lead in leads:
        if lead.assigned_to:
            assigned_name = lead.assigned_to.get_full_name() or lead.assigned_to.username
        else:
            assigned_name = "Unassigned"
        # you can pass the whole lead and a computed field together
        leads_display.append({
            'lead': lead,
            'assigned_name': assigned_name,
        })

    return render(request, "lead_assign_list.html", {'leads_display': leads_display})


def assign_lead_view(request):
    """
    View to assign leads to users - SHOWS ONLY UNASSIGNED LEADS
    """
    users = User.objects.filter(status='active')  # Get active users for assignment
    
    if request.method == 'POST':
        ticket_no = request.POST.get('ticket_no')
        assign_to_id = request.POST.get('assign_to')
        
        try:
            # Get the lead by ticket number
            lead = Lead.objects.get(ticket_number=ticket_no)
            
            # Get current user (assigner)
            current_user = None
            if request.session.get('custom_user_id'):
                try:
                    current_user = User.objects.get(id=request.session['custom_user_id'])
                except User.DoesNotExist:
                    pass
            
            # Update lead assignment
            lead.assigned_to_id = assign_to_id
            lead.assigned_by = current_user
            lead.assigned_date = timezone.now().date()
            lead.assigned_time = timezone.now().time()
            lead.status = 'assigned'
            lead.assignment_type = 'assigned'  # Update assignment type
            lead.save()
            
            messages.success(request, f'Lead {ticket_no} assigned successfully!')
            return redirect('app5:lead_assign_list')
            
        except Lead.DoesNotExist:
            messages.error(request, f'Lead with ticket number {ticket_no} not found!')
        except Exception as e:
            messages.error(request, f'Error assigning lead: {str(e)}')
    
    # GET request - show form
    # ✅ GET ONLY UNASSIGNED LEADS
    unassigned_leads = Lead.objects.filter(
        assignment_type='unassigned'
    ).order_by('-created_at')
    
    # Get lead_id from URL parameter for pre-selection
    lead_id = request.GET.get('lead_id')
    lead = None
    
    if lead_id:
        try:
            lead = Lead.objects.get(id=lead_id, assignment_type='unassigned')
        except Lead.DoesNotExist:
            messages.error(request, 'Lead not found or already assigned!')
    
    context = {
        'users': users,
        'lead': lead,
        'unassigned_leads': unassigned_leads,  # Pass unassigned leads to template
    }
    return render(request, "lead_assign_form.html", context)

def edit_lead_view(request, lead_id):
    """
    View to edit lead assignment
    """
    lead = get_object_or_404(Lead, id=lead_id)
    users = User.objects.filter(status='active')
    
    if request.method == 'POST':
        try:
            assign_to_id = request.POST.get('assign_to')
            
            # Get current user (assigner)
            current_user = None
            if request.session.get('custom_user_id'):
                try:
                    current_user = User.objects.get(id=request.session['custom_user_id'])
                except User.DoesNotExist:
                    pass
            
            lead.assigned_to_id = assign_to_id
            lead.assigned_by = current_user
            lead.assigned_date = timezone.now().date()
            lead.assigned_time = timezone.now().time()
            lead.status = 'assigned'
            lead.save()
            
            messages.success(request, 'Lead assignment updated successfully!')
            return redirect('app5:lead_assign_list')
        except Exception as e:
            messages.error(request, f'Error updating lead assignment: {str(e)}')
    
    context = {
        'users': users,
        'lead': lead
    }
    return render(request, 'lead_assign_form.html', context)



# ------------------------------
# Requirement Views
# ------------------------------

@csrf_exempt
def requirement_form(request):
    """Handles adding new requirement items"""
    if request.method == "POST":
        items = request.POST.getlist('item_name')
        units = request.POST.getlist('unit')
        prices = request.POST.getlist('price')

        items_created = 0
        for i in range(len(items)):
            item_name = items[i].strip()
            unit = units[i] if i < len(units) else ""
            try:
                price = float(prices[i]) if i < len(prices) and prices[i] else 0.0
            except (ValueError, TypeError):
                price = 0.0
            
            total = price  # total column currently same as price
            
            if item_name:  # Only create if item name is not empty
                RequirementItem.objects.create(
                    item_name=item_name,
                    unit=unit,
                    price=price,
                    total=total
                )
                items_created += 1

        if items_created > 0:
            messages.success(request, f'Successfully added {items_created} requirement item(s)!')
        else:
            messages.warning(request, 'No valid items were added.')
        
        return redirect('app5:requirement_list')

    # GET request - show the form
    return render(request, 'requirement_form.html')


def requirement_list(request):
    """Show all saved requirement items"""
    items = RequirementItem.objects.all().order_by('-created_at')
    grand_total = sum(item.total for item in items)
    context = {
        'items': items,
        'grand_total': grand_total,
    }
    return render(request, 'requirement_list.html', context)


def requirement_form_view(request):
    if request.method == "POST":
        item_names = request.POST.getlist("item_name")
        units = request.POST.getlist("unit")
        prices = request.POST.getlist("price")

        for name, unit, price in zip(item_names, units, prices):
            if name and unit and price:
                RequirementItem.objects.create(
                    item_name=name,
                    unit=unit,
                    price=price,
                    total=price   # or calculate here
                )

        messages.success(request, "Items saved successfully!")
        return redirect("app5:requirements_list")

    return render(request, "requirement_form.html")


def requirements_list_view(request):
    items = RequirementItem.objects.all()
    grand_total = RequirementItem.objects.aggregate(total=Sum('total'))['total'] or 0
    return render(request, "requirement_list.html", {
        "items": items,
        "grand_total": grand_total
    })



# Replace the business nature views in your views.py with these fixed versions

# app5/views.py - Business Nature Views
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