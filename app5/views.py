# views.py (updated)
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from .models import JobCard, JobCardImage, Item
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

        if not customer or not address or not phone:
            messages.error(request, "Customer name, address, and phone are required fields.")
            return redirect('app5:jobcard_create')

        items = request.POST.getlist('items[]')
        items_data = []

        # Build items_data structure with complaints kept (for DB), but serial/config left blank
        for idx, item_name in enumerate(items):
            if not item_name:
                continue

            item_entry = {
                "item": item_name,
                "serial": "",
                "config": "",
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

        # find creator (logged-in user from session)
        creator = None
        creator_name = "Unknown"
        if request.session.get('custom_user_id'):
            try:
                creator = User.objects.get(id=request.session['custom_user_id'])
                creator_name = getattr(creator, "username", str(creator))
            except User.DoesNotExist:
                creator = None

        # Create job card
        job_card = JobCard.objects.create(
            customer=customer,
            address=address,
            phone=phone,
            status=status,
            items_data=items_data,
            created_by=creator
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

        # WhatsApp message details
        created_date = job_card.created_at.strftime("%d-%m-%Y") if hasattr(job_card, "created_at") else datetime.now().strftime("%d-%m-%Y")

        if hasattr(job_card, "ticket_no") and job_card.ticket_no:
            ticket_no = str(job_card.ticket_no)
        else:
            ticket_no = f"JC{job_card.id:06d}"

        creator_label = creator_name if not creator else getattr(creator, "username", str(creator))

        # ITEMS: only item names (no serial/config/complaints)
        items_lines = []
        for idx, item in enumerate(items_data):
            items_lines.append(f"{idx+1}. {item.get('item','')}")

        items_block = "\n".join(items_lines) if items_lines else "No items listed."

        # Build final message (single icon included)
        message_text = (
            f" *Job Card Created* \n\n"
            f"*Created Date:* {created_date}\n"
            f"*Ticket No:* {ticket_no}\n"
            # f"*Creator:* {creator_label}\n\n"
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

        recipients = ["7593820007","7593820006","7593820005"]

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

        messages.success(request, "Job card(s) created successfully.")
        return redirect('app5:jobcard_list')

    # GET: fetch items + customers
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
    """Alias for update_status to match URLs"""
    return update_status(request, pk)

from django.http import JsonResponse
from django.shortcuts import get_object_or_404

@csrf_exempt
def api_jobcard_detail(request, pk):
    """API endpoint to get jobcard details"""
    try:
        jobcard = get_object_or_404(JobCard, pk=pk)
        return JsonResponse({
            "id": jobcard.pk,
            "customer": jobcard.customer,
            "address": jobcard.address,
            "phone": jobcard.phone,
            "status": jobcard.status,
            "ticket_no": jobcard.ticket_no,
            "items_data": jobcard.items_data,
        })
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


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
            jobcard.status = status
            jobcard.save()
            
            # Fetch the technician's phone number from the User model
            assigned_user = User.objects.get(name=technician)
            if assigned_user.phone_number:
                # Prepare the WhatsApp message
                message = f"You have been assigned a new job. Ticket Number: {ticket_number}"
                send_whatsapp_message(assigned_user.phone_number, message)
            
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
    technicians = User.objects.filter(status='active').order_by('name')  # Add this line

    if request.method == "POST":
        technician = request.POST.get("technician")
        status = request.POST.get("status", "sent_technician")
        jobcard.technician = technician
        jobcard.status = status
        jobcard.save()

        messages.success(request, f"Job {jobcard.ticket_no} updated successfully!")
        return redirect("app5:jobcard_assign_table")

    context = {
        "assign": jobcard,
        "technicians": technicians,  # Add this line
        "jobcards": JobCard.objects.all()
    }
    return render(request, "jobcard_assign_edit.html", context)

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

def job_technician_accept(request):
    # Include all relevant jobcards for the logged-in technician
    processed_jobcards = JobCard.objects.filter(
        technician=request.user.get_full_name() or request.user.username,
        status__in=["sent_technician", "accepted", "rejected", "completed"]
    )

    # Count by statuses
    accepted_count = processed_jobcards.filter(status="accepted").count()
    pending_count = processed_jobcards.filter(status="sent_technician").count()
    rejected_count = processed_jobcards.filter(status="rejected").count()
    completed_count = processed_jobcards.filter(status="completed").count()

    total_count = (
        accepted_count + pending_count + rejected_count + completed_count
    )

    context = {
        "processed_jobcards": processed_jobcards,
        "accepted_count": accepted_count,
        "pending_count": pending_count,
        "rejected_count": rejected_count,
        "completed_count": completed_count,
        "total_count": total_count,
    }
    return render(request, "job_technician_accept.html", context)



@csrf_exempt
def update_jobcard_status(request, pk):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            action = data.get("action")
            completion_details = data.get("completion_details", {})

            jobcard = JobCard.objects.get(pk=pk)

            if action == "accepted":
                jobcard.status = "accepted"
            elif action == "rejected":
                jobcard.status = "rejected"
            elif action == "completed":
                jobcard.status = "completed"
                # Save completion details if provided
                if completion_details:
                    # Store completion details in the jobcard
                    # You might want to add a completion_details field to your JobCard model
                    # or store it in the existing items_data field
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



