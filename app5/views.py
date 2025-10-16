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

            # ✅ CORRECT: Get warranty and take_to_office values for each item
            warranty_value = warranties[idx] if idx < len(warranties) else "no"
            take_to_office_value = take_to_offices[idx] if idx < len(take_to_offices) else "no"

            item_entry = {
                "item": item_name,
                "serial": serials[idx] if idx < len(serials) else "",
                "config": configs[idx] if idx < len(configs) else "",
                "status": status,
                "complaints": [],
                # ✅ STORE WARRANTY AND TAKE TO OFFICE FOR EACH ITEM
                "warranty": warranty_value,
                "take_to_office": take_to_office_value,
            }

            # ✅ Add warranty details if enabled
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
                    # Update items_data with image info
                    try:
                        if idx < len(items_data) and complaint_idx < len(items_data[idx]["complaints"]):
                            items_data[idx]["complaints"][complaint_idx]["images"].append(image.name)
                    except Exception as e:
                        logger.debug(f"Error attaching image: {e}")

        # Update job card with final items_data (including images)
        job_card.items_data = items_data
        job_card.save()

        # WhatsApp Notification
        created_date = job_card.created_at.strftime("%d-%m-%Y") if job_card.created_at else datetime.now().strftime("%d-%m-%Y")
        ticket_no = job_card.ticket_no
        
        # Build items list with warranty and office info
        items_lines = []
        for item in items_data:
            line = f"• {item['item']}"
            if item.get('warranty') == 'yes':
                line += " 📋(Warranty)"
            if item.get('take_to_office') == 'yes':
                line += " 🏢(Office)"
            items_lines.append(line)
        
        items_block = "\n".join(items_lines)

        message_text = (
            f"📋 *New Job Card Created*\n\n"
            f"*Ticket No:* {ticket_no}\n"
            f"*Date:* {created_date}\n"
            f"*Customer:* {customer}\n"
            f"*Place:* {address}\n"
            f"*Phone:* {phone}\n"
            f"*Items ({len(items_data)}):*\n{items_block}\n"
        )

        # Send WhatsApp (optional)
        try:
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
            logger.debug(f"WhatsApp sending failed: {e}")

        success_message = f"Job card #{ticket_no} created successfully with {len(items_data)} item(s)."
        if self_assigned:
            success_message += f" Self-assigned to {technician}."
        
        messages.success(request, success_message)
        return redirect('app5:jobcard_list')

    # GET Request - Show form
    items = Item.objects.all().order_by("name")
    suppliers = Supplier.objects.all().order_by("name")

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
        'items': items,
        'customer_data': customer_data,
        'suppliers': suppliers,
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
def warranty_item_management(request):
    """
    Display warranty item management page with supplier selection
    """
    suppliers = Supplier.objects.all()
    
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
            pre_selected_supplier = Supplier.objects.filter(id=supplier_id).first()
            if not pre_selected_supplier:
                # Try by name
                pre_selected_supplier = Supplier.objects.filter(name__icontains=supplier_id).first()
        except:
            pass
    
    context = {
        'suppliers': suppliers,
        'pre_selected_ticket': ticket_no,
        'pre_selected_supplier': pre_selected_supplier,
        'pre_selected_item': item_name,
        'pre_selected_serial': serial_no,
    }
    return render(request, 'warranty_item.html', context)

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
def process_warranty_tickets(request):
    """
    Process multiple warranty items submission
    Creates warranty tickets for all selected items
    """
    try:
        supplier_id = request.POST.get('supplier')
        ticket_no = request.POST.get('ticket_no')
        selected_items = request.POST.getlist('selected_items')
        item_serials = request.POST.getlist('item_serials[]')
        
        # Validate required fields
        if not all([supplier_id, ticket_no]) or not selected_items:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'error': 'Supplier, ticket number, and at least one item must be selected'
                })
            messages.error(request, 'Supplier, ticket number, and at least one item must be selected')
            return redirect('app5:warranty_item')
        
        # Get related objects
        supplier = get_object_or_404(Supplier, id=supplier_id)
        jobcard = get_object_or_404(JobCard, ticket_no=ticket_no)
        
        created_tickets = []
        processed_items = []
        duplicate_items = []
        
        # Process each selected item
        for idx, selected_item in enumerate(selected_items):
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
                continue
            
            # Check if item has warranty
            if selected_item_data.get('warranty') != 'yes':
                continue
            
            # ✅ DUPLICATE DETECTION: Check if this item already has an active warranty ticket
            existing_tickets = WarrantyTicket.objects.filter(
                selected_item=selected_item,
                status__in=['pending', 'submitted', 'approved']  # Active statuses
            )
            
            # If serial number is available, use it for more precise duplicate detection
            if item_serial:
                existing_tickets = existing_tickets.filter(
                    models.Q(item_serial=item_serial) | models.Q(selected_item=selected_item)
                )
            
            if existing_tickets.exists():
                duplicate_tickets = list(existing_tickets.values_list('ticket_no', flat=True))
                duplicate_items.append({
                    'item': selected_item,
                    'serial': item_serial,
                    'existing_tickets': duplicate_tickets
                })
                continue  # Skip creating duplicate warranty ticket
            
            # Generate warranty ticket number for each item
            last_warranty = WarrantyTicket.objects.order_by('-id').first()
            if last_warranty:
                try:
                    last_num = int(last_warranty.ticket_no.split('-')[-1])
                    new_ticket_no = f"WT-{last_num + 1:06d}"
                except:
                    new_ticket_no = f"WT-{WarrantyTicket.objects.count() + 1:06d}"
            else:
                new_ticket_no = "WT-000001"
            
            # ✅ UPDATE WARRANTY STATUS IN ITEMS_DATA for each item
            if item_index is not None and jobcard.items_data:
                # Update the warranty status to show it's been sent to supplier
                jobcard.items_data[item_index]['warranty_status'] = 'sent_to_supplier'
                jobcard.items_data[item_index]['warranty_sent_date'] = timezone.now().isoformat()
                jobcard.items_data[item_index]['warranty_supplier'] = supplier.name
                jobcard.items_data[item_index]['warranty_ticket_no'] = new_ticket_no
                jobcard.items_data[item_index]['warranty_processed'] = True
            
            # Create warranty ticket for each item
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
            
            # Create log entry for each item
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
        
        # Save jobcard with updated warranty status for all items
        jobcard.save()
        
        # Handle response with duplicate information
        response_data = {
            'success': True,
            'items_processed': len(processed_items),
            'processed_items': processed_items,
            'supplier': supplier.name,
            'jobcard_ticket': jobcard.ticket_no
        }
        
        # Add duplicate information if any duplicates were found
        if duplicate_items:
            response_data['duplicate_items'] = duplicate_items
            response_data['has_duplicates'] = True
        
        # ✅ Send WhatsApp notification for all processed items
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
                
                # Add duplicate warning to WhatsApp if applicable
                if duplicate_items:
                    duplicate_list = "\n".join([f"• {item['item']} (Existing: {', '.join(item['existing_tickets'])})" 
                                              for item in duplicate_items])
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
        
        # Return JSON response for AJAX requests
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse(response_data)
        
        # Handle non-AJAX requests
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
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
        messages.error(request, f'Error processing warranty items: {str(e)}')
        return redirect('app5:warranty_item')

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
    
    # Get filter options
    suppliers = Supplier.objects.all()
    status_choices = WarrantyTicket.STATUS_CHOICES
    
    context = {
        'warranty_tickets': warranty_tickets,
        'suppliers': suppliers,
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
        
        if new_status in ['completed', 'approved', 'returned']:
            warranty_ticket.resolved_at = timezone.now()
            
            # ✅ UPDATE WARRANTY STATUS IN JOBCARD
            jobcard = warranty_ticket.jobcard
            item_name = warranty_ticket.selected_item
            
            if hasattr(jobcard, 'items_data') and jobcard.items_data:
                for idx, item in enumerate(jobcard.items_data):
                    if item.get('item') == item_name:
                        jobcard.items_data[idx]['warranty_status'] = 'returned_from_supplier'
                        jobcard.items_data[idx]['warranty_return_date'] = timezone.now().isoformat()
                        jobcard.items_data[idx]['warranty_resolution'] = resolution_notes
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