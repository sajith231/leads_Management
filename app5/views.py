# views.py (updated)
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from app2.models import StandbyItem, StandbyImage

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

@csrf_exempt
def jobcard_create(request):
    if request.method == 'POST':
        customer = request.POST.get('customer', '').strip()
        address = request.POST.get('address', '').strip()
        phone = request.POST.get('phone', '').strip()
        status = request.POST.get('status', 'logged')
        
        # NEW: Check if self-assigned
        self_assigned = request.POST.get('self_assigned') == 'true'
        technician = None  # Initialize technician
        assigned_date = None  # Initialize assigned_date
        
        # Get the current user as creator
        creator = None
        creator_name = "Unknown"
        
        if request.session.get('custom_user_id'):
            try:
                creator = User.objects.get(id=request.session['custom_user_id'])
                creator_name = getattr(creator, "name", creator.username if hasattr(creator, 'username') else str(creator))
            except User.DoesNotExist:
                pass
        
        if self_assigned:
            status = 'sent_technician'  # Change status if self-assigned
            assigned_date = timezone.now()  # Set assigned date to current time
            
            # Set technician to current user's name
            if creator:
                technician = creator_name
            else:
                technician = "Self-Assigned User"  # Fallback

        if not customer or not address or not phone:
            messages.error(request, "Customer name, address, and phone are required fields.")
            return redirect('app5:jobcard_create')

        items = request.POST.getlist('items[]')
        serials = request.POST.getlist('serials[]')
        configs = request.POST.getlist('configs[]')
        items_data = []

        # Build items_data structure with proper serial and config
        for idx, item_name in enumerate(items):
            if not item_name:
                continue

            item_entry = {
                "item": item_name,
                "serial": serials[idx] if idx < len(serials) else "",
                "config": configs[idx] if idx < len(configs) else "",
                "status": status,  # Add status for each item
                "complaints": []
            }

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

        # Create job card - UPDATED with self_assigned field
        job_card = JobCard.objects.create(
            customer=customer,
            address=address,
            phone=phone,
            status=status,
            items_data=items_data,
            created_by=creator,
            technician=technician,  # Set technician for self-assigned jobs
            assigned_date=assigned_date,  # Set assigned_date for self-assigned jobs
            self_assigned=self_assigned  # NEW: Add the self_assigned flag
        )

        # Save uploaded images and update items_data image names
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
                        items_data[idx]["complaints"][complaint_idx]["images"].append(image.name)
                    except Exception:
                        logger.debug("Index mismatch while attaching image name to items_data")

        job_card.items_data = items_data
        job_card.save()

        # WhatsApp message details - UPDATED to include self-assignment info
        created_date = job_card.created_at.strftime("%d-%m-%Y") if hasattr(job_card, "created_at") else datetime.now().strftime("%d-%m-%Y")

        if hasattr(job_card, "ticket_no") and job_card.ticket_no:
            ticket_no = str(job_card.ticket_no)
        else:
            ticket_no = f"JC{job_card.id:06d}"

        # NEW: Add self-assignment info to WhatsApp message
        assignment_info = ""
        if self_assigned and technician:
            assignment_info = f"*Assigned To:* {technician} (Self-Assigned)\n"

        # ITEMS: only item names (no serial/config/complaints)
        items_lines = []
        for idx, item in enumerate(items_data):
            items_lines.append(f"{idx+1}. {item.get('item','')}")

        items_block = "\n".join(items_lines) if items_lines else "No items listed."

        # Build final message - UPDATED with assignment info
        message_text = (
            f"📋 *Job Card Created* \n\n"
            f"*Created Date:* {created_date}\n"
            f"*Ticket No:* {ticket_no}\n"
            f"{assignment_info}"
            f"*Customer:* {customer}\n"
            f"*Address:* {address}\n"
            f"*Phone:* {phone}\n\n"
            f"*Items:*\n{items_block}\n"
        )

        # WhatsApp API
        whatsapp_api_base = "https://app.dxing.in/api/send/whatsapp"
        params_base = {
            "secret": "7b8ae820ecb39f8d173d57b51e1fce4c023e359e",
            "account": "1756959119812b4ba287f5ee0bc9d43bbf5bbe87fb68b9118fcf1af",
            "type": "text",
            "priority": 1
        }

        recipients = ["9946545535"]

        for recipient in recipients:
            params = params_base.copy()
            params["recipient"] = recipient
            params["message"] = message_text
            try:
                resp = requests.get(whatsapp_api_base, params=params, timeout=10)
                if resp.status_code != 200:
                    logger.error("WhatsApp API returned non-200 for %s: %s", recipient, resp.status_code)
            except Exception as e:
                logger.exception("Failed to send WhatsApp message to %s: %s", recipient, e)

        success_message = "Job card created successfully."
        if self_assigned:
            success_message += f" Self-assigned to {technician}."
        
        messages.success(request, success_message)
        return redirect('app5:jobcard_list')

    # GET: fetch items + customers (existing code remains the same)
    items = Item.objects.all().order_by("name")
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
        customer_data = []

    return render(request, 'jobcard_form.html', {
        'items': items,
        'customer_data': customer_data
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

# WhatsApp API credentials
WHATSAPP_API_SECRET = '7b8ae820ecb39f8d173d57b51e1fce4c023e359e'
WHATSAPP_API_ACCOUNT = '1756959119812b4ba287f5ee0bc9d43bbf5bbe87fb68b9118fcf1af'

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


