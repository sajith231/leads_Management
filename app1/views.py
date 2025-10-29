from django.contrib.auth import authenticate, login as auth_login  # Alias the imported login function
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .forms import BranchForm,RequirementForm
from django.http import JsonResponse
from django.contrib.auth import logout as auth_logout
from .forms import UserForm,DistrictForm,District
from .models import Branch, Requirement, User
from django.shortcuts import get_object_or_404
from django.contrib.auth import authenticate, login as auth_login
from django.contrib.auth.models import User as DjangoUser  # Added this import
from .forms import BranchForm, RequirementForm, UserForm,LeadRequirementAmount,AreaForm,LocationForm,Location,Hardware,HardwareForm,LeadHardwarePrice
from .models import Lead
from .forms import LeadForm
from django.db.models import Q
from datetime import datetime, timedelta
from .models import Requirement  #Ensure the correct model is imported
from .models import Lead,ServiceEntry,JobTitle
import json
from django.utils import timezone
from .models import Employee, Attendance,LeaveRequest
from django.db import transaction
from django.db import models
from .models import Employee, Attendance, LeaveRequest, Holiday,LateRequest,DefaultSettings,EarlyRequest
from .utils import is_holiday

import requests

def send_whatsapp_message(phone_number, message):
    """
    Send a WhatsApp message using the updated DxIng API.
    Automatically encodes the message and logs response info.
    """
    # ✅ Updated credentials
    secret = "7b8ae820ecb39f8d173d57b51e1fce4c023e359e"
    account = "1761365422812b4ba287f5ee0bc9d43bbf5bbe87fb68fc4daea92d8"

    # ✅ Encode message safely for URL
    encoded_message = requests.utils.quote(message)

    # ✅ Build the full API URL
    url = (
        f"https://app.dxing.in/api/send/whatsapp?"
        f"secret={secret}"
        f"&account={account}"
        f"&recipient={phone_number}"
        f"&type=text"
        f"&message={encoded_message}"
        f"&priority=1"
    )

    try:
        response = requests.get(url, timeout=10)

        if response.status_code == 200:
            print(f"✅ WhatsApp message sent successfully to {phone_number}")
            return True
        else:
            print(
                f"❌ Failed to send WhatsApp message to {phone_number}. "
                f"Status code: {response.status_code}, Response: {response.text}"
            )
            return False

    except requests.exceptions.RequestException as e:
        print(f"⚠️ Error sending WhatsApp message: {e}")
        return False




import requests

def send_whatsapp_message_for_service_log(phone_number, message):
    """
    Send a WhatsApp message for service logs using the DxIng API.
    Sends a clean, human-readable message (no URL encoding issues).
    """
    import requests

    # ✅ API credentials
    secret = "7b8ae820ecb39f8d173d57b51e1fce4c023e359e"
    account = "1761365422812b4ba287f5ee0bc9d43bbf5bbe87fb68fc4daea92d8"

    # ✅ Ensure message is properly formatted (convert newlines for WhatsApp)
    # Replace double spaces/newlines for better readability
    message = message.replace("\r\n", "\n").replace("\r", "\n")

    # ✅ Construct the API URL (no manual encoding)
    url = (
        f"https://app.dxing.in/api/send/whatsapp?"
        f"secret={secret}"
        f"&account={account}"
        f"&recipient={phone_number}"
        f"&type=text"
        f"&message={message}"
        f"&priority=1"
    )

    try:
        response = requests.get(url, timeout=10)

        if response.status_code == 200:
            print(f"✅ WhatsApp service log message sent successfully to {phone_number}")
            return True
        else:
            print(
                f"❌ Failed to send WhatsApp service log message to {phone_number}. "
                f"Status code: {response.status_code}, Response: {response.text}"
            )
            return False

    except requests.exceptions.RequestException as e:
        print(f"⚠️ Error sending WhatsApp service log message: {e}")
        return False


# --- Helper to resolve display name for approver ---
def _display_name_for_user(django_user, request):
    """
    Returns a nice display name for the current user (approver/admin)
    using session-based custom user info if available.
    """
    try:
        # Try custom User model linked to session
        custom_user_id = request.session.get('custom_user_id')
        if custom_user_id:
            from .models import User  # import inside to avoid circular import
            cu = User.objects.filter(id=custom_user_id).only('name', 'userid').first()
            if cu and (cu.name or cu.userid):
                return (cu.name or cu.userid).strip()
    except Exception:
        pass

    # Then check Django user fields
    if getattr(django_user, 'name', None):
        nm = django_user.name.strip()
        if nm:
            return nm
    if hasattr(django_user, 'get_full_name'):
        nm = (django_user.get_full_name() or '').strip()
        if nm:
            return nm
    nm = f"{getattr(django_user, 'first_name', '')} {getattr(django_user, 'last_name', '')}".strip()
    if nm:
        return nm
    return getattr(django_user, 'username', None) or "Admin"



def login(request):
    if request.method == "POST":
        userid = request.POST.get("username")
        password = request.POST.get("password")

        # First, try Django's built-in authentication for superusers
        django_user = authenticate(request, username=userid, password=password)

        if django_user and django_user.is_superuser:
            auth_login(request, django_user)
            return redirect("all_leads")

        else:
            # Custom user authentication
            try:
                custom_user = User.objects.get(userid=userid, password=password)

                # Check if the user is inactive
                if custom_user.status == 'inactive':
                    messages.error(request, "Your account is inactive. Please contact the admin.")
                    return redirect("login")

                # Create or retrieve Django user for session management
                django_user, created = DjangoUser.objects.get_or_create(
                    username=custom_user.userid,
                    defaults={
                        'is_staff': custom_user.user_level == 'admin_level',
                        'is_superuser': custom_user.user_level == 'admin_level',
                        'password': 'dummy_password'  
                    }
                )

                if created:
                    django_user.set_password(password)
                    django_user.save()

                auth_login(request, django_user)

                # Store user info in session
                request.session['custom_user_id'] = custom_user.id
                request.session['user_level'] = custom_user.user_level
                
                # Store allowed menus in session
                try:
                    allowed_menus = json.loads(custom_user.allowed_menus) if custom_user.allowed_menus else []
                except json.JSONDecodeError:
                    allowed_menus = []
                request.session['allowed_menus'] = allowed_menus

                # Redirect admin users to all_leads page
                if custom_user.user_level == 'normal':
                    return redirect("all_leads")

                # Redirect other users to the user dashboard
                return redirect("user_dashboard")

            except User.DoesNotExist:
                messages.error(request, "Invalid username or password")
                return redirect("login")

    return render(request, "login.html")




def logout(request):
    # Clear the session data
    request.session.flush()
    
    # Ensure 'custom_user_id' is removed if it exists
    if 'custom_user_id' in request.session:
        del request.session['custom_user_id']
    
    # Logout the user
    auth_logout(request)
    
    # Redirect to the login page after logout
    return redirect('login')

@login_required
def admin_dashboard(request):
    return render(request, "admin_dashboard.html")

@login_required
def save_user_menus(request, user_id):
    if request.method == 'POST':
        user = get_object_or_404(User, id=user_id)
        selected_menus = json.loads(request.POST.get('selected_menus', '[]'))
        user.allowed_menus = selected_menus
        user.save()
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'}, status=400)


@login_required
def add_branch(request):
    if request.method == 'POST':
        form = BranchForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Branch added successfully!')
            return redirect('all_branches')
    return redirect('all_branches')

@login_required
def all_branches(request):
    branches = Branch.objects.all()
    return render(request, 'all_branch.html', {'branches': branches})

@login_required
def delete_branch(request, branch_id):
    if request.method == 'POST':
        branch = get_object_or_404(Branch, id=branch_id)
        branch_name = branch.name
        try:
            branch.delete()
            messages.success(request, f'Branch "{branch_name}" deleted successfully.')
        except Exception as e:
            messages.error(request, f'Error deleting branch: {str(e)}')
    return redirect('all_branches')

@login_required
def edit_branch(request, branch_id):
    branch = get_object_or_404(Branch, id=branch_id)
    if request.method == 'POST':
        form = BranchForm(request.POST, instance=branch)
        if form.is_valid():
            form.save()
            messages.success(request, f'Branch "{branch.name}" updated successfully!')
            return redirect('all_branches')
    else:
        form = BranchForm(instance=branch)
    return render(request, 'edit_branch_modal.html', {'form': form, 'branch': branch})

@login_required
def add_requirement(request):
    if request.method == 'POST':
        form = RequirementForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Requirement added successfully!')
            return redirect('all_requirements')
    return redirect('all_requirements')

@login_required
def all_requirements(request):
    requirements = Requirement.objects.all()
    return render(request, 'all_requirements.html', {'requirements': requirements})



@login_required
def delete_requirement(request, requirement_id):
    if request.method == 'POST':
        requirement = get_object_or_404(Requirement, id=requirement_id)
        requirement_name = requirement.name
        try:
            requirement.delete()
            messages.success(request, f'Requirement "{requirement_name}" deleted successfully.')
        except Exception as e:
            messages.error(request, f'Error deleting requirement: {str(e)}')
    return redirect('all_requirements')






@login_required
def edit_requirement(request, requirement_id):
    requirement = get_object_or_404(Requirement, id=requirement_id)
    if request.method == 'POST':
        form = RequirementForm(request.POST, instance=requirement)
        if form.is_valid():
            form.save()
            messages.success(request, f'Requirement "{requirement.name}" updated successfully.')
            return redirect('all_requirements')
    else:
        form = RequirementForm(instance=requirement)
    return render(request, 'edit_requirement.html', {'form': form, 'requirement': requirement})






# In-memory list to store users (you may replace this with a database model in production)
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .forms import UserForm



# @login_required
# def add_user(request):
#     if request.method == "POST":
#         form = UserForm(request.POST, request.FILES)  # Process submitted form data

#         # Prevent using "admin" as a User ID
#         if request.POST.get("userid") == "admin":
#             messages.error(request, "The User ID 'admin' is not allowed.")
#             return render(request, "add_user.html", {"form": form})

#         if form.is_valid():
#             try:
#                 user = form.save(commit=False)  # Create a user instance but don't save yet
                
#                 # Handle the optional image field
#                 if "image" in request.FILES:
#                     user.image = request.FILES["image"]  # Assign uploaded image
                
#                 user.save()  # Save the user to the database

#                 messages.success(request, f"User '{user.name}' created successfully!")
#                 return redirect("users_table")
#             except Exception as e:
#                 messages.error(request, f"Error creating user: {str(e)}")
#         else:
#             # Display form errors as messages
#             for field, errors in form.errors.items():
#                 for error in errors:
#                     messages.error(request, f"{field}: {error}")
#     else:
#         form = UserForm()  # Initialize an empty form for GET requests

#     return render(request, "add_user.html", {"form": form})

from app2.models import JobRole  # Import JobRole from app2

@login_required
def add_user(request):
    if request.method == "POST":
        form = UserForm(request.POST, request.FILES, edit_mode=False)

        if request.POST.get("userid") == "admin":
            messages.error(request, "The User ID 'admin' is not allowed.")
            return render(request, "add_user.html", {"form": form})

        if form.is_valid():
            try:
                user = form.save(commit=False)
                
                # Handle job role assignment
                job_role_id = request.POST.get('job_role')
                if job_role_id:
                    user.job_role = JobRole.objects.get(id=job_role_id)
                
                # The cv_name field is just for selection, not saved to model
                
                if "image" in request.FILES:
                    user.image = request.FILES["image"]
                
                try:
                    default_settings = DefaultSettings.objects.first()
                    if default_settings and default_settings.default_menus:
                        user.allowed_menus = default_settings.default_menus
                    else:
                        user.allowed_menus = json.dumps([])
                except Exception as e:
                    messages.warning(request, f"Could not set default menus: {str(e)}")
                    user.allowed_menus = json.dumps([])
                
                user.save()

                messages.success(request, f"User '{user.name}' created successfully!")
                return redirect("users_table")
            except Exception as e:
                messages.error(request, f"Error creating user: {str(e)}")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = UserForm()
        job_roles = JobRole.objects.all()  # Fetch all job roles for the dropdown

    return render(request, "add_user.html", {"form": form, "job_roles": job_roles})

@login_required
def users_table(request):
    # Get status filter from request, default to 'active'
    status_filter = request.GET.get('status_filter', 'active')
    
    # Base query
    users_query = User.objects.all().select_related('branch')
    
    # Apply filter if not 'all'
    if status_filter != 'all':
        users_query = users_query.filter(status=status_filter)
    
    users = users_query
    
    return render(request, 'users_table.html', {
        'users': users,
        'status_filter': status_filter
    })


@login_required
def delete_user(request, user_id):
    if request.method == 'POST':
        user = get_object_or_404(User, id=user_id)
        user_name = user.name
        try:
            user.delete()
            messages.success(request, f'User "{user_name}" deleted successfully.')
        except Exception as e:
            messages.error(request, f'Error deleting user: {str(e)}')
    return redirect('users_table')




@login_required
def edit_user(request, user_id):
    user = get_object_or_404(User, id=user_id)

    if request.method == "POST":
        form = UserForm(request.POST, request.FILES, instance=user, edit_mode=True)
        if form.is_valid():
            user = form.save(commit=False)

            # Handle job role update
            job_role_id = request.POST.get('job_role')
            if job_role_id:
                user.job_role = JobRole.objects.get(id=job_role_id)
            else:
                user.job_role = None

            # Handle password update
            password = form.cleaned_data.get("password")
            if password:
                user.password = password  # Directly saving password (ensure hashing if needed)

            user.save()
            messages.success(request, f"User '{user.name}' updated successfully!")
            return redirect("users_table")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = UserForm(instance=user, edit_mode=True)
        job_roles = JobRole.objects.all()  # Fetch all job roles for the dropdown

    return render(request, "edit_user.html", {"form": form, "user": user, "job_roles": job_roles})


from django.db.models import Prefetch

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from app1.models import User, Lead
from app2.models import JobRole  # Import JobRole from app2

@login_required
def user_dashboard(request):
    # Get the custom user ID from session
    custom_user_id = request.session.get('custom_user_id')
    
    # Fetch the user object
    user = get_object_or_404(User, id=custom_user_id)
    
    # Fetch only leads for the logged-in user with related data
    leads = Lead.objects.filter(
        user_id=custom_user_id
    ).prefetch_related(
        'requirements',
        'requirement_amounts',
        'requirement_amounts__requirement'
    ).order_by('-created_at')
    
    # Fetch job roles for the logged-in user
    job_roles = JobRole.objects.filter(id=user.job_role_id) if user.job_role_id else JobRole.objects.none()
    
    username = f" {request.user.username}" if request.user.is_authenticated else ""
    context = {
        'leads': leads,
        'job_roles': job_roles,
        'username': username
    }
    return render(request, 'user_dashboard.html', context)






# views.py
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from .models import User
from django.contrib.auth import update_session_auth_hash

@login_required
def edit_profile(request):
    try:
        user = User.objects.get(userid=request.user.username)
    except User.DoesNotExist:
        messages.error(request, "User not found")
        return redirect('login')

    if request.method == 'POST':
        current_password = request.POST.get('current_password')
        new_password1 = request.POST.get('new_password1')
        new_password2 = request.POST.get('new_password2')
        
        # Validate current password
        if current_password and user.password != current_password:
            messages.error(request, "Current password is incorrect")
            return redirect('edit_profile')
        
        # Check if new passwords match
        if new_password1 and new_password1 != new_password2:
            messages.error(request, "New passwords don't match")
            return redirect('edit_profile')
        
        # Update password if changed
        if new_password1:
            user.password = new_password1
            messages.success(request, "Password updated successfully")
        
        user.save()
        return redirect('edit_profile')

    return render(request, 'edit_profile.html', {'user': user})





# @login_required
# def add_lead(request):
#     """
#     View to add a new lead.
#     """
#     # Determine the current user
#     if request.user.is_superuser:
#         try:
#             current_user = User.objects.filter(userid=request.user.username, user_level='admin_level').first()
#             if not current_user:
#                 current_user = User.objects.create(
#                     name=request.user.username,
#                     userid=request.user.username,
#                     password='default_password',
#                     branch=Branch.objects.first() or Branch.objects.create(name='Default Branch'),
#                     user_level='admin_level'
#                 )
#                 messages.info(request, "Created an admin user for lead management.")
#         except Exception as e:
#             messages.error(request, f"Error creating admin user: {str(e)}")
#             return redirect('all_leads')
#     else:
#         try:
#             current_user = User.objects.get(id=request.session['custom_user_id'])
#         except User.DoesNotExist:
#             messages.error(request, "User session is invalid.")
#             return redirect('logout')

#     # Handle POST
#     if request.method == 'POST':
#         form = LeadForm(request.POST, request.FILES)
#         if form.is_valid():
#             try:
#                 lead = form.save(commit=False)
#                 lead.user = current_user

#                 # Location data
#                 location_data = request.POST.get('location_data', '')
#                 if location_data:
#                     try:
#                         location = json.loads(location_data)
#                         lead.added_latitude = location.get('latitude')
#                         lead.added_longitude = location.get('longitude')
#                     except json.JSONDecodeError:
#                         messages.warning(request, 'Invalid location data format.')

#                 lead.save()
#                 form.save_m2m()

#                 # Requirement amounts & remarks
#                 amounts_data = request.POST.get('requirement_amounts_data', '{}')
#                 remarks_data = request.POST.get('requirement_remarks_data', '{}')
#                 try:
#                     amounts = json.loads(amounts_data)
#                     remarks = json.loads(remarks_data)
#                     for req_id, amount in amounts.items():
#                         LeadRequirementAmount.objects.create(
#                             lead=lead,
#                             requirement_id=int(req_id),
#                             amount=float(amount),
#                             remarks=remarks.get(req_id, '')
#                         )
#                 except json.JSONDecodeError:
#                     messages.warning(request, 'Invalid data format for requirements.')

#                 # Hardware prices
#                 hardware_prices_data = request.POST.get('hardware_prices_data', '{}')
#                 try:
#                     hardware_prices = json.loads(hardware_prices_data)
#                     for hardware_id, custom_price in hardware_prices.items():
#                         hardware = Hardware.objects.get(id=int(hardware_id))
#                         LeadHardwarePrice.objects.create(
#                             lead=lead,
#                             hardware=hardware,
#                             custom_price=float(custom_price)
#                         )
#                 except json.JSONDecodeError:
#                     messages.warning(request, "Invalid hardware price data format.")
#                 except Hardware.DoesNotExist:
#                     messages.warning(request, f"Hardware with ID {hardware_id} not found.")
#                 except ValueError:
#                     messages.warning(request, f"Invalid price value for hardware ID {hardware_id}.")

#                 messages.success(request, 'Lead added successfully!')

#                 if request.user.is_superuser or current_user.user_level == 'normal':
#                     return redirect('all_leads')
#                 return redirect('user_dashboard')

#             except Exception as e:
#                 messages.error(request, f"Error saving lead: {str(e)}")
#         else:
#             messages.error(request, 'Please correct the errors below.')
#     else:
#         form = LeadForm()
#         form.fields['location'].queryset = Location.objects.all()

#     requirements = Requirement.objects.all()
#     hardwares = Hardware.objects.all()

#     return render(request, 'add_lead.html', {
#         'form': form,
#         'requirements': requirements,
#         'hardwares': hardwares,
#     })


import requests
import json
from django.contrib import messages
from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required
from .forms import LeadForm
from .models import Lead, LeadRequirementAmount, LeadHardwarePrice, Requirement, Hardware, User, Branch
from django.utils import timezone

# WhatsApp API credentials
WHATSAPP_API_SECRET = '7b8ae820ecb39f8d173d57b51e1fce4c023e359e'
WHATSAPP_API_ACCOUNT = '1756959119812b4ba287f5ee0bc9d43bbf5bbe87fb68b9118fcf1af'

import urllib.parse

def send_whatsapp_message(phone_number, message):
    message = urllib.parse.quote(message)
    url = f"https://app.dxing.in/api/send/whatsapp?secret={WHATSAPP_API_SECRET}&account={WHATSAPP_API_ACCOUNT}&recipient={phone_number}&type=text&message={message}&priority=1"
    response = requests.get(url)
    if response.status_code == 200:
        print(f"WhatsApp message sent successfully to {phone_number}")
    else:
        print(f"Failed to send WhatsApp message to {phone_number}. Status code: {response.status_code}, Response: {response.text}")

@login_required
def add_lead(request):
    """
    View to add a new lead.
    """
    # Determine the current user
    if request.user.is_superuser:
        try:
            current_user = User.objects.filter(userid=request.user.username, user_level='admin_level').first()
            if not current_user:
                current_user = User.objects.create(
                    name=request.user.username,
                    userid=request.user.username,
                    password='default_password',
                    branch=Branch.objects.first() or Branch.objects.create(name='Default Branch'),
                    user_level='admin_level'
                )
                messages.info(request, "Created an admin user for lead management.")
        except Exception as e:
            messages.error(request, f"Error creating admin user: {str(e)}")
            return redirect('all_leads')
    else:
        try:
            current_user = User.objects.get(id=request.session['custom_user_id'])
        except User.DoesNotExist:
            messages.error(request, "User session is invalid.")
            return redirect('logout')

    # Handle POST
    if request.method == 'POST':
        form = LeadForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                lead = form.save(commit=False)
                lead.user = current_user

                # Location data
                location_data = request.POST.get('location_data', '')
                if location_data:
                    try:
                        location = json.loads(location_data)
                        lead.added_latitude = location.get('latitude')
                        lead.added_longitude = location.get('longitude')
                    except json.JSONDecodeError:
                        messages.warning(request, 'Invalid location data format.')

                lead.save()
                form.save_m2m()

                # Requirement amounts & remarks
                amounts_data = request.POST.get('requirement_amounts_data', '{}')
                remarks_data = request.POST.get('requirement_remarks_data', '{}')
                try:
                    amounts = json.loads(amounts_data)
                    remarks = json.loads(remarks_data)
                    for req_id, amount in amounts.items():
                        LeadRequirementAmount.objects.create(
                            lead=lead,
                            requirement_id=int(req_id),
                            amount=float(amount),
                            remarks=remarks.get(req_id, '')
                        )
                except json.JSONDecodeError:
                    messages.warning(request, 'Invalid data format for requirements.')

                # Hardware prices
                hardware_prices_data = request.POST.get('hardware_prices_data', '{}')
                try:
                    hardware_prices = json.loads(hardware_prices_data)
                    for hardware_id, custom_price in hardware_prices.items():
                        hardware = Hardware.objects.get(id=int(hardware_id))
                        LeadHardwarePrice.objects.create(
                            lead=lead,
                            hardware=hardware,
                            custom_price=float(custom_price)
                        )
                except json.JSONDecodeError:
                    messages.warning(request, "Invalid hardware price data format.")
                except Hardware.DoesNotExist:
                    messages.warning(request, f"Hardware with ID {hardware_id} not found.")
                except ValueError:
                    messages.warning(request, f"Invalid price value for hardware ID {hardware_id}.")

                # Prepare WhatsApp message
                created_at = lead.created_at.strftime("%Y-%m-%d %H:%M")
                firm_name = lead.firm_name
                message = f"New Lead Created!\nCreated At: {created_at}\nFirm Name: {firm_name}"
                send_whatsapp_message("9946545535", message)

                messages.success(request, 'Lead added successfully!')

                if request.user.is_superuser or current_user.user_level == 'normal':
                    return redirect('all_leads')
                return redirect('user_dashboard')

            except Exception as e:
                messages.error(request, f"Error saving lead: {str(e)}")
                print(f"Error saving lead: {str(e)}")  # Log the exception
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = LeadForm()
        form.fields['location'].queryset = Location.objects.all()

    requirements = Requirement.objects.all()
    hardwares = Hardware.objects.all()

    return render(request, 'add_lead.html', {
        'form': form,
        'requirements': requirements,
        'hardwares': hardwares,
    })

@login_required
def edit_lead(request, lead_id):
    """
    View to edit a lead.
    """
    lead = get_object_or_404(Lead, id=lead_id)

    if request.method == 'POST':
        form = LeadForm(request.POST, request.FILES, instance=lead)
        if form.is_valid():
            lead = form.save()

            try:
                # Hardware prices
                hardware_prices_data = request.POST.get('hardware_prices_data', '{}')
                hardware_prices = json.loads(hardware_prices_data)
                LeadHardwarePrice.objects.filter(lead=lead).delete()
                for hardware_id, custom_price in hardware_prices.items():
                    hardware = Hardware.objects.get(id=int(hardware_id))
                    LeadHardwarePrice.objects.create(
                        lead=lead,
                        hardware=hardware,
                        custom_price=float(custom_price)
                    )

                # Requirement amounts & remarks
                amounts_data = request.POST.get('requirement_amounts_data', '{}')
                remarks_data = request.POST.get('requirement_remarks_data', '{}')
                amounts = json.loads(amounts_data)
                remarks = json.loads(remarks_data)
                LeadRequirementAmount.objects.filter(lead=lead).delete()
                for req_id, amount in amounts.items():
                    LeadRequirementAmount.objects.create(
                        lead=lead,
                        requirement_id=int(req_id),
                        amount=float(amount),
                        remarks=remarks.get(req_id, '')
                    )

                messages.success(request, f'Lead "{lead.firm_name}" updated successfully!')
                return redirect('all_leads')

            except json.JSONDecodeError:
                messages.error(request, "Invalid JSON data format.")
            except Exception as e:
                messages.error(request, f"Error updating lead: {str(e)}")
        else:
            messages.error(request, "Please correct the errors in the form.")
    else:
        form = LeadForm(instance=lead)

    requirements = Requirement.objects.all()
    hardwares = Hardware.objects.all()
    existing_hardware_prices = {hp.hardware.id: hp.custom_price
                                for hp in LeadHardwarePrice.objects.filter(lead=lead)}
    existing_amounts = {ra.requirement_id: ra.amount
                        for ra in LeadRequirementAmount.objects.filter(lead=lead)}
    existing_remarks = {ra.requirement_id: ra.remarks
                        for ra in LeadRequirementAmount.objects.filter(lead=lead)}

    return render(request, 'edit_lead.html', {
        'form': form,
        'lead': lead,
        'requirements': requirements,
        'hardwares': hardwares,
        'existing_hardware_prices': existing_hardware_prices,
        'existing_amounts': existing_amounts,
        'existing_remarks': existing_remarks,  # Added this line
    })







@login_required
def all_leads(request):
    """
    View to display all leads with filtering and user role-based handling.
    """
    current_user = None

    # Determine if the user is a superuser or acting as a custom user
    if request.user.is_superuser or request.session.get('custom_user_id'):
        if request.user.is_superuser:
            current_user = User.objects.filter(user_level='admin_level').first()
        else:
            current_user = User.objects.get(id=request.session['custom_user_id'])

        # Base queryset with necessary prefetching and selecting
        leads = Lead.objects.prefetch_related(
            'hardware_prices', 
            'hardware_prices__hardware', 
            'requirements'
        ).select_related(
            'user', 
            'user__branch', 
            'location', 
            'location__area', 
            'location__district'
        )

        # Filters
        filters = {}

        # Planet entry filter (default to False - "Not Entered")
        planet_entry = request.GET.get('planet_entry', 'false')
        if planet_entry != '':  # If not "All"
            filters['planet_entry'] = planet_entry == 'true'

        # Branch filter
        branch = request.GET.get('branch')
        if branch:
            filters['user__branch_id'] = branch

        # User filter
        user = request.GET.get('user')
        if user:
            filters['user_id'] = user

        # Requirements filter
        requirement = request.GET.get('requirements')
        if requirement:
            filters['requirements__id'] = requirement

        # Apply all collected filters
        if filters:
            leads = leads.filter(**filters)

        # Date range filter
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        if start_date and end_date:
            try:
                start_date = datetime.strptime(start_date, '%Y-%m-%d')
                end_date = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
                leads = leads.filter(created_at__gte=start_date, created_at__lt=end_date)
            except ValueError:
                messages.error(request, "Invalid date range provided.")

        # Firm name search
        firm_name = request.GET.get('firm_name')
        if firm_name:
            leads = leads.filter(firm_name__icontains=firm_name)

        # Order by created_at in descending order
        leads = leads.order_by('-created_at')

        # Context for rendering
        context = {
            'leads': leads,
            'branches': Branch.objects.all(),
            'requirements': Requirement.objects.all(),
            'districts': District.objects.all(),
            'users': User.objects.select_related('branch').all(),
            'selected_user': request.GET.get('user', ''),
            'selected_planet_entry': planet_entry,
            'username': f" {request.user.username}"
        }

        return render(request, 'all_leads.html', context)

    else:
        # Redirect non-admin/non-custom users to their dashboard
        return redirect('user_dashboard')







@login_required
def delete_lead(request, lead_id):
    if request.method == 'POST':
        lead = get_object_or_404(Lead, id=lead_id)
        lead_name = lead.firm_name
        
        # Get the referring page
        referer = request.META.get('HTTP_REFERER', '')
        is_from_all_leads = 'all_leads' in referer
        
        try:
            lead.delete()
            messages.success(request, f'Lead "{lead_name}" deleted successfully.')
        except Exception as e:
            messages.error(request, f'Error deleting lead: {str(e)}')
        
        # Redirect based on where the request came from
        if is_from_all_leads:
            return redirect('all_leads')
        return redirect('all_leads')
    
    # If not POST, redirect to appropriate page based on referer
    referer = request.META.get('HTTP_REFERER', '')
    if 'all_leads' in referer:
        return redirect('all_leads')
    return redirect('user_dashboard')


from django.views.decorators.http import require_POST

@require_POST
def toggle_planet_entry(request):
    lead_id = request.POST.get('lead_id')
    try:
        lead = Lead.objects.get(id=lead_id)
        lead.planet_entry = not lead.planet_entry
        lead.save()
        return JsonResponse({'success': True})
    except Lead.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Lead not found'})
    

import json

@require_POST
def toggle_status(request):
    try:
        data = json.loads(request.body)
        lead_id = data.get('lead_id')
        status_type = data.get('status_type')
        
        # Validate status_type to prevent arbitrary field updates
        valid_status_fields = ['follow_up_required', 'quotation_required', 'planet_entry']
        if status_type not in valid_status_fields:
            return JsonResponse({
                'success': False,
                'error': 'Invalid status type'
            })
        
        lead = Lead.objects.get(id=lead_id)
        
        # Toggle the specified status
        current_value = getattr(lead, status_type)
        setattr(lead, status_type, not current_value)
        lead.save()
        
        return JsonResponse({
            'success': True,
            'new_value': getattr(lead, status_type)
        })
        
    except Lead.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Lead not found'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })
    


@login_required
def add_district(request):
    if request.method == 'POST':
        form = DistrictForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'District added successfully!')
            return redirect('all_districts')
    else:
        form = DistrictForm()
    return render(request, 'add_districts.html', {'form': form})

@login_required
def all_districts(request):
    districts = District.objects.all()
    return render(request, 'all_districts.html', {'districts': districts})

@login_required
def delete_district(request, district_id):
    if request.method == 'POST':
        district = get_object_or_404(District, id=district_id)
        district_name = district.name
        try:
            district.delete()
            messages.success(request, f'District "{district_name}" deleted successfully.')
        except Exception as e:
            messages.error(request, f'Error deleting district: {str(e)}')
    return redirect('all_districts')

@login_required
def edit_district(request, district_id):
    district = get_object_or_404(District, id=district_id)
    if request.method == 'POST':
        form = DistrictForm(request.POST, instance=district)
        if form.is_valid():
            form.save()
            messages.success(request, f'District "{district.name}" updated successfully.')
            return redirect('all_districts')
    else:
        form = DistrictForm(instance=district)
    return render(request, 'edit_district.html', {'form': form, 'district': district})


from .models import Area


@login_required
def add_area(request):
    if request.method == 'POST':
        form = AreaForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Area added successfully!')
            return redirect('all_areas')
    else:
        form = AreaForm()
    return render(request, 'add_area.html', {'form': form})

@login_required
def all_areas(request):
    areas = Area.objects.select_related('district').all()
    return render(request, 'all_areas.html', {'areas': areas})

@login_required
def delete_area(request, area_id):
    if request.method == 'POST':
        area = get_object_or_404(Area, id=area_id)
        area_name = area.name
        try:
            area.delete()
            messages.success(request, f'Area "{area_name}" deleted successfully.')
        except Exception as e:
            messages.error(request, f'Error deleting area: {str(e)}')
    return redirect('all_areas')

@login_required
def edit_area(request, area_id):
    area = get_object_or_404(Area, id=area_id)
    if request.method == 'POST':
        form = AreaForm(request.POST, instance=area)
        if form.is_valid():
            form.save()
            messages.success(request, f'Area "{area.name}" updated successfully.')
            return redirect('all_areas')
    else:
        form = AreaForm(instance=area)
    return render(request, 'edit_area.html', {'form': form, 'area': area})






from django.core.serializers.json import DjangoJSONEncoder
from django.utils.safestring import mark_safe
import json

@login_required
def add_location(request):
    if request.method == 'POST':
        form = LocationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Location added successfully!')
            return redirect('all_locations')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = LocationForm()

    # Pass all areas to the template for client-side filtering
    all_areas = Area.objects.select_related('district').values('id', 'name', 'district_id', 'district__name')
    all_areas_json = mark_safe(json.dumps(list(all_areas), cls=DjangoJSONEncoder))

    return render(request, 'add_location.html', {
        'form': form,
        'all_areas': all_areas_json,
    })


@login_required
def edit_location(request, location_id):
    location = get_object_or_404(Location, id=location_id)
    if request.method == 'POST':
        form = LocationForm(request.POST, instance=location)
        if form.is_valid():
            form.save()
            messages.success(request, f'Location "{location.name}" updated successfully!')
            return redirect('all_locations')
    else:
        form = LocationForm(instance=location)
    return render(request, 'edit_location.html', {'form': form, 'location': location})

@login_required
def all_locations(request):
    locations = Location.objects.select_related('district', 'area').all()
    return render(request, 'all_locations.html', {'locations': locations})



from django.http import JsonResponse
from .models import Area

def load_areas(request):
    district_id = request.GET.get('district_id')  # Get district_id from query parameters
    if district_id:
        areas = Area.objects.filter(district_id=district_id).order_by('name')
        return JsonResponse(list(areas.values('id', 'name')), safe=False)
    return JsonResponse({'error': 'Invalid district_id'}, status=400)


from django.http import JsonResponse
from .models import Location

def load_locations(request):
    district_id = request.GET.get('district_id')
    if district_id:
        locations = Location.objects.filter(district_id=district_id).select_related('area').order_by('name')
        return JsonResponse([
            {
                'id': location.id,
                'name': location.name,
                'area': location.area.name,
                'district': location.district.name,
            } for location in locations
        ], safe=False)
    return JsonResponse({'error': 'Invalid district_id'}, status=400)


@login_required
def delete_location(request, location_id):
    location = get_object_or_404(Location, id=location_id)
    location.delete()
    messages.success(request, f'Location "{location.name}" deleted successfully!')
    return redirect('all_locations')


# this is for view fields district and area
from django.http import JsonResponse
from .models import Location

def get_location_details(request):
    location_id = request.GET.get('location_id')
    try:
        location = Location.objects.get(id=location_id)
        data = {
            'district': location.district.id,
            'area': location.area.id,
        }
        return JsonResponse(data)
    except Location.DoesNotExist:
        return JsonResponse({'error': 'Location not found'}, status=404)





@login_required
def add_hardware(request):
    if request.method == 'POST':
        form = HardwareForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Hardware added successfully!')
            return redirect('all_hardwares')
    else:
        form = HardwareForm()
    return render(request, 'add_hardware.html', {'form': form})

@login_required
def all_hardwares(request):
    hardwares = Hardware.objects.all()
    return render(request, 'all_hardwares.html', {'hardwares': hardwares})

@login_required
def edit_hardware(request, hardware_id):
    hardware = get_object_or_404(Hardware, id=hardware_id)
    
    if request.method == 'POST':
        form = HardwareForm(request.POST, instance=hardware)
        if form.is_valid():
            form.save()
            return redirect('all_hardwares')  # Redirect to the list of hardwares
    else:
        form = HardwareForm(instance=hardware)
    
    return render(request, 'edit_hardware.html', {'form': form})

@login_required
def delete_hardware(request, hardware_id):
    if request.method == 'POST':
        hardware = get_object_or_404(Hardware, id=hardware_id)
        hardware_name = hardware.name
        try:
            hardware.delete()
            messages.success(request, f'Hardware "{hardware_name}" deleted successfully.')
        except Exception as e:
            messages.error(request, f'Error deleting hardware: {str(e)}')
    return redirect('all_hardwares')








# app1/views.py (complaint-related functions)
# views.py (snippet)
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Complaint, User
from .forms import ComplaintForm
from software_master.models import Software

# views.py (complaint-related functions)

@login_required
def add_complaint(request):
    if request.method == 'POST':
        form = ComplaintForm(request.POST)
        if form.is_valid():
            complaint = form.save(commit=False)
            # attach created_by if available in session (preserve existing logic)
            if 'user_id' in request.session:
                try:
                    from .models import User
                    custom_user = User.objects.get(id=request.session['user_id'])
                    complaint.created_by = custom_user
                except User.DoesNotExist:
                    complaint.created_by = None
            else:
                complaint.created_by = None
            complaint.save()
            # Save M2M if available; fallback to manual set
            if hasattr(form, 'save_m2m'):
                form.save_m2m()
            else:
                # fallback: set software from cleaned_data
                sw = form.cleaned_data.get('software')
                if sw is not None:
                    # ensure sequence
                    complaint.software.set(sw if hasattr(sw, '__iter__') else [sw])
            return redirect('all_complaints')
    else:
        form = ComplaintForm()
    return render(request, 'add_complaints.html', {'form': form})


@login_required
def edit_complaint(request, complaint_id):
    complaint = get_object_or_404(Complaint, id=complaint_id)
    if request.method == 'POST':
        form = ComplaintForm(request.POST, instance=complaint)
        if form.is_valid():
            complaint = form.save(commit=False)
            complaint.save()
            if hasattr(form, 'save_m2m'):
                form.save_m2m()
            else:
                sw = form.cleaned_data.get('software')
                if sw is not None:
                    complaint.software.set(sw if hasattr(sw, '__iter__') else [sw])
            return redirect('all_complaints')
    else:
        form = ComplaintForm(instance=complaint)
    return render(request, 'edit_complaint.html', {'form': form})



@login_required
def all_complaints(request):
    selected_type = request.GET.get('type', 'all')

    # for M2M, use prefetch_related
    if selected_type == 'all':
        complaints = Complaint.objects.prefetch_related('software').all().order_by('description')
    else:
        complaints = Complaint.objects.prefetch_related('software').filter(complaint_type=selected_type).order_by('description')

    from django.core.paginator import Paginator
    paginator = Paginator(complaints, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    start_index = (page_obj.number - 1) * paginator.per_page

    context = {
        'page_obj': page_obj,
        'selected_type': selected_type,
        'start_index': start_index,
    }
    return render(request, 'all_complaints.html', context)



# Delete complaint view
def delete_complaint(request, complaint_id):
    complaint = get_object_or_404(Complaint, id=complaint_id)
    complaint.delete()
    return redirect('all_complaints')





    




def get_current_user(request):
    """Helper function to get current user for both superuser and regular users"""
    if request.user.is_superuser:
        # Try to get existing admin user first
        admin_user = User.objects.filter(
            userid=request.user.username,
            user_level='admin_level'
        ).first()
        
        # If no admin user exists, create one
        if not admin_user:
            default_branch = Branch.objects.first()
            if not default_branch:
                default_branch = Branch.objects.create(name='Default Branch')
                
            admin_user = User.objects.create(
                name=request.user.username,
                userid=request.user.username,
                password='default_password',  # You might want to set this more securely
                branch=default_branch,
                user_level='admin_level'
            )
        return admin_user
    else:
        return User.objects.get(id=request.session.get('custom_user_id'))

import requests
from django.http import JsonResponse

from django.http import JsonResponse
import requests

def get_customers(request):
    response = requests.get("https://rrcpython.imcbs.com/api/clients/all")
    if response.status_code == 200:
        json_data = response.json()
        customers = json_data.get("data", [])  # safely get the data list
        return JsonResponse(customers, safe=False)  # safe=False because it's a list
    return JsonResponse({"error": "Failed to fetch data"}, status=500)

    


from django.shortcuts import render, redirect
from django.utils import timezone
from .models import ServiceEntry, User  # Import the custom User model
from django.contrib.auth.decorators import login_required

from django.shortcuts import render, redirect
from django.utils import timezone
from .models import ServiceEntry, User
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.contrib import messages

from django.contrib.auth import get_user_model
User = get_user_model()

from django.utils.timezone import now, timedelta
from datetime import datetime

from django.utils.timezone import now, timedelta
from datetime import datetime, date

from django.utils.timezone import now, timedelta
from datetime import datetime, date

@login_required
def service_entry(request):
    try:
        current_user = request.user
        selected_user_id = request.GET.get('user')
        
        # Check if any date filters are already applied
        has_date_filter = 'from_date' in request.GET or 'to_date' in request.GET
        
        # Default to today's date if no date filters are applied
        today = now().date()
        if not has_date_filter:
            default_from_date = today
            default_to_date = today
        else:
            # Get date range from request
            from_date_str = request.GET.get('from_date')
            to_date_str = request.GET.get('to_date')
            
            # Convert string dates to date objects
            try:
                default_from_date = datetime.strptime(from_date_str, '%Y-%m-%d').date() if from_date_str else today
                default_to_date = datetime.strptime(to_date_str, '%Y-%m-%d').date() if to_date_str else today
            except (ValueError, TypeError):
                default_from_date = today
                default_to_date = today
        
        # Filter by date range (inclusive)
        service_entries_list = ServiceEntry.objects.filter(
            date__date__gte=default_from_date,
            date__date__lte=default_to_date
        ).order_by('-date')

        # Apply user filter if provided
        if selected_user_id and selected_user_id != 'all':
            service_entries_list = service_entries_list.filter(user_id=selected_user_id)

        # Pagination
        paginator = Paginator(service_entries_list, 12)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        # Send user list to template
        users = User.objects.all()

        return render(request, 'service_entry.html', {
            'page_obj': page_obj,
            'current_user': current_user,
            'users': users,
            'selected_user_id': selected_user_id,
            'default_from_date': default_from_date.strftime('%Y-%m-%d'),
            'default_to_date': default_to_date.strftime('%Y-%m-%d'),
        })
    except Exception as e:
        messages.error(request, f'Error accessing service entries: {str(e)}')
        return redirect('login')



@login_required
def add_service_entry(request):
    try:
        current_user = get_current_user(request)
        complaints = Complaint.objects.all().order_by('created_at')

        # Fetch customers from the API
        customers = []
        try:
            response = requests.get('https://rrcpython.imcbs.com/api/clients/all')
            if response.status_code == 200:
                customers = response.json()
        except Exception as e:
            messages.warning(request, f'Could not fetch customers: {str(e)}')

        if request.method == 'POST':
            # Check if it's a new customer
            new_customer_name = request.POST.get('new_customer_name')
            if new_customer_name:
                # This is a new customer
                customer_name = new_customer_name
                place = request.POST.get('new_customer_address', '')
                
                # Here you would typically save the new customer to your database
                # For now, we'll just use the name directly
            else:
                # Existing customer
                customer_name = request.POST.get('customer')
                place = request.POST.get('place')

            # Get other form data
            complaint = request.POST.get('complaint')
            remarks = request.POST.get('remarks')
            status = request.POST.get('status')
            mode_of_service = request.POST.get('mode_of_service')
            service_type = request.POST.get('service_type')
            duration = request.POST.get('duration')
            phone_number = request.POST.get('phone_number')


            # Create new service entry
            service_entry = ServiceEntry.objects.create(
                date=timezone.now(),
                customer=customer_name,
                complaint=complaint,
                remarks=remarks,
                status=status,
                mode_of_service=mode_of_service,
                service_type=service_type,
                user=current_user,
                place=place,
                duration=duration,
                phone_number=phone_number
            )

            messages.success(request, 'Service entry added successfully!')

            # Redirect based on user level
            if current_user.user_level == 'admin_level' or request.user.is_superuser:
                return redirect('service_entry')
            else:
                return redirect('user_service_entry')

        return render(request, 'add_service_entry.html', {
            'complaints': complaints,
            'customers': customers,
            'current_user': current_user
        })

    except Exception as e:
        messages.error(request, f'Error adding service entry: {str(e)}')
        if current_user.user_level == 'admin_level' or request.user.is_superuser:
            return redirect('service_entry')
        else:
            return redirect('user_service_entry')




@login_required
def edit_service_entry(request, entry_id):
    entry = get_object_or_404(ServiceEntry, id=entry_id)
    current_user = get_current_user(request)
    complaints = Complaint.objects.all().order_by('created_at')
    

    # Fetch customers from the API
    import requests
    customers = []
    try:
        response = requests.get('https://rrcpython.imcbs.com/api/clients/all')
        if response.status_code == 200:
            customers = response.json().get('data', [])
    except Exception as e:
        messages.warning(request, f'Could not fetch customers: {str(e)}')

    if request.method == 'POST':
        entry.customer = request.POST.get('customer')
        complaint_description = request.POST.get('complaint')
        entry.complaint = complaint_description
        entry.remarks = request.POST.get('remarks')
        entry.place = request.POST.get('place')
        entry.status = request.POST.get('status')
        entry.mode_of_service = request.POST.get('mode_of_service')  # Existing field
        entry.service_type = request.POST.get('service_type')  # New field
        entry.duration = request.POST.get('duration')
        entry.phone_number = request.POST.get('phone_number')
        entry.save()

        # Redirect based on user level
        if current_user.user_level == 'admin_level' or request.user.is_superuser:
            return redirect('service_entry')
        else:
            return redirect('user_service_entry')

    context = {
        'entry': entry,
        'complaints': complaints,
        'customers': customers,
    }
    return render(request, 'edit_service_entry.html', context)






@login_required
def delete_service_entry(request, entry_id):
    entry = get_object_or_404(ServiceEntry, id=entry_id)
    current_user = get_current_user(request)
    
    if request.method == 'POST':
        entry.delete()
        # Redirect based on user level
        if current_user.user_level == 'admin_level' or request.user.is_superuser:
            return redirect('service_entry')
        else:
            return redirect('user_service_entry')
            
    return render(request, 'confirm_delete.html', {'entry': entry})




@login_required
def user_service_entry(request):
    try:
        current_user = get_current_user(request)
        # Filter service entries for current user only
        service_entries = ServiceEntry.objects.filter(user=current_user).order_by('-date')
        return render(request, 'user_service_entry.html', {
            'service_entries': service_entries,
            'current_user': current_user
        })
    except Exception as e:
        messages.error(request, f'Error accessing service entries: {str(e)}')
        return redirect('login')



@login_required
def user_add_service_entry(request):
    try:
        current_user = get_current_user(request)
        complaints = Complaint.objects.all().order_by('created_at')

        if request.method == 'POST':
            # Get form data
            customer = request.POST.get('customer')
            complaint = request.POST.get('complaint')
            remarks = request.POST.get('remarks')
            place = request.POST.get('place')
            status = request.POST.get('status')
            
            # Create new service entry for current user
            service_entry = ServiceEntry.objects.create(
                date=timezone.now(),
                customer=customer,
                complaint=complaint,
                remarks=remarks,
                status=status,
                user=current_user,
                place=place
            )
            
            messages.success(request, 'Service entry added successfully!')
            return redirect('user_service_entry')
        
        return render(request, 'add_service_entry.html', {
            'complaints': complaints,
            'current_user': current_user,
            'is_user_view': True  # Add this to differentiate user view
        })
        
    except Exception as e:
        messages.error(request, f'Error adding service entry: {str(e)}')
        return redirect('user_service_entry')



@login_required
def user_edit_service_entry(request, entry_id):
    entry = get_object_or_404(ServiceEntry, id=entry_id)
    current_user = get_current_user(request)
    
    if entry.user != current_user:
        messages.error(request, "You don't have permission to edit this entry.")
        return redirect('user_service_entry')
    
    complaints = Complaint.objects.all().order_by('created_at')

    # Fetch customers from the API
    customers = []
    try:
        response = requests.get('https://rrcpython.imcbs.com/api/clients/all')
        if response.status_code == 200:
            customers = response.json().get("data", [])
    except Exception as e:
        messages.warning(request, f'Could not fetch customers: {str(e)}')

    if request.method == 'POST':
        entry.customer = request.POST.get('customer')
        complaint_description = request.POST.get('complaint')
        entry.complaint = complaint_description
        entry.remarks = request.POST.get('remarks')
        entry.place = request.POST.get('place')
        entry.status = request.POST.get('status')
        entry.mode_of_service = request.POST.get('mode_of_service')
        entry.service_type = request.POST.get('service_type')
        entry.duration = request.POST.get('duration')
        entry.phone_number = request.POST.get('phone_number')
        entry.save()
        return redirect('user_service_entry')

    context = {
        'entry': entry,
        'complaints': complaints,
        'customers': customers,  # Add this line
        'is_user_view': True
    }
    return render(request, 'edit_service_entry.html', context)



@login_required
def user_delete_service_entry(request, entry_id):
    entry = get_object_or_404(ServiceEntry, id=entry_id)
    current_user = get_current_user(request)
    
    if entry.user != current_user:
        messages.error(request, "You don't have permission to delete this entry.")
        return redirect('user_service_entry')
        
    if request.method == 'POST':
        entry.delete()
        return redirect('user_service_entry')
    return render(request, 'confirm_delete.html', {'entry': entry, 'is_user_view': True})

from django.shortcuts import render, redirect
from .models import Agent

from django.core.paginator import Paginator
from django.shortcuts import render, redirect
from .models import Agent, BusinessType

from django.core.paginator import Paginator
from django.shortcuts import render, redirect
from .models import Agent, BusinessType

from django.core.paginator import Paginator
from django.shortcuts import render, redirect
from .models import Agent, BusinessType

from django.core.paginator import Paginator
from django.shortcuts import render, redirect
from .models import Agent, BusinessType

from django.core.paginator import Paginator
from django.db.models import Q

from django.db.models import Q
from django.core.paginator import Paginator
from django.shortcuts import render
from .models import Agent, BusinessType

def agent_list(request):
    # Get search parameters from the request
    search_name = request.GET.get('name', '').strip().upper()
    search_district = request.GET.get('district', '').strip().upper()
    search_business_type = request.GET.get('business_type', '').strip().upper()

    # Filter agents based on search parameters
    agents = Agent.objects.all()
    if search_name:
        agents = agents.filter(Q(name__icontains=search_name) | Q(firm_name__icontains=search_name))
    if search_district:
        agents = agents.filter(district__icontains=search_district)
    if search_business_type:
        agents = agents.filter(business_type__icontains=search_business_type)

    # Sort agents alphabetically by name
    agents = agents.order_by('name')

    # Set up pagination
    paginator = Paginator(agents, 15)  # Show 15 agents per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Pass search parameters to the template for pagination links
    context = {
        'agents': page_obj,
        'business_types': BusinessType.objects.all(),
        'search_name': search_name,
        'search_district': search_district,
        'search_business_type': search_business_type
    }

    return render(request, 'agent.html', context)



def add_agent(request):
    business_types = BusinessType.objects.all()
    if request.method == 'POST':
        name = request.POST['name']
        firm_name = request.POST.get('firm_name', '')
        business_type = request.POST['business_type']
        location = request.POST['location']
        district = request.POST['district']
        contact_number = request.POST['contact_number']
        remarks = request.POST.get('remarks', '')
        Agent.objects.create(
            name=name,
            firm_name=firm_name,
            business_type=business_type,
            location=location,
            district=district,
            contact_number=contact_number,
            remarks=remarks
        )
        return redirect('agent_list')
    return render(request, 'add_agent.html', {'business_types': business_types})


from django.shortcuts import get_object_or_404

def edit_agent(request, agent_id):
    agent = get_object_or_404(Agent, id=agent_id)
    business_types = BusinessType.objects.all()
    if request.method == 'POST':
        agent.name = request.POST['name']
        agent.firm_name = request.POST.get('firm_name', '')
        agent.business_type = request.POST['business_type']
        agent.location = request.POST['location']
        agent.district = request.POST['district']
        agent.contact_number = request.POST['contact_number']
        agent.remarks = request.POST.get('remarks', '')
        agent.save()
        return redirect('agent_list')
    return render(request, 'edit_agent.html', {'agent': agent, 'business_types': business_types})


def delete_agent(request, agent_id):
    agent = get_object_or_404(Agent, id=agent_id)
    agent.delete()
    return redirect('agent_list')


from django.shortcuts import render
from django.core.paginator import Paginator
from .models import CV, JobTitle

def cv_management(request):
    job_titles = JobTitle.objects.all()
    selected_job_title = request.GET.get('job_title')
    selected_interview_status = request.GET.get('interview_status')
    name_query = request.GET.get('name')
    
    # Start with ordered queryset - newest first
    cv_list = CV.objects.all().order_by('-created_date')
    
    if name_query:
        # Search by name or phone number
        cv_list = cv_list.filter(Q(name__icontains=name_query) | Q(phone_number__icontains=name_query))
    
    if selected_job_title:
        try:
            cv_list = cv_list.filter(job_title_id=selected_job_title)
        except ValueError:
            pass
    
    if selected_interview_status:
        if selected_interview_status == "Yes":
            cv_list = cv_list.filter(interview_status=True)
        elif selected_interview_status == "No":
            cv_list = cv_list.filter(interview_status=False)
    
    paginator = Paginator(cv_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'cv_list': page_obj,
        'job_titles': job_titles,
        'selected_job_title': selected_job_title,
        'selected_interview_status': selected_interview_status,
    }
    
    return render(request, 'cv_management.html', context)

from django.utils.timezone import now

from django.shortcuts import render, redirect
from django.contrib import messages
from .models import CV

from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils.timezone import now
from .models import CV, JobTitle

from django.utils.timezone import now
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from .models import CV, JobTitle, Agent  # Ensure correct imports

@login_required
def add_cv(request):
    if request.method == "POST":
        phone_number = request.POST.get('phone_number')

        if CV.objects.filter(phone_number=phone_number).exists():
            messages.error(request, 'Duplicate phone number is not allowed.')
            return redirect('add_cv')

        try:
            # Retrieve form data
            name = request.POST['name']
            address = request.POST.get('address', '')
            place = request.POST['place']
            district = request.POST['district']
            education = request.POST['education']
            experience = request.POST['experience']
            job_title_id = request.POST['job_title']
            job_title = JobTitle.objects.get(id=job_title_id)
            dob = request.POST.get('dob') or None
            remarks = request.POST.get('remarks', '')
            cv_attachment = request.FILES['cv_attachment']
            agent_id = request.POST.get('agent')
            gender = request.POST.get('gender', '')

            # Create CV instance (without agent initially)
            cv = CV.objects.create(
                name=name,
                address=address,
                phone_number=phone_number,
                place=place,
                district=district,
                education=education,
                experience=experience,
                job_title=job_title,
                dob=dob,
                remarks=remarks,
                cv_attachment=cv_attachment,
                created_date=now(),
                created_by=request.user,
                gender=gender,
            )

            # Assign agent after CV creation
            if agent_id:
                try:
                    agent = Agent.objects.get(id=agent_id)
                    cv.agent = agent
                    cv.save()
                except Agent.DoesNotExist:
                    messages.error(request, 'Invalid agent selected.')

            messages.success(request, 'CV added successfully!')
            return redirect('cv_management')

        except JobTitle.DoesNotExist:
            messages.error(request, 'Invalid job title selected.')
        except Exception as e:
            messages.error(request, f'Error creating CV: {str(e)}')

    # Add job titles and agents to context
    job_titles = JobTitle.objects.all()
    agents = Agent.objects.all()
    return render(request, 'add_cv.html', {
        'job_titles': job_titles,
        'agents': agents
    })





def edit_cv(request, id):
    cv = get_object_or_404(CV, id=id)
    job_titles = JobTitle.objects.all()
    districts = CV.KERALA_DISTRICTS

    if request.method == 'POST':
        try:
            cv.name = request.POST['name']
            cv.address = request.POST['address']
            cv.phone_number = request.POST['phone_number']  # New field
            cv.place = request.POST['place']
            cv.district = request.POST['district']
            cv.education = request.POST['education']
            cv.experience = request.POST['experience']
            job_title_id = request.POST['job_title']
            cv.gender = request.POST.get('gender', '')
            cv.job_title = JobTitle.objects.get(id=job_title_id)
            if 'dob' in request.POST and request.POST['dob']:
                cv.dob = request.POST['dob']
            else:
                cv.dob = None
            cv.remarks = request.POST.get('remarks', '')
            if 'cv_attachment' in request.FILES:
                cv.cv_attachment = request.FILES['cv_attachment']
            cv.save()
            return redirect('cv_management')
        except JobTitle.DoesNotExist:
            messages.error(request, 'Invalid job title selected.')
        except Exception as e:
            messages.error(request, f'Error updating CV: {str(e)}')

    return render(request, 'edit_cv.html', {'cv': cv, 'job_titles': job_titles, 'districts': districts})


def delete_cv(request, id):
    """
    Directly deletes a CV entry and redirects to the CV management page.
    """
    cv = get_object_or_404(CV, id=id)
    if request.method == 'POST':
        cv.delete()
    return redirect('cv_management')

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import CV

@csrf_exempt
def toggle_interview_status(request):
    if request.method == 'POST':
        cv_id = request.POST.get('cv_id')
        new_status = request.POST.get('new_status') == 'Yes'
        try:
            cv = CV.objects.get(id=cv_id)
            cv.interview_status = new_status
            if new_status:  # If status is set to "Yes", update the interview date
                cv.interview_date = timezone.now()
            else:  # If status is set to "No", clear the interview date
                cv.interview_date = None
            cv.save()
            return JsonResponse({'success': True})
        except CV.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'CV not found'})
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

def job_titles(request):
    titles = JobTitle.objects.all().order_by('id')
    return render(request, 'job_titles.html', {'titles': titles})

def add_job_title(request):
    if request.method == 'POST':
        title = request.POST.get('job_title')
        if title:
            JobTitle.objects.create(title=title)
            messages.success(request, 'Job title added successfully!')
            return redirect('job_titles')
        else:
            messages.error(request, 'Please enter a job title.')
    return render(request, 'add_job_title.html')

def edit_job_title(request, title_id):
    title = get_object_or_404(JobTitle, id=title_id)
    if request.method == 'POST':
        new_title = request.POST.get('job_title')
        if new_title:
            title.title = new_title
            title.save()
            messages.success(request, 'Job title updated successfully!')
            return redirect('job_titles')
        else:
            messages.error(request, 'Please enter a job title.')
    return render(request, 'edit_job_title.html', {'title': title})

def delete_job_title(request, title_id):
    title = get_object_or_404(JobTitle, id=title_id)
    title.delete()
    messages.success(request, 'Job title deleted successfully!')
    return redirect('job_titles')








from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import CV, Rating

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Rating, CV
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import CV, Rating
import json
import base64
import tempfile
from django.core.files import File
import os
from django.utils import timezone

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import CV, Rating
import json
import base64
import tempfile
from django.core.files import File
import os
from django.utils import timezone







from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
import json
from .models import BusinessType

def business_type_list(request):
    business_types = BusinessType.objects.all().order_by('-created_at')
    return render(request, 'business_type.html', {'business_types': business_types})

@require_http_methods(['POST'])
def create_business_type(request):
    try:
        data = json.loads(request.body)
        business_type = BusinessType.objects.create(name=data['name'])
        return JsonResponse({'success': True, 'id': business_type.id})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})

@require_http_methods(['PUT'])
def update_business_type(request, id):
    try:
        data = json.loads(request.body)
        business_type = BusinessType.objects.get(id=id)
        business_type.name = data['name']
        business_type.save()
        return JsonResponse({'success': True})
    except BusinessType.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Business type not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})

@require_http_methods(['DELETE'])
def delete_business_type(request, id):
    try:
        business_type = BusinessType.objects.get(id=id)
        business_type.delete()
        return JsonResponse({'success': True})
    except BusinessType.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Business type not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})
    




from django.shortcuts import render, get_object_or_404
from .models import CV
from django.shortcuts import render, get_object_or_404
from .models import CV, OfferLetterDetails

def offer_letter(request, cv_id):
    cv = get_object_or_404(CV, id=cv_id)
    clicked_date = request.GET.get("date", cv.created_date.strftime("%d/%m/%Y"))
    offer_letter_details = OfferLetterDetails.objects.filter(cv=cv).first()

    context = {
        'candidate_name': cv.name,
        'candidate_address': cv.address,
        'offer_letter_details': offer_letter_details,  # Pass the offer letter details to the template
    }
    return render(request, 'offer_letter.html', context)



from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import CV, OfferLetterDetails
import json

from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from .models import OfferLetterDetails, CV

from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from .models import CV, OfferLetterDetails
import json

def save_offer_letter_details(request, cv_id):
    if request.method == 'POST':
        try:
            cv = get_object_or_404(CV, id=cv_id)
            offer_details, created = OfferLetterDetails.objects.get_or_create(cv=cv)

            # Retrieve form data safely
            offer_details.position = request.POST.get('position', '').strip()
            offer_details.department = request.POST.get('department', '').strip()
            offer_details.start_date = request.POST.get('startDate', None)
            offer_details.salary = request.POST.get('salary', '').strip()
            offer_details.notice_period = request.POST.get('noticePeriod', 2)  # Default to 2 days

            # Save the offer letter details
            offer_details.save()

            return JsonResponse({'success': True})
        
        except CV.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'CV not found'})
        
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request'})




def get_offer_letter_details(request, cv_id):
    try:
        offer_details = get_object_or_404(OfferLetterDetails, cv_id=cv_id)

        return JsonResponse({
            'success': True,
            'position': offer_details.position,
            'department': offer_details.department,
            'start_date': offer_details.start_date.strftime('%Y-%m-%d') if offer_details.start_date else '',
            'salary': offer_details.salary,
            'notice_period': offer_details.notice_period  # Now includes notice period
        })

    except OfferLetterDetails.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Offer letter details not found'})

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


from django.shortcuts import render, get_object_or_404
from .models import CV, OfferLetterDetails

def generate_offer_letter(request, cv_id):
    # Fetch the CV and associated Offer Letter details
    cv = get_object_or_404(CV, id=cv_id)
    
    try:
        offer_letter_details = OfferLetterDetails.objects.get(cv=cv)
    except OfferLetterDetails.DoesNotExist:
        offer_letter_details = None

    # Get the current date
    today_date = now().strftime('%d-%m-%Y')  # Format: dd-mm-yyyy

    # Pass data to the offer letter template
    context = {
        'candidate_name': cv.name.upper(),
        'candidate_address': cv.address.upper(),
        'offer_letter_details': offer_letter_details,
        'today_date': today_date,  # Pass the date to the template
    }
    return render(request, 'offer_letter.html', context)




from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from .models import Employee, Attachment
from django.core.files.storage import FileSystemStorage


from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from .models import Employee

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q

@login_required
def employee_management(request):
    status_filter = request.GET.get('status', 'active')  # Default to 'active'
    search_query = request.GET.get('search', '')  # Get search query
    
    # Base queryset with status filter
    employees = Employee.objects.filter(status=status_filter).select_related("user").order_by('name')

    
    # Apply search filter if search query exists
    if search_query:
        employees = employees.filter(
            Q(name__icontains=search_query) |
            Q(user__userid__icontains=search_query) |
            Q(job_title__icontains=search_query) |
            Q(organization__icontains=search_query)
        )
    
    # Pagination - 15 employees per page
    paginator = Paginator(employees, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, "employee_management.html", {
        "page_obj": page_obj,
        "employees": page_obj,  # For backward compatibility
        "status_filter": status_filter,
        "search_query": search_query,
        "total_employees": paginator.count,
    })



from django.shortcuts import render, redirect
from .models import Employee, Attachment, CV
from django.shortcuts import render, redirect
from .models import Employee, User, Attachment, CV

@login_required
def add_employee(request):
    users = User.objects.all()  # Fetch all users for the dropdown
    
    if request.method == "POST":
        name = request.POST['name']
        user_id = request.POST.get("user_id")  # Capture selected user ID
        photo = request.FILES['photo']
        address = request.POST.get('address', '')
        phone_personal = request.POST['phone_personal']
        phone_residential = request.POST['phone_residential']
        place = request.POST['place']
        district = request.POST['district']
        education = request.POST['education']
        experience = request.POST['experience']
        job_title = request.POST['job_title']
        organization = request.POST.get("organization")
        joining_date = request.POST['joining_date']
        dob = request.POST['dob']
        bank_account_number = request.POST.get('bank_account_number', '')
        ifsc_code = request.POST.get('ifsc_code', '')
        bank_name = request.POST.get('bank_name', '')
        branch = request.POST.get('branch', '')
        status = request.POST.get("status")
        duty_time_start = request.POST.get('duty_time_start', None)
        duty_time_end = request.POST.get('duty_time_end', None)

        employee = Employee.objects.create(
            name=name,
            user=User.objects.get(id=user_id) if user_id else None,  # Assign selected user
            photo=photo,
            address=address,
            phone_personal=phone_personal,
            phone_residential=phone_residential,
            place=place,
            district=district,
            education=education,
            experience=experience,
            job_title=job_title,
            organization=organization,
            joining_date=joining_date,
            dob=dob,
            bank_account_number=bank_account_number,
            ifsc_code=ifsc_code,
            bank_name=bank_name,
            branch=branch,
            status=status,
            duty_time_start=duty_time_start,
            duty_time_end=duty_time_end,
        )

        for file in request.FILES.getlist('attachments'):
            Attachment.objects.create(employee=employee, file=file)

        return redirect('employee_management')
    
    return render(request, 'add_employee.html', {'users': users, 'cvs': CV.objects.all()})





def delete_employee(request, emp_id):
    employee = get_object_or_404(Employee, id=emp_id)
    employee.delete()
    return redirect('employee_management')



from django.shortcuts import render, redirect, get_object_or_404
from .models import Employee, Attachment
from django.contrib import messages
@login_required
def edit_employee(request, emp_id):
    employee = get_object_or_404(Employee, id=emp_id)
    users = User.objects.exclude(employee__isnull=False).union(User.objects.filter(id=employee.user.id if employee.user else None))

    if request.method == "POST":
        user_id = request.POST.get("user_id")
        selected_user = User.objects.get(id=user_id) if user_id else None

        # Ensure User ID is unique
        if selected_user and Employee.objects.exclude(id=employee.id).filter(user=selected_user).exists():
            messages.error(request, f"User ID {selected_user.userid} is already assigned to another employee.")
            return redirect("edit_employee", emp_id=emp_id)

        # Update employee fields
        employee.user = selected_user
        employee.name = request.POST["name"]
        if "photo" in request.FILES:
            employee.photo = request.FILES["photo"]
        employee.address = request.POST.get("address", "")
        employee.phone_personal = request.POST["phone_personal"]
        employee.phone_residential = request.POST.get("phone_residential", "")
        employee.place = request.POST["place"]
        employee.district = request.POST["district"]
        employee.education = request.POST["education"]
        employee.experience = request.POST.get("experience", "")
        employee.job_title = request.POST["job_title"]
        employee.organization = request.POST.get("organization", "")
        employee.joining_date = request.POST["joining_date"]
        employee.dob = request.POST["dob"]
        employee.bank_account_number = request.POST.get("bank_account_number", "")
        employee.ifsc_code = request.POST.get("ifsc_code", "")
        employee.bank_name = request.POST.get("bank_name", "")
        employee.branch = request.POST.get("branch", "")
        employee.status = request.POST.get("status")
        employee.duty_time_start = request.POST.get("duty_time_start", None)
        employee.duty_time_end = request.POST.get("duty_time_end", None)
        employee.save()

        # Delete selected attachments
        delete_attachments = request.POST.getlist("delete_attachments")
        if delete_attachments:
            Attachment.objects.filter(id__in=delete_attachments).delete()

        # Handle new attachments (if any)
        for file in request.FILES.getlist('attachments'):
            Attachment.objects.create(employee=employee, file=file)

        messages.success(request, "Employee updated successfully.")
        return redirect("employee_management")

    context = {
        "employee": employee,
        "users": users,
        "joining_date": employee.joining_date.strftime("%Y-%m-%d"),
        "dob": employee.dob.strftime("%Y-%m-%d"),
    }

    return render(request, "edit_employee.html", context)










from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from .models import Document

def document_list(request):
    documents = Document.objects.all()
    return render(request, 'document.html', {'documents': documents})

def add_document(request):
    if request.method == "POST":
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        if name:
            Document.objects.create(name=name, description=description)
        return JsonResponse({"message": "Document added successfully"})
    return JsonResponse({"error": "Invalid request"}, status=400)

def edit_document(request, id):
    document = get_object_or_404(Document, id=id)
    if request.method == "POST":
        document.name = request.POST.get('name')
        document.description = request.POST.get('description', '')
        document.save()
        return JsonResponse({"message": "Document updated successfully"})
    return JsonResponse({"error": "Invalid request"}, status=400)

def delete_document(request, id):
    document = get_object_or_404(Document, id=id)
    document.delete()
    return JsonResponse({"message": "Document deleted successfully"})





from django.http import JsonResponse
from django.shortcuts import render
from .models import Document, DocumentSetting
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from .models import DocumentSetting, Document

def get_document_settings(request, doc_id):
    settings = DocumentSetting.objects.filter(document_id=doc_id).values('id', 'name', 'url')
    return JsonResponse({"settings": list(settings)})



@csrf_exempt
def add_document_setting(request):
    if request.method == 'POST':
        try:
            document_id = request.POST.get("document_id")
            name = request.POST.get("name")
            url = request.POST.get("url", "")
            attachment = request.FILES.get("attachment")

            document = Document.objects.get(id=document_id)
            new_setting = DocumentSetting.objects.create(
                document=document,
                name=name,
                url=url,
                attachment=attachment
            )

            return JsonResponse({
                'status': 'success', 
                'message': 'Setting added', 
                'setting': {'id': new_setting.id, 'name': new_setting.name}
            })
        except Exception as e:
            return JsonResponse({'status': 'error', 'error': str(e)}, status=500)
    return JsonResponse({'status': 'error', 'error': 'Invalid request'}, status=400)



from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_protect
from .models import DocumentSetting
from django.views.decorators.http import require_http_methods

@require_http_methods(["POST"])  # Remove @csrf_protect
def delete_document_setting(request, setting_id):
    try:
        setting = get_object_or_404(DocumentSetting, id=setting_id)
        setting_info = {
            'id': setting.id,
            'name': setting.name,
            'document_id': setting.document.id
        }
        setting.delete()
        return JsonResponse({
            "status": "success",
            "message": f"Setting '{setting_info['name']}' deleted successfully",
            "data": setting_info
        })
    except DocumentSetting.DoesNotExist:
        return JsonResponse({"status": "error", "error": "Setting not found"}, status=404)
    except Exception as e:
        return JsonResponse({"status": "error", "error": str(e)}, status=500)
    
@csrf_exempt
def edit_document_setting(request, setting_id):
    if request.method == "POST":
        try:
            setting = get_object_or_404(DocumentSetting, id=setting_id)
            setting.name = request.POST.get("name")
            setting.url = request.POST.get("url")

            attachment = request.FILES.get("attachment")
            if attachment:
                setting.attachment = attachment

            setting.save()

            return JsonResponse({"status": "success", "message": "Setting updated"})
        except Exception as e:
            return JsonResponse({"status": "error", "error": str(e)}, status=500)

    return JsonResponse({"status": "error", "error": "Invalid request"}, status=400)






def document_detail(request, doc_id):
    document = get_object_or_404(Document.objects.prefetch_related(
        models.Prefetch(
            'settings',
            queryset=DocumentSetting.objects.order_by('position').prefetch_related(
                models.Prefetch(
                    'fields',
                    queryset=DocumentSettingField.objects.order_by('position')
                )
            )
        )
    ), id=doc_id)
    return render(request, 'document_detail.html', {'document': document})

from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from .models import Document, DocumentSetting, DocumentSettingField
import json

def save_document_settings(request, doc_id):
    if request.method == 'POST':
        try:
            document = get_object_or_404(Document, id=doc_id)
            setting_id = request.POST.get('setting_id')
            url = request.POST.get('url')
            attachment = request.FILES.get('attachment')
            fields = json.loads(request.POST.get('fields', '[]'))

            if setting_id:
                setting = get_object_or_404(DocumentSetting, id=setting_id)
            else:
                setting = DocumentSetting(document=document, name="New Setting")
            
            setting.url = url
            if attachment:
                setting.attachment = attachment
            setting.save()

            # Track existing field IDs to determine which need to be deleted
            existing_field_ids = list(setting.fields.values_list('id', flat=True))
            processed_field_ids = []

            # Process field updates
            for index, field_data in enumerate(fields):
                field_id = field_data.get('id')
                
                if field_id and field_id.isdigit():  # This is an existing field
                    try:
                        field = DocumentSettingField.objects.get(id=field_id)
                        field.field_name = field_data.get('name')
                        field.field_value = field_data.get('value')
                        field.purpose = field_data.get('purpose')
                        
                        # Get new attachment if available
                        new_attachment_key = field_data.get('new_attachment')
                        if new_attachment_key and new_attachment_key in request.FILES:
                            field.attachment = request.FILES[new_attachment_key]
                        
                        field.save()
                        processed_field_ids.append(int(field_id))
                    except DocumentSettingField.DoesNotExist:
                        # Field doesn't exist, create a new one
                        field_id = None
                
                if not field_id or not field_id.isdigit():  # This is a new field
                    # Get the attachment using the unique key
                    attachment_key = field_data.get('new_attachment')
                    field_attachment = request.FILES.get(attachment_key) if attachment_key else None
                    
                    DocumentSettingField.objects.create(
                        setting=setting,
                        field_name=field_data.get('name'),
                        field_value=field_data.get('value'),
                        purpose=field_data.get('purpose'),
                        attachment=field_attachment
                    )
            
            # Delete fields that were not included in the update
            fields_to_delete = set(existing_field_ids) - set(processed_field_ids)
            if fields_to_delete:
                DocumentSettingField.objects.filter(id__in=fields_to_delete).delete()

            return JsonResponse({
                "status": "success",
                "message": "Settings saved successfully!"
            })

        except Exception as e:
            return JsonResponse({
                "status": "error",
                "message": str(e)
            }, status=500)

    return JsonResponse({
        "status": "error",
        "message": "Invalid request method"
    }, status=400)




from django.http import JsonResponse
from .models import DocumentSetting, DocumentSettingField

def get_document_setting_fields(request, setting_id):
    setting = DocumentSetting.objects.get(id=setting_id)
    fields = setting.fields.all()

    field_list = [
        {
            'id': field.id,
            'name': field.field_name,  # Make sure key names match exactly
            'value': field.field_value,
            'purpose': field.purpose,
            'attachment': field.attachment.url if field.attachment else None,
        }
        for field in fields
    ]

    return JsonResponse({'fields': field_list})




from django.http import FileResponse, Http404
from django.views.decorators.clickjacking import xframe_options_sameorigin

@xframe_options_sameorigin
def view_attachment(request, setting_id=None, field_id=None):
    try:
        if setting_id:
            obj = get_object_or_404(DocumentSetting, id=setting_id)
            file = obj.attachment
        elif field_id:
            obj = get_object_or_404(DocumentSettingField, id=field_id)
            file = obj.attachment
        else:
            raise Http404("No attachment specified")

        if not file:
            raise Http404("No attachment found")

        response = FileResponse(file.open())
        return response
    except Exception as e:
        raise Http404(f"Error accessing file: {str(e)}")
    











from django.utils import timezone

from django.core.paginator import Paginator
from django.utils import timezone
from django.shortcuts import render
from .models import Employee








def base_context(request):
    user_image = None
    if request.user.is_authenticated:
        custom_user = User.objects.filter(userid=request.user.username).first()
        if custom_user and custom_user.image:
            user_image = custom_user.image.url  # Get the image URL
    return {'user_image': user_image}




from django.shortcuts import render, get_object_or_404
from .models import User
from .models import Employee  # Ensure Employee is imported

from django.shortcuts import render, get_object_or_404
from num2words import num2words
from .models import Employee



    

def user_control(request, user_id):
    return render(request, 'user_control.html', {'user_id': user_id})


from django.shortcuts import render
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from .models import Employee, Attendance

def attendance(request):
    employees = Employee.objects.select_related('user').filter(
        status='active'  # Add this filter to get only active employees
    )
    
    today = timezone.now()
    current_month = today.month
    current_year = today.year
    
    # Get all attendance records for the current month
    attendance_records = Attendance.objects.filter(
        date__year=current_year,
        date__month=current_month
    ).select_related('employee')

    # Create a dictionary to store attendance data
    attendance_data = {}
    for record in attendance_records:
        employee_id = str(record.employee_id)  # Convert to string for JSON serialization
        if employee_id not in attendance_data:
            attendance_data[employee_id] = {}

        day = str(record.date.day)
        
        # Determine attendance status
        status = record.status if record.status else 'initial'

        attendance_data[employee_id][day] = {
            'status': status,
            'punch_in': record.punch_in.isoformat() if record.punch_in else None,
            'punch_out': record.punch_out.isoformat() if record.punch_out else None
        }

    # Calculate total days in current month
    from calendar import monthrange
    days_in_month = monthrange(current_year, current_month)[1]

    context = {
        'employees': employees,
        'attendance_data': json.dumps(attendance_data),
        'current_month': today.strftime('%B %Y'),
        'days_in_month': days_in_month,
        'today': today.day,
        'range': range(1, days_in_month + 1),
        'is_superuser': request.user.is_superuser  # Add this line
    }

    return render(request, 'attendance.html', context)


@csrf_exempt
def save_attendance(request, employee_id, day, status):
    try:
        # Parse request body for punch in/out times
        data = json.loads(request.body)
        punch_in = data.get('punch_in')
        punch_out = data.get('punch_out')

        # Get the current month and year
        today = datetime.now()
        year = today.year
        month = today.month

        # Get or create attendance record
        employee = Employee.objects.get(id=employee_id)
        attendance_date = datetime(year, month, int(day))
        
        attendance, created = Attendance.objects.get_or_create(
            employee=employee,
            date=attendance_date,
            defaults={
                'status': status,
                'punch_in': punch_in,
                'punch_out': punch_out
            }
        )

        if not created:
            attendance.status = status
            attendance.punch_in = punch_in
            attendance.punch_out = punch_out
            attendance.save()

        return JsonResponse({
            'status': 'success',
            'message': 'Attendance saved successfully',
            'data': {
                'status': attendance.status,
                'punch_in': attendance.punch_in,
                'punch_out': attendance.punch_out
            }
        })
    except Employee.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': 'Employee not found'
        }, status=404)
    except json.JSONDecodeError:
        return JsonResponse({
            'status': 'error',
            'message': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)


from app2.models import DailyTask
from django.utils import timezone

@login_required
def attendance_user(request):
    # Get the ongoing task for the user
    ongoing_task = DailyTask.objects.filter(
        added_by=request.user,
        status='in_progress'
    ).first()

    return render(request, 'attendance_user.html', {
        'ongoing_task': ongoing_task,
        'current_date': timezone.now().date(),
        # other context variables
    })


@login_required
def get_current_employee_id(request):
    try:
        custom_user_id = request.session.get('custom_user_id')
        if not custom_user_id:
            return JsonResponse({'error': 'User session not found'}, status=404)
        
        employee = Employee.objects.get(user_id=custom_user_id)
        return JsonResponse({'employee_id': employee.id})
    except Employee.DoesNotExist:
        return JsonResponse({'error': 'Employee not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
from django.utils import timezone
# views.py

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from django.utils import timezone
from .models import Attendance, Employee
from django.contrib.auth.decorators import login_required

@csrf_exempt
@login_required
def punch_in(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            custom_user_id = request.session.get('custom_user_id')
            if not custom_user_id:
                return JsonResponse({'success': False, 'error': 'User session not found'})
            
            custom_user = User.objects.get(id=custom_user_id)
            employee = Employee.objects.get(user=custom_user)
            now = timezone.now()
            today = now.date()
            
            # Check if today is a holiday
            if is_holiday(today):
                return JsonResponse({'success': False, 'error': 'Cannot punch in on a holiday'})
            
            # Check if the employee has already punched in today
            existing_attendance = Attendance.objects.filter(
                employee=employee,
                date=today,
                day=today.day,
                punch_in__isnull=False
            ).exists()
            
            if existing_attendance:
                return JsonResponse({'success': False, 'error': 'You have already punched in today'})
            
            attendance, created = Attendance.objects.get_or_create(
                employee=employee,
                date=today,
                day=today.day,
                defaults={
                    'punch_in': now,
                    'punch_in_location': data.get('location_name'),
                    'punch_in_latitude': data.get('latitude'),
                    'punch_in_longitude': data.get('longitude'),
                    'status': 'half'
                }
            )
            
            if not created:
                attendance.punch_in = now
                attendance.punch_in_location = data.get('location_name')
                attendance.punch_in_latitude = data.get('latitude')
                attendance.punch_in_longitude = data.get('longitude')
                attendance.status = 'half'
                attendance.save()
            
            return JsonResponse({
                'success': True,
                'status': 'half',
                'punch_in': now.strftime('%H:%M:%S'),
                'employee_id': str(employee.id),
                'day': str(now.day)
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Invalid request'})

@csrf_exempt
@login_required
def punch_out(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            custom_user_id = request.session.get('custom_user_id')
            if not custom_user_id:
                return JsonResponse({'success': False, 'error': 'User session not found'})
            
            custom_user = User.objects.get(id=custom_user_id)
            employee = Employee.objects.get(user=custom_user)
            now = datetime.now()
            today = now.date()
            
            # Check if today is a holiday
            if is_holiday(today):
                return JsonResponse({'success': False, 'error': 'Cannot punch out on a holiday'})
            
            # Check if the employee has an active break
            active_break = BreakTime.objects.filter(
                employee=employee,
                date=today,
                is_active=True,
                break_punch_in__isnull=False,
                break_punch_out__isnull=True
            ).first()
            
            if active_break:
                return JsonResponse({'success': False, 'error': 'You have an active break. Please finish your break before punching out.'})
            
            # Check if the employee has already punched out today
            try:
                attendance = Attendance.objects.get(
                    employee=employee,
                    date=today,
                    day=today.day
                )
                
                # Check if already punched out
                if attendance.punch_out is not None:
                    return JsonResponse({'success': False, 'error': 'You have already punched out today'})
                
                # Check if not punched in yet
                if attendance.punch_in is None:
                    return JsonResponse({'success': False, 'error': 'You must punch in before punching out'})
                
                attendance.punch_out = now
                attendance.punch_out_location = data.get('location_name')
                attendance.punch_out_latitude = data.get('latitude')
                attendance.punch_out_longitude = data.get('longitude')
                attendance.status = 'full'
                attendance.save()
                
                return JsonResponse({'success': True})
            except Attendance.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'No punch-in record found for today'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Invalid request'})

# views.py
from django.http import JsonResponse
from django.utils.timezone import localtime
from .models import Attendance, Employee
from django.contrib.auth.decorators import login_required
from datetime import datetime

from django.http import JsonResponse
from django.utils.timezone import localtime
from .models import Attendance, Employee
from django.contrib.auth.decorators import login_required
from datetime import datetime

@login_required
def get_attendance_status(request):
    employee_id = request.GET.get('employee_id')
    date_str = request.GET.get('date')

    try:
        employee = Employee.objects.get(id=employee_id)
        date = datetime.strptime(date_str, '%Y-%m-%d').date()

        attendance = Attendance.objects.filter(employee=employee, date=date).first()

        if attendance:
            return JsonResponse({
                'punch_in': attendance.punch_in.isoformat() if attendance.punch_in else None,
                'punch_out': attendance.punch_out.isoformat() if attendance.punch_out else None,
                'punch_in_location': attendance.punch_in_location if attendance.punch_in_location else 'Not available',
                'punch_out_location': attendance.punch_out_location if attendance.punch_out_location else 'Not available',
                'punch_in_latitude': str(attendance.punch_in_latitude) if attendance.punch_in_latitude else None,
                'punch_in_longitude': str(attendance.punch_in_longitude) if attendance.punch_in_longitude else None,
                'punch_out_latitude': str(attendance.punch_out_latitude) if attendance.punch_out_latitude else None,
                'punch_out_longitude': str(attendance.punch_out_longitude) if attendance.punch_out_longitude else None,
                'note': attendance.note if attendance.note else '',  # Include the note
            })
        return JsonResponse({
            'punch_in': None,
            'punch_out': None,
            'punch_in_location': 'Not available',
            'punch_out_location': 'Not available',
            'note': ''  # Ensure note is included even if no record exists
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

from django.http import JsonResponse
from django.views.decorators.http import require_GET
from .models import Attendance, Employee
from datetime import datetime

@require_GET
def get_attendance_data(request):
    employee_id = request.GET.get('employee_id')
    year = request.GET.get('year')
    month = request.GET.get('month')

    try:
        employee = Employee.objects.get(id=employee_id)
        attendance_records = Attendance.objects.filter(
            employee=employee,
            date__year=year,
            date__month=month
        )

        # Get holidays for this month
        holidays = Holiday.objects.filter(
            date__year=year,
            date__month=month
        ).values_list('date', flat=True)

        attendance_data = {}
        for record in attendance_records:
            day = record.date.day
            # Check if this date is a holiday
            is_holiday = record.date in holidays
            
            attendance_data[day] = {
                'status': 'holiday' if is_holiday else (record.status if record.status else 'initial'),
                'punch_in': record.punch_in.isoformat() if record.punch_in else None,
                'punch_out': record.punch_out.isoformat() if record.punch_out else None,
                'punch_in_location': record.punch_in_location if record.punch_in_location else None,
                'punch_out_location': record.punch_out_location if record.punch_out_location else None,
                'is_holiday': is_holiday
            }

        # Add holidays that don't have attendance records
        for holiday_date in holidays:
            day = holiday_date.day
            if day not in attendance_data:
                attendance_data[day] = {
                    'status': 'holiday',
                    'punch_in': None,
                    'punch_out': None,
                    'punch_in_location': None,
                    'punch_out_location': None,
                    'is_holiday': True
                }

        return JsonResponse({
            'success': True,
            'attendance': attendance_data
        })
    except Employee.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Employee not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from .models import Attendance, Employee
import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.dateparse import parse_date
import json
from .models import Attendance, Employee

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.dateparse import parse_date
import json
from .models import Attendance, Employee

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from .models import Attendance, Employee
@csrf_exempt
def update_attendance_status(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            employee_id = data.get("employee_id")
            date_str = data.get("date")
            status = data.get("status")
            note = data.get("note", "")  # Get the note from the request

            if not all([employee_id, date_str, status]):
                return JsonResponse({"success": False, "error": "Missing required fields"})

            try:
                date = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                return JsonResponse({"success": False, "error": "Invalid date format"})

            employee = get_object_or_404(Employee, id=employee_id)
            
            # Get or create attendance record
            attendance, created = Attendance.objects.get_or_create(
                employee=employee,
                date=date,
                defaults={
                    'status': status,
                    'day': date.day,
                    'verified': True if status.startswith('verified_') else False
                }
            )

            if not created:
                attendance.status = status
                attendance.verified = True if status.startswith('verified_') else False
                attendance.note = note  # Update the note field
                attendance.save()

            return JsonResponse({
                "success": True,
                "employee_id": employee_id,
                "date": date_str,
                "status": status,
                "note": note,  # Return the note in the response
                "verified": attendance.verified
            })

        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})

    return JsonResponse({"success": False, "error": "Invalid request method"})






@csrf_exempt
def update_setting_positions(request, doc_id):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            positions = data.get('positions', [])
            
            # Get the document
            document = get_object_or_404(Document, id=doc_id)
            
            # Update positions for each setting
            with transaction.atomic():  # Use transaction to ensure all updates succeed or none do
                for position, setting_id in enumerate(positions, start=1):  # Start from 1
                    DocumentSetting.objects.filter(
                        id=setting_id,
                        document=document  # Ensure setting belongs to this document
                    ).update(position=position)
            
            # Return the updated order
            settings = DocumentSetting.objects.filter(document=document).order_by('position')
            return JsonResponse({
                'status': 'success',
                'positions': list(settings.values('id', 'position'))
            })
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=500)
    return JsonResponse({
        'status': 'error',
        'message': 'Invalid request'
    }, status=400)

@csrf_exempt
def update_field_positions(request, setting_id):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            positions = data.get('positions', [])
            
            # Get the setting
            setting = get_object_or_404(DocumentSetting, id=setting_id)
            
            # Update positions for each field
            with transaction.atomic():  # Use transaction to ensure all updates succeed or none do
                for position, field_id in enumerate(positions, start=1):  # Start from 1
                    DocumentSettingField.objects.filter(
                        id=field_id,
                        setting=setting  # Ensure field belongs to this setting
                    ).update(position=position)
            
            # Return the updated order
            fields = DocumentSettingField.objects.filter(setting=setting).order_by('position')
            return JsonResponse({
                'status': 'success',
                'positions': list(fields.values('id', 'position'))
            })
        except json.JSONDecodeError as e:
            return JsonResponse({
                'status': 'error',
                'message': 'Invalid JSON data'
            }, status=400)
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=500)
    return JsonResponse({
        'status': 'error',
        'message': 'Invalid request method'
    }, status=405)

def document_detail(request, doc_id):
    document = get_object_or_404(Document.objects.prefetch_related(
        models.Prefetch(
            'settings',
            queryset=DocumentSetting.objects.order_by('position').prefetch_related(
                models.Prefetch(
                    'fields',
                    queryset=DocumentSettingField.objects.order_by('position')
                )
            )
        )
    ), id=doc_id)
    return render(request, 'document_detail.html', {'document': document})








from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from .models import ReminderType

def reminder_type_view(request):
    reminders = ReminderType.objects.all()
    return render(request, 'reminder_type.html', {'reminders': reminders})

def add_reminder_type(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        ReminderType.objects.create(name=name)
        return JsonResponse({'success': True})
    return JsonResponse({'success': False})

def edit_reminder_type(request, id):
    reminder = get_object_or_404(ReminderType, id=id)
    if request.method == 'POST':
        name = request.POST.get('name')
        reminder.name = name
        reminder.save()
        return JsonResponse({'success': True})
    return JsonResponse({'success': False})

def delete_reminder_type(request, id):
    reminder = get_object_or_404(ReminderType, id=id)
    reminder.delete()
    return redirect('reminder_type')





@csrf_exempt
def update_attendance(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            employee_id = data.get("employee_id")
            date = data.get("date")
            status = data.get("status")

            if not employee_id or not date or not status:
                return JsonResponse({"success": False, "error": "Missing required fields"})

            attendance, created = Attendance.objects.get_or_create(
                employee_id=employee_id, date=date, defaults={"status": status}
            )

            if not created:
                attendance.status = status
                attendance.save()

            return JsonResponse({"success": True, "status": status})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})

    return JsonResponse({"success": False, "error": "Invalid request"})














# reminder related views functions start here(

from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
import logging
from .models import Reminder, Employee, ReminderType
from django.core.paginator import Paginator
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from .models import Reminder, ReminderType, Employee

logger = logging.getLogger(__name__)



@login_required
def reminders(request):
    """View for displaying filtered reminders."""
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")
    search_query = request.GET.get("search")

    reminders_list = Reminder.objects.all().prefetch_related('responsible_persons').order_by('entry_date')

    if start_date and end_date:
        reminders_list = reminders_list.filter(remind_date__range=[start_date, end_date])
    elif start_date:
        reminders_list = reminders_list.filter(remind_date=start_date)

    if search_query:
        reminders_list = reminders_list.filter(
            Q(remark__icontains=search_query) |
            Q(reminder_type__name__icontains=search_query) |
            Q(remind_date__icontains=search_query) |
            Q(responsible_persons__name__icontains=search_query)
        )

    # Prepare data for template
    reminders_data = []
    for index, reminder in enumerate(reminders_list, start=1):
        responsible_people = [{"id": p.id, "name": p.name} for p in reminder.responsible_persons.all()]
        reminders_data.append({
            "display_no": index,
            "no": reminder.no,
            "entry_date": reminder.entry_date,
            "reminder_type": reminder.reminder_type,
            "remark": reminder.remark,
            "remind_date": reminder.remind_date,
            "event_date": reminder.event_date,  # Make sure this is included
            "added_by": reminder.added_by,      # Make sure this is included
            "responsible_people": responsible_people
        })
    
    # Pagination
    paginator = Paginator(reminders_data, 15)  # Show 15 reminders per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, "reminder.html", {
        "page_obj": page_obj,
        "reminder_types": ReminderType.objects.all()
    })




from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Reminder, ReminderType, Employee

@login_required
def add_reminder(request):
    # Fetch reminder types and employees for the form
    reminder_types = ReminderType.objects.all()
    employees = Employee.objects.all()

    # Handle GET request
    if request.method == 'GET':
        return render(request, 'add_reminder.html', {
            'reminder_types': reminder_types,
            'employees': employees,
            'form_data': {}  # Empty form data for initial render
        })

    # Handle POST request
    if request.method == 'POST':
        try:
            reminder_type_id = request.POST.get('reminder_type')
            remark = request.POST.get('remark')
            remind_date = request.POST.get('remind_date')
            event_date = request.POST.get('event_date') or None
            responsible_persons = request.POST.getlist('responsible_persons[]')

            # Create reminder with the currently logged-in user
            reminder = Reminder.objects.create(
                reminder_type_id=reminder_type_id,
                remark=remark,
                remind_date=remind_date,
                event_date=event_date,
                added_by=request.user  # Automatically set to logged-in user
            )

            # Add responsible persons
            if responsible_persons:
                reminder.responsible_persons.set(responsible_persons)

            messages.success(request, 'Reminder added successfully.')
            return redirect('reminders')

        except Exception as e:
            # If there's an error, re-render the form with error message
            messages.error(request, f'Error adding reminder: {str(e)}')
            return render(request, 'add_reminder.html', {
                'reminder_types': reminder_types,
                'employees': employees,
                'error': str(e),
                'form_data': request.POST  # Preserve form data
            })

    # Fallback return if method is neither GET nor POST
    return render(request, 'add_reminder.html', {
        'reminder_types': reminder_types,
        'employees': employees,
        'form_data': {}
    })









# edit remainder views functions
@login_required
def edit_reminder(request, reminder_no):
    reminder = get_object_or_404(Reminder, no=reminder_no)
    reminder_types = ReminderType.objects.all()
    employees = Employee.objects.all()
    
    if request.method == 'POST':
        try:
            reminder.reminder_type_id = request.POST.get('reminder_type')
            reminder.remark = request.POST.get('remark')
            reminder.remind_date = request.POST.get('remind_date')
            reminder.event_date = request.POST.get('event_date') or None
            
            # Do NOT change the added_by user
            
            # Update responsible persons
            responsible_persons = request.POST.getlist('responsible_persons[]')
            reminder.save()
            reminder.responsible_persons.set(responsible_persons)

            messages.success(request, 'Reminder updated successfully.')
            return redirect('reminders')
        
        except Exception as e:
            messages.error(request, f'Error updating reminder: {str(e)}')
            return render(request, 'edit_reminder.html', {
                'reminder': reminder,
                'reminder_types': reminder_types,
                'employees': employees,
                'error': str(e)
            })
    
    return render(request, 'edit_reminder.html', {
        'reminder': reminder,
        'reminder_types': reminder_types,
        'employees': employees
    })




# delete remainder views function
@login_required
def delete_reminder(request, reminder_id):
    """View for deleting a reminder."""
    reminder = get_object_or_404(Reminder, no=reminder_id)
    
    try:
        reminder_no = reminder.no  # Store the no for the message
        reminder.delete()
        logger.info(f"Successfully deleted reminder #{reminder_no}")
        messages.success(request, f"Reminder #{reminder_no} was deleted successfully")
    except Exception as e:
        logger.error(f"Error deleting reminder: {e}")
        messages.error(request, f"Error deleting reminder: {e}")
    
    return redirect("reminders")



# adding indication based on remaind date
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.urls import reverse  # Add this import

@login_required
def base_context_processor(request):
    """Context processor to add reminder count to all templates."""
    # Get current date
    today = timezone.now().date()
    
    # Count reminders that are due today or in the past
    active_reminders_count = Reminder.objects.filter(remind_date__lte=today).count()
    
    # Check if we're currently on the reminders page
    is_reminders_page = request.path == reverse('reminders')
    
    # Get user's allowed menus
    allowed_menus = []
    if hasattr(request, 'user') and request.user.is_authenticated:
        try:
            user = User.objects.get(userid=request.user.username)
            if user.allowed_menus:
                allowed_menus = json.loads(user.allowed_menus)
        except User.DoesNotExist:
            pass
    
    return {
        'active_reminders_count': active_reminders_count,
        'is_reminders_page': is_reminders_page,
        'allowed_menus': allowed_menus
    }


# reminder related functions end here )




from django.views.decorators.csrf import csrf_exempt
from .models import Holiday
import json
from datetime import datetime

@csrf_exempt
def add_holiday(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            date_str = data.get('date')
            description = data.get('description', '')
            
            # Validate required fields
            if not date_str:
                return JsonResponse({
                    'success': False,
                    'error': 'Date is required'
                })
            
            try:
                # Convert string to date object
                date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                return JsonResponse({
                    'success': False,
                    'error': 'Invalid date format. Use YYYY-MM-DD'
                })
            
            # Check if holiday already exists
            if Holiday.objects.filter(date=date).exists():
                return JsonResponse({
                    'success': False,
                    'error': 'Holiday already exists for this date'
                })
            
            # Create the holiday
            holiday = Holiday.objects.create(
                date=date,
                description=description
            )
            
            return JsonResponse({
                'success': True,
                'holiday': {
                    'date': holiday.date.strftime('%Y-%m-%d'),
                    'description': holiday.description
                }
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=400)
    return JsonResponse({
        'success': False,
        'error': 'Invalid request method'
    }, status=405)

def get_holidays(request):
    year = request.GET.get('year')
    month = request.GET.get('month')
    
    try:
        holidays = Holiday.objects.filter(
            date__year=year,
            date__month=month
        ).values('date', 'description')
        
        return JsonResponse({
            'success': True,
            'holidays': list(holidays)
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })
    


@csrf_exempt
def delete_holiday(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            date_str = data.get('date')
            
            if not date_str:
                return JsonResponse({
                    'success': False,
                    'error': 'Date is required'
                })
            
            try:
                date = datetime.strptime(date_str, '%Y-%m-%d').date()
                Holiday.objects.filter(date=date).delete()
                return JsonResponse({
                    'success': True,
                    'message': 'Holiday deleted successfully'
                })
            except ValueError:
                return JsonResponse({
                    'success': False,
                    'error': 'Invalid date format'
                })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=400)
    return JsonResponse({
        'success': False,
        'error': 'Invalid request method'
    }, status=405)



import requests
import json
from datetime import timedelta
from django.utils import timezone
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import LeaveRequest, Employee, Attendance

@login_required
def create_leave_request(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            employee = Employee.objects.get(user_id=request.session.get('custom_user_id'))
            
            start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
            end_date   = datetime.strptime(data['end_date'],   '%Y-%m-%d').date()
            note       = (data.get('note') or '').strip()  # NEW

            if not note:
                return JsonResponse({'success': False, 'error': 'Note is required'})

            leave_request = LeaveRequest.objects.create(
                employee=employee,
                start_date=start_date,
                end_date=end_date,
                leave_type=data['leave_type'],
                reason=data['reason'],   # keep Reason
                note=note,               # NEW
                status='pending'
            )

            phone_numbers = ["9946545535", "7593820007", "7593820005","9846754998","8129191379","9061947005"]
            
            formatted_start = start_date.strftime('%d-%m-%Y')
            formatted_end   = end_date.strftime('%d-%m-%Y')

            # Include NOTE in WhatsApp
            message = (
                f"New leave request from {employee.name}.\n"
                f"Type: {leave_request.get_leave_type_display()}\n"
                f"From: {formatted_start}  To: {formatted_end}\n"
                f"Reason: {data['reason']}\n"
                f"Note: {note}"
            )
            
            for number in phone_numbers:
                send_whatsapp_message_new_request(number, message)
            
            return JsonResponse({'success': True, 'message': 'Leave request submitted successfully'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})




import requests

def send_whatsapp_message_new_request(phone_number, message):
    """
    Send a WhatsApp message using the updated DxIng API.
    Automatically URL-encodes the message and handles connection errors.
    """
    secret = "7b8ae820ecb39f8d173d57b51e1fce4c023e359e"
    account = "1761365422812b4ba287f5ee0bc9d43bbf5bbe87fb68fc4daea92d8"  # ✅ updated account

    # Encode message safely for URL
    encoded_message = requests.utils.quote(message)

    # Build API URL
    url = (
        f"https://app.dxing.in/api/send/whatsapp?"
        f"secret={secret}"
        f"&account={account}"
        f"&recipient={phone_number}"
        f"&type=text"
        f"&message={encoded_message}"
        f"&priority=1"
    )

    try:
        response = requests.get(url, timeout=10)

        if response.status_code == 200:
            print(f"✅ WhatsApp message sent successfully to {phone_number}")
            return True
        else:
            print(
                f"❌ Failed to send WhatsApp message to {phone_number}. "
                f"Status code: {response.status_code}, Response: {response.text}"
            )
            return False

    except requests.exceptions.RequestException as e:
        print(f"⚠️ Error sending WhatsApp message: {e}")
        return False


@login_required
def get_leave_requests(request):
    status_filter = request.GET.get('status', None)
    
    if request.user.is_superuser or request.session.get('user_level') == 'normal':
        leave_requests = LeaveRequest.objects.all().select_related('employee').order_by('-created_at')
    else:
        employee = Employee.objects.get(user_id=request.session.get('custom_user_id'))
        leave_requests = LeaveRequest.objects.filter(employee=employee).select_related('employee').order_by('-created_at')

    if status_filter:
        leave_requests = leave_requests.filter(status=status_filter)
    
    data = [{
        'id': req.id,
        'employee_name': req.employee.name,
        'start_date': req.start_date.strftime('%d-%m-%Y'),
        'end_date': req.end_date.strftime('%d-%m-%Y'),
        'leave_type': req.get_leave_type_display(),
        'reason': req.reason,
        'note': req.note,                                # NEW
        'status': req.status,
        'processed_by': req.processed_by.username if req.processed_by else None,
        'processed_at': req.processed_at.strftime('%Y-%m-%d %H:%M') if req.processed_at else None,
        'created_at': req.created_at.strftime('%d-%m-%Y')
    } for req in leave_requests]
    
    return JsonResponse({'leave_requests': data})


# views.py (make sure these imports exist)
import json
from datetime import timedelta
from django.utils import timezone
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
import requests

from .models import Attendance, LeaveRequest, User  # <-- your custom User

@login_required
def process_leave_request(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method'})

    try:
        payload = json.loads(request.body or '{}')
        req_id = payload.get('request_id')
        action = (payload.get('action') or '').strip().lower()
        if action not in ('approve', 'reject'):
            return JsonResponse({'success': False, 'error': 'Invalid action'})

        leave_request = LeaveRequest.objects.get(id=req_id)

        # 1) Update status + Attendance (for leave only)
        if action == 'approve':
            leave_request.status = 'approved'
            current_date = leave_request.start_date
            while current_date <= leave_request.end_date:
                att, created = Attendance.objects.get_or_create(
                    employee=leave_request.employee,
                    date=current_date,
                    defaults={
                        'day': current_date.day,
                        'status': 'leave' if leave_request.leave_type == 'full_day' else 'half'
                    }
                )
                if not created:
                    att.status = 'leave' if leave_request.leave_type == 'full_day' else 'half'
                    att.save()
                current_date += timedelta(days=1)
        else:  # reject
            leave_request.status = 'rejected'
            current_date = leave_request.start_date
            while current_date <= leave_request.end_date:
                Attendance.objects.filter(
                    employee=leave_request.employee,
                    date=current_date,
                    status='leave'
                ).delete()
                current_date += timedelta(days=1)

        # 2) Audit
        leave_request.processed_by = request.user
        leave_request.processed_at = timezone.now()
        leave_request.save()

        # 3) WhatsApp (same helper as leave-create)
        approver_name = _display_name_for_user(request.user, request)
        emp = leave_request.employee
        emp_name = getattr(emp, 'name', None) or getattr(emp, 'employee_name', None) \
                   or f"{getattr(emp, 'first_name', '')} {getattr(emp, 'last_name', '')}".strip() \
                   or getattr(emp, 'userid', None) or "Employee"
        emp_poss = emp_name + ("'" if emp_name.lower().endswith('s') else "'s")

        if action == 'approve':
            msg = (
                f"✅ {emp_poss} leave request has been approved.\n"
                f"📅 {leave_request.start_date.strftime('%d-%m-%Y')} → {leave_request.end_date.strftime('%d-%m-%Y')}\n"
                f"📝 Reason: {leave_request.reason}\n"
                f"📌 Type: {leave_request.leave_type}\n"
                f"👤 Approved By: {approver_name}"
            )
        else:
            msg = (
                f"❌ {emp_poss} leave request has been rejected.\n"
                f"📅 {leave_request.start_date.strftime('%d-%m-%Y')} → {leave_request.end_date.strftime('%d-%m-%Y')}\n"
                f"📝 Reason: {leave_request.reason}\n"
                f"📌 Type: {leave_request.leave_type}\n"
                f"👤 Rejected By: {approver_name}"
            )

        recipients = []
        emp_phone = getattr(emp, 'phone_personal', None) or getattr(emp, 'phone_number', None)
        if emp_phone:
            recipients.append(str(emp_phone))
        if action == 'approve':
            recipients += ["9946545535","7593820007","7593820005","9846754998","8129191379","9061947005"]

        for r in recipients:
            send_whatsapp_message_new_request(r, msg)

        return JsonResponse({
            'success': True,
            'id': leave_request.id,
            'action': action,
            'status': leave_request.status
        })
    except LeaveRequest.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Leave request not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


def send_whatsapp_message_status_update(leave_request, action, approver_name=None):
    """Send WhatsApp message with detailed leave request information"""
    secret = "7b8ae820ecb39f8d173d57b51e1fce4c023e359e"
    account = "1756959119812b4ba287f5ee0bc9d43bbf5bbe87fb68b9118fcf1af"

    approver_name = (approver_name or "").strip() or "Admin"

    emp = getattr(leave_request, 'employee', None)
    emp_first_last = f"{getattr(emp, 'first_name', '')} {getattr(emp, 'last_name', '')}".strip() if emp else ''
    employee_name = (
        (getattr(emp, 'name', None) if emp else None)
        or (getattr(emp, 'employee_name', None) if emp else None)
        or (emp_first_last if emp_first_last else None)
        or (getattr(emp, 'userid', None) if emp else None)
        or "Employee"
    )
    employee_possessive = (employee_name + "'" if str(employee_name).strip().lower().endswith('s') else employee_name + "'s")

    if action == 'approve':
        message = (
            f"✅ {employee_possessive} leave request has been approved.\n"
            f"📅 Start Date: {leave_request.start_date.strftime('%d-%m-%Y')}\n"
            f"📅 End Date: {leave_request.end_date.strftime('%d-%m-%Y')}\n"
            f"📝 Reason: {leave_request.reason}\n"
            f"👤 Approved By: {approver_name}"
        )
    elif action == 'reject':
        message = (
            f"❌ {employee_possessive} leave request has been rejected.\n"
            f"📅 Start Date: {leave_request.start_date.strftime('%d-%m-%Y')}\n"
            f"📅 End Date: {leave_request.end_date.strftime('%d-%m-%Y')}\n"
            f"📝 Reason: {leave_request.reason}\n"
            f"👤 Rejected By: {approver_name}"
        )
    else:
        message = (
            f"ℹ️ {employee_possessive} leave request status updated.\n"
            f"📅 Start Date: {leave_request.start_date.strftime('%d-%m-%Y')}\n"
            f"📅 End Date: {leave_request.end_date.strftime('%d-%m-%Y')}\n"
            f"📝 Reason: {leave_request.reason}\n"
            f"📌 Status: {leave_request.status}\n"
            f"👤 Reviewed By: {approver_name}"
        )

    recipients = []
    employee_number = getattr(leave_request.employee, 'phone_personal', None) or getattr(leave_request.employee, 'phone_number', None)
    if employee_number:
        recipients.append(str(employee_number))
    if action == 'approve':
        recipients += ["9946545535"]

    if not recipients:
        print("⚠️ No recipients found to send WhatsApp message.")
        return False

    encoded_message = requests.utils.quote(message)
    all_ok = True
    for phone in recipients:
        url = (
            f"https://app.dxing.in/api/send/whatsapp?"
            f"secret={secret}&account={account}"
            f"&recipient={phone}"
            f"&type=text&message={encoded_message}&priority=1"
        )
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                print(f"✅ WhatsApp message sent successfully to {phone}")
            else:
                all_ok = False
                print(f"❌ Failed (status {response.status_code}) to {phone}: {response.text}")
        except requests.exceptions.RequestException as e:
            all_ok = False
            print(f"⚠️ Error sending WhatsApp message to {phone}: {e}")
    return all_ok







@login_required
def delete_leave_request(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            leave_request = LeaveRequest.objects.get(id=data['request_id'])
            
            # Only allow deletion if status is pending (for all users)
            if leave_request.status != 'pending':
                return JsonResponse({'success': False, 'error': 'Only pending requests can be deleted'})
            
            # Check if user is superuser or has user_level='normal'
            if not (request.user.is_superuser or request.session.get('user_level') == 'normal'):
                # For regular users, check ownership
                if leave_request.employee.user_id != request.session.get('custom_user_id'):
                    return JsonResponse({'success': False, 'error': 'You can only delete your own leave requests'})
            
            leave_request.delete()
            return JsonResponse({'success': True})
        except LeaveRequest.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Leave request not found'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Invalid request method'})





# views.py
@login_required
def create_late_request(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method'})

    try:
        data = json.loads(request.body or '{}')

        # who’s submitting
        custom_user_id = request.session.get('custom_user_id')
        if not custom_user_id:
            return JsonResponse({'success': False, 'error': 'Session expired. Please log in again.'})
        try:
            employee = Employee.objects.get(user_id=custom_user_id)
        except Employee.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Employee record not found for the logged-in user'})

        # inputs (same explicit parsing style as leave-create)
        raw_date   = (data.get('date') or '').strip()
        delay_time = (data.get('delay_time') or '').strip()  # string like '00:30' or '30m'
        reason     = (data.get('reason') or '').strip()

        if not raw_date or not delay_time or not reason:
            return JsonResponse({'success': False, 'error': 'date, delay_time and reason are required'})

        try:
            date_obj = datetime.strptime(raw_date, '%Y-%m-%d').date()
        except ValueError:
            return JsonResponse({'success': False, 'error': 'Invalid date format. Use YYYY-MM-DD'})

        # If your LateRequest.delay_time is a TimeField, parse like HH:MM
        # try:
        #     delay_time_obj = datetime.strptime(delay_time, '%H:%M').time()
        # except ValueError:
        #     return JsonResponse({'success': False, 'error': 'Invalid delay_time format. Use HH:MM'})
        # value_to_store = delay_time_obj
        value_to_store = delay_time  # keep string if your model is CharField

        # create
        lr = LateRequest.objects.create(
            employee=employee,
            date=date_obj,
            delay_time=value_to_store,
            reason=reason,
            status='pending'
        )

        # WhatsApp (same helper/account as leave-create)
        phone_numbers = ["9946545535","7593820007","7593820005","9846754998","8129191379","9061947005"]
        message = (
            f"New late request from {employee.name}.\n"
            f"Date: {date_obj.strftime('%d-%m-%Y')}\n"
            f"Delay Time: {delay_time}\n"
            f"Reason: {reason}"
        )
        for number in phone_numbers:
            send_whatsapp_message_new_request(number, message)

        return JsonResponse({'success': True, 'message': 'Late request submitted successfully', 'id': lr.id})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})



def send_whatsapp_message_new(phone_number, message):
    secret = "7b8ae820ecb39f8d173d57b51e1fce4c023e359e"
    account = "1756959119812b4ba287f5ee0bc9d43bbf5bbe87fb68b9118fcf1af"

    encoded_message = requests.utils.quote(message)
    url = (
        f"https://app.dxing.in/api/send/whatsapp?"
        f"secret={secret}&account={account}"
        f"&recipient={phone_number}"
        f"&type=text&message={encoded_message}&priority=1"
    )
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            print(f"✅ WhatsApp message sent successfully to {phone_number}")
            return True
        else:
            print(f"❌ Failed to send WhatsApp message to {phone_number}. "
                  f"Status code: {response.status_code}, Response: {response.text}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"⚠️ Error sending WhatsApp message: {e}")
        return False



# views.py
# views.py
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from .models import LateRequest, Employee
import json

@login_required
def get_late_requests(request):
    status_filter = request.GET.get('status', None)
    
    if request.user.is_superuser or request.session.get('user_level') == 'normal':
        late_requests = LateRequest.objects.all().select_related('employee')
        if status_filter:
            late_requests = late_requests.filter(status=status_filter)
    else:
        employee = Employee.objects.get(user_id=request.session.get('custom_user_id'))
        late_requests = LateRequest.objects.filter(employee=employee)
        if status_filter:
            late_requests = late_requests.filter(status=status_filter)
            
    data = [{
        'id': req.id,
        'employee_name': req.employee.name,
        'date': req.date.strftime('%Y-%m-%d'),
        'delay_time': req.delay_time,
        'reason': req.reason,
        'status': req.status,
        'created_at': req.created_at.strftime('%Y-%m-%d ')
    } for req in late_requests]
    
    return JsonResponse({'success': True, 'late_requests': data})

# at top of views.py ensure these imports exist:
# import requests
# from .models import User  # your custom User model

@login_required
def process_late_request(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method'})

    try:
        payload = json.loads(request.body or '{}')
        req_id = payload.get('request_id')
        action = (payload.get('action') or '').strip().lower()
        if action not in ('approve', 'reject'):
            return JsonResponse({'success': False, 'error': 'Invalid action'})

        lr = LateRequest.objects.get(id=req_id)

        # 1) Status
        lr.status = 'approved' if action == 'approve' else 'rejected'

        # 2) Audit
        lr.processed_by = request.user
        lr.processed_at = timezone.now()
        lr.save()

        # 3) WhatsApp (same helper as leave-create)
        approver_name = _display_name_for_user(request.user, request)
        emp = lr.employee
        emp_name = getattr(emp, 'name', None) or getattr(emp, 'employee_name', None) \
                   or f"{getattr(emp, 'first_name', '')} {getattr(emp, 'last_name', '')}".strip() \
                   or getattr(emp, 'userid', None) or "Employee"
        emp_poss = emp_name + ("'" if emp_name.lower().endswith('s') else "'s")

        if action == 'approve':
            msg = (
                f"✅ {emp_poss} late request approved.\n"
                f"📅 Date: {lr.date.strftime('%d-%m-%Y')}\n"
                f"⏰ Delay Time: {lr.delay_time}\n"
                f"📝 Reason: {lr.reason}\n"
                f"👤 Approved By: {approver_name}"
            )
        else:
            msg = (
                f"❌ {emp_poss} late request rejected.\n"
                f"📅 Date: {lr.date.strftime('%d-%m-%Y')}\n"
                f"⏰ Delay Time: {lr.delay_time}\n"
                f"📝 Reason: {lr.reason}\n"
                f"👤 Rejected By: {approver_name}"
            )

        recipients = []
        emp_phone = getattr(emp, 'phone_personal', None) or getattr(emp, 'phone_number', None)
        if emp_phone:
            recipients.append(str(emp_phone))
        if action == 'approve':
            recipients += ["9946545535","7593820007","7593820005","9846754998","8129191379","9061947005"]

        for r in recipients:
            send_whatsapp_message_new_request(r, msg)

        return JsonResponse({'success': True, 'id': lr.id, 'action': action, 'status': lr.status})
    except LateRequest.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Late request not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})




@login_required
def delete_late_request(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            late_request = LateRequest.objects.get(id=data['request_id'])
            
            # Only allow deletion if status is pending (for all users)
            if late_request.status != 'pending':
                return JsonResponse({'success': False, 'error': 'Only pending requests can be deleted'})
            
            # Check if user is superuser or has user_level='normal'
            if not (request.user.is_superuser or request.session.get('user_level') == 'normal'):
                # For regular users, check ownership
                if late_request.employee.user_id != request.session.get('custom_user_id'):
                    return JsonResponse({'success': False, 'error': 'You can only delete your own late requests'})
            
            late_request.delete()
            return JsonResponse({'success': True})
        except LateRequest.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Late request not found'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Invalid request method'})








from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.utils import timezone
from django.utils.timezone import localtime
from datetime import datetime
from .models import Employee, Attendance, Holiday

from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.utils import timezone
from django.utils.timezone import localtime
from datetime import datetime
from .models import Employee, Attendance, Holiday

from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.utils import timezone
from django.utils.timezone import localtime
from datetime import datetime
from .models import Employee, Attendance, Holiday

def attendance_summary(request, employee_id):
    employee = get_object_or_404(Employee, id=employee_id)
    now = timezone.now()
    year = request.GET.get('year', now.year)
    month = request.GET.get('month', now.month)
    user_name_filter = request.GET.get('user_name', '')

    try:
        year = int(year)
        month = int(month)
    except (ValueError, TypeError):
        year = now.year
        month = now.month

    # Filter attendance records based on user name if provided
    if user_name_filter:
        selected_employee = Employee.objects.filter(name__icontains=user_name_filter).first()
        if selected_employee:
            attendance_records = Attendance.objects.filter(
                employee=selected_employee,
                date__year=year,
                date__month=month
            ).order_by('date')
        else:
            attendance_records = Attendance.objects.none()
    else:
        attendance_records = Attendance.objects.filter(
            employee=employee,
            date__year=year,
            date__month=month
        ).order_by('date')

    holidays = Holiday.objects.filter(
        date__year=year,
        date__month=month
    ).values_list('date', flat=True)

    if month == 12:
        days_in_month = (datetime(year + 1, 1, 1) - datetime(year, month, 1)).days
    else:
        days_in_month = (datetime(year, month + 1, 1) - datetime(year, month, 1)).days

    attendance_data = []
    full_day_count = verified_full_day_count = half_day_count = verified_half_day_count = leave_count = not_marked_count = 0

    for day in range(1, days_in_month + 1):
        date = datetime(year, month, day).date()
        day_name = date.strftime('%A')
        record = next((r for r in attendance_records if r.date == date), None)

        if date in holidays:
            status = 'Holiday'
            status_class = 'holiday'
        elif record:
            if record.status == 'full':
                status = 'Full Day'
                status_class = 'full-day'
                full_day_count += 1
            elif record.status == 'verified_full':
                status = 'Verified Full Day'
                status_class = 'verified-full-day'
                verified_full_day_count += 1
            elif record.status == 'half':
                status = 'Half Day'
                status_class = 'half-day'
                half_day_count += 1
            elif record.status == 'verified_half':
                status = 'Verified Half Day'
                status_class = 'verified-half-day'
                verified_half_day_count += 1
            elif record.status == 'leave':
                status = 'Leave'
                status_class = 'leave'
                leave_count += 1
            else:
                status = 'Not Marked'
                status_class = 'not-marked'
                not_marked_count += 1
        else:
            status = 'Not Marked'
            status_class = 'not-marked'
            not_marked_count += 1

        punch_in = (
            localtime(record.punch_in).strftime('%I:%M %p')
            if record and record.punch_in else '-'
        )
        punch_out = (
            localtime(record.punch_out).strftime('%I:%M %p')
            if record and record.punch_out else '-'
        )

        attendance_data.append({
            'date': date.strftime('%Y-%m-%d'),
            'display_date': date.strftime('%d %b %Y'),
            'day': day_name,
            'status': status,
            'status_class': status_class,
            'punch_in': punch_in,
            'punch_out': punch_out,
            'punch_in_location': record.punch_in_location if record and record.punch_in_location else '-',
            'punch_out_location': record.punch_out_location if record and record.punch_out_location else '-',
            'punch_in_latitude': record.punch_in_latitude if record else None,
            'punch_in_longitude': record.punch_in_longitude if record else None,
            'punch_out_latitude': record.punch_out_latitude if record else None,
            'punch_out_longitude': record.punch_out_longitude if record else None,
            'note': record.note if record and record.note else '',  # Ensure note is included
        })

    context = {
        'employee': employee,
        'attendance_data': attendance_data,
        'year': year,
        'month': month,
        'month_name': datetime(year, month, 1).strftime('%B %Y'),
        'full_day_count': full_day_count,
        'verified_full_day_count': verified_full_day_count,
        'half_day_count': half_day_count,
        'verified_half_day_count': verified_half_day_count,
        'leave_count': leave_count,
        'not_marked_count': not_marked_count,
        'current_year': now.year,
        'current_month': now.month,
        'user_name_filter': user_name_filter,
        'selected_employee_name': selected_employee.name if user_name_filter and selected_employee else employee.name,
        'employees': Employee.objects.filter(status='active').order_by('name'),
    }

    return render(request, 'attendance_summary.html', context)


from django.shortcuts import render
from django.utils import timezone
from calendar import monthrange
from datetime import datetime
from .models import Employee, Attendance, Holiday

from django.contrib.auth.decorators import login_required

from django.shortcuts import render
from django.utils import timezone
from calendar import monthrange
from datetime import datetime
from .models import Employee, Attendance, Holiday
from django.contrib.auth.decorators import login_required
@login_required
def attendance_total_summary(request):
    year = int(request.GET.get('year', timezone.now().year))
    month = int(request.GET.get('month', timezone.now().month))

    employees = Employee.objects.select_related('user').filter(status='active')
    days_in_month = monthrange(year, month)[1]
    start_date = datetime(year, month, 1).date()
    end_date = datetime(year, month, days_in_month).date()

    holidays = Holiday.objects.filter(date__range=(start_date, end_date))
    holiday_dates = set(h.date for h in holidays)
    holidays_count = len(holiday_dates)

    employee_summaries = []

    for employee in employees:
        attendance_records = Attendance.objects.filter(employee=employee, date__range=(start_date, end_date))

        full_days = attendance_records.filter(status='full').count()
        verified_full_days = attendance_records.filter(status='verified_full').count()
        half_days = attendance_records.filter(status='half').count()
        verified_half_days = attendance_records.filter(status='verified_half').count()
        leaves = attendance_records.filter(status='leave').count()

        marked_dates = set(attendance_records.values_list('date', flat=True))
        not_marked = days_in_month - len(marked_dates | holiday_dates)
        working_days = days_in_month - holidays_count

        employee_summaries.append({
            'id': employee.id,
            'name': employee.name,
            'full_days': full_days,
            'verified_full_days': verified_full_days,
            'half_days': half_days,
            'verified_half_days': verified_half_days,
            'leaves': leaves,
            'not_marked': not_marked,
            'holidays': holidays_count,
            'number_of_days': days_in_month,
            'working_days': working_days,
            'total_attendance': full_days + verified_full_days + (0.5 * half_days) + (0.5 * verified_half_days),
        })

    return render(request, 'attendance_total_summary.html', {
        'employee_summaries': employee_summaries,
        'current_year': year,
        'current_month': f"{month:02}",
    })









#Project Management







from django.shortcuts import get_object_or_404

from .models import Employee  # make sure Employee is imported
from .models import Employee  # make sure Employee is imported

def add_project(request):
    # Get all employees
    employees = Employee.objects.select_related('user').all()
    project=Project.objects.all()

    if request.method == "POST":
        employee_id = request.POST.get('assigned_person')
        employee = get_object_or_404(Employee, id=employee_id) if employee_id else None

        Project.objects.create(
            project_name=request.POST['project_name'],
            languages=request.POST['languages'],
            technologies=request.POST['technologies'],
            description=request.POST['description'],
            database_name=request.POST['database_name'],
            domain_name=request.POST['domain_name'],
            domain_platform=request.POST['domain_platform'],
            github_link=request.POST['github_link'],
            assigned_person=employee,
            client=request.POST['client'],
            project_status=request.POST['project_status'],
            project_type=request.POST['project_type'],
            project_duration=request.POST['project_duration'],
        )
        return redirect('project_management')

    return render(request, "add_project.html", {"employees": employees})


from django.shortcuts import render, redirect, get_object_or_404
from .models import Project, Employee
from django.contrib import messages

def edit_project(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    employees = Employee.objects.select_related('user').all()

    if request.method == "POST":
        user_id = request.POST.get('assigned_person')
        employee = get_object_or_404(Employee, user_id=user_id) if user_id else None

        project.project_name = request.POST['project_name']
        project.languages = request.POST['languages']
        project.technologies = request.POST['technologies']
        project.description = request.POST['description']
        project.database_name = request.POST['database_name']
        project.domain_name = request.POST['domain_name']
        project.domain_platform = request.POST['domain_platform']
        project.github_link = request.POST['github_link']
        project.assigned_person = employee
        project.client = request.POST['client']
        project.project_status = request.POST['project_status']
        project.project_type = request.POST['project_type']
        project.project_duration = request.POST['project_duration']
        project.save()
        messages.success(request, "Project updated successfully!")
        return redirect('project_management')

    return render(request, 'project_edit.html', {'project': project, 'employees': employees})


def delete_project(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    project.delete()
    messages.success(request, "Project deleted successfully!")
    return redirect('project_management')



@login_required
def get_active_employees(request):
    """API endpoint to get active employees"""
    try:
        active_employees = Employee.objects.filter(status='active').values('id', 'name')
        return JsonResponse(list(active_employees), safe=False)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.shortcuts import render
from .models import Project, Employee
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.shortcuts import render
from .models import Project, Employee

def project_management(request):
    projects = Project.objects.all()
    employees = Employee.objects.select_related('user').all()

    # Get filter parameters from request
    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    project_name_filter = request.GET.get('project_name', '')
    languages_filter = request.GET.get('languages', '')
    database_filter = request.GET.get('database', '')
    domain_platform_filter = request.GET.get('domain_platform', '')
    assigned_person_filter = request.GET.get('assigned_person', '')
    client_filter = request.GET.get('client', '')
    project_type_filter = request.GET.get('project_type', '')

    # Apply filters
    if search_query:
        projects = projects.filter(project_name__icontains=search_query)
    if status_filter and status_filter != 'all':
        projects = projects.filter(project_status=status_filter)
    if project_name_filter:
        projects = projects.filter(project_name__icontains=project_name_filter)
    if languages_filter:
        projects = projects.filter(languages__icontains=languages_filter)
    if database_filter:
        projects = projects.filter(database_name__icontains=database_filter)
    if domain_platform_filter:
        projects = projects.filter(domain_platform__icontains=domain_platform_filter)
    if assigned_person_filter:
        projects = projects.filter(assigned_person__id=assigned_person_filter)
    if client_filter:
        projects = projects.filter(client__icontains=client_filter)
    if project_type_filter and project_type_filter != 'all':
        projects = projects.filter(project_type=project_type_filter)

    # Set up pagination
    paginator = Paginator(projects, 15)  # Show 15 projects per page
    page = request.GET.get('page')

    try:
        projects = paginator.page(page)
    except PageNotAnInteger:
        projects = paginator.page(1)
    except EmptyPage:
        projects = paginator.page(paginator.num_pages)

    # Prepare filter parameters to pass to template for pagination links
    filter_params = {
        'search': search_query,
        'status': status_filter,
        'project_name': project_name_filter,
        'languages': languages_filter,
        'database': database_filter,
        'domain_platform': domain_platform_filter,
        'assigned_person': assigned_person_filter,
        'client': client_filter,
        'project_type': project_type_filter
    }

    return render(request, 'project_management.html', {
        'projects': projects,
        'employees': employees,
        'filter_params': filter_params,
        'search_query': search_query
    })




from django.shortcuts import get_object_or_404

from .models import Employee  # make sure Employee is imported
from .models import Employee  # make sure Employee is imported

def add_project(request):
    # Get all employees
    employees = Employee.objects.select_related('user').all()
    
    if request.method == "POST":
        employee_id = request.POST.get('assigned_person')
        employee = get_object_or_404(Employee, id=employee_id) if employee_id else None
        deadline = request.POST.get('deadline') if request.POST.get('deadline') else None
        
        Project.objects.create(
            project_name=request.POST['project_name'],
            languages=request.POST['languages'],
            technologies=request.POST['technologies'],
            notes=request.POST['notes'],  # Changed from description to notes
            database_name=request.POST['database_name'],
            domain_name=request.POST['domain_name'],
            domain_platform=request.POST['domain_platform'],
            github_link=request.POST['github_link'],
            assigned_person=employee,
            client=request.POST['client'],
            project_status=request.POST['project_status'],
            project_type=request.POST['project_type'],
            project_duration=request.POST['project_duration'],
            deadline=deadline,  # Add this line

        )
        return redirect('project_management')
    
    return render(request, "add_project.html", {"employees": employees})

from django.shortcuts import render, redirect, get_object_or_404
from .models import Project, Employee
from django.contrib import messages

def edit_project(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    employees = Employee.objects.select_related('user').all()

    if request.method == "POST":
        user_id = request.POST.get('assigned_person')
        employee = get_object_or_404(Employee, user_id=user_id) if user_id else None

        project.project_name = request.POST['project_name']
        project.languages = request.POST['languages']
        project.technologies = request.POST['technologies']
        project.notes = request.POST['notes']  # Changed from description to notes
        project.database_name = request.POST['database_name']
        project.domain_name = request.POST['domain_name']
        project.domain_platform = request.POST['domain_platform']
        project.github_link = request.POST['github_link']
        project.assigned_person = employee
        project.client = request.POST['client']
        project.project_status = request.POST['project_status']
        project.project_type = request.POST['project_type']
        project.project_duration = request.POST['project_duration']
        project.deadline = request.POST.get('deadline') if request.POST.get('deadline') else None
        
        project.save()
        messages.success(request, "Project updated successfully!")
        return redirect('project_management')

    return render(request, 'project_edit.html', {'project': project, 'employees': employees})


def delete_project(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    project.delete()
    messages.success(request, "Project deleted successfully!")
    return redirect('project_management')



@login_required
def get_active_employees(request):
    """API endpoint to get active employees"""
    try:
        active_employees = Employee.objects.filter(status='active').values('id', 'name')
        return JsonResponse(list(active_employees), safe=False)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from .models import Project, Employee, ProjectWork

@login_required
def project_work(request):
    """View for project work management"""

    # Fetch all projects and active employees
    projects = Project.objects.all().order_by('project_name')
    employees = Employee.objects.filter(status='active').values('id', 'name', 'status')
    
    # Fetch project works with related project (FK) and members (ManyToMany)
    project_works = ProjectWork.objects.select_related(
        'project'
    ).prefetch_related(
        'members'
    ).all().order_by('-start_date')

    if request.method == 'POST':
        project_id = request.POST.get('project')
        member_ids = request.POST.getlist('members')  # Get multiple selected members
        start_date = request.POST.get('start_date')
        deadline = request.POST.get('deadline')
        client = request.POST.get('client')
        status = request.POST.get('status')

        try:
            project = Project.objects.get(id=project_id)

            # Create a new ProjectWork instance
            project_work = ProjectWork.objects.create(
                project=project,
                start_date=start_date,
                deadline=deadline,
                client=client,
                status=status
            )

            # Add selected members
            for member_id in member_ids:
                member = Employee.objects.get(id=member_id, status='active')
                project_work.members.add(member)

            messages.success(request, "Project work assigned successfully!")
            return redirect('project_work')

        except Project.DoesNotExist:
            messages.error(request, "Selected project does not exist.")
        except Employee.DoesNotExist:
            messages.error(request, "Selected employee is not active or does not exist.")
        except Exception as e:
            messages.error(request, f"Error assigning work: {str(e)}")

    context = {
        'projects': projects,
        'employees': employees,
        'project_works': project_works,
    }

    return render(request, 'project.html', context)


@login_required
def user_projects(request):
    """View for displaying projects assigned to the logged-in user"""
    try:
        # Get the current user's employee record
        custom_user_id = request.session.get('custom_user_id')
        if not custom_user_id:
            return redirect('login')
            
        employee = Employee.objects.get(user_id=custom_user_id)
        
        # Get all project works assigned to this employee
        assigned_projects = ProjectWork.objects.filter(
            members=employee
        ).select_related('project').prefetch_related('members').order_by('-start_date')
        
        return render(request, 'user_project.html', {
            'assigned_projects': assigned_projects,
            'employee': employee
        })
        
    except Employee.DoesNotExist:
        messages.error(request, "Employee record not found")
        return redirect('login')
    except Exception as e:
        messages.error(request, f"Error fetching projects: {str(e)}")
        return redirect('login')

@login_required
def update_project_status(request):
    """Update the status of a project work"""
    if request.method == 'POST':
        project_work_id = request.POST.get('project_work_id')
        new_status = request.POST.get('status')
        
        try:
            # Get the project work and check if the user is assigned to it
            project_work = ProjectWork.objects.get(id=project_work_id)
            custom_user_id = request.session.get('custom_user_id')
            employee = Employee.objects.get(user_id=custom_user_id)
            
            # Check if the user is assigned to this project
            if employee in project_work.members.all():
                # Update the status
                project_work.status = new_status
                project_work.save()
                return JsonResponse({'success': True, 'message': 'Status updated successfully'})
            else:
                return JsonResponse({'success': False, 'message': 'You are not assigned to this project'}, status=403)
                
        except ProjectWork.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Project work not found'}, status=404)
        except Employee.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Employee record not found'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'message': f'Error: {str(e)}'}, status=500)
    
    return JsonResponse({'success': False, 'message': 'Invalid request method'}, status=400)





@login_required
def edit_project_work(request, work_id):
    """View for editing project work"""
    try:
        # Get the project work to edit
        project_work = ProjectWork.objects.get(id=work_id)
        
        # Fetch all projects and active employees
        projects = Project.objects.all().order_by('project_name')
        employees = Employee.objects.filter(status='active').values('id', 'name', 'status')
        
        # Get currently selected member IDs for pre-selecting in the form
        selected_members = list(project_work.members.values_list('id', flat=True))
        
        if request.method == 'POST':
            project_id = request.POST.get('project')
            member_ids = request.POST.getlist('members')  # Get multiple selected members
            start_date = request.POST.get('start_date')
            deadline = request.POST.get('deadline')
            client = request.POST.get('client')
            status = request.POST.get('status')

            try:
                project = Project.objects.get(id=project_id)

                # Update project work fields
                project_work.project = project
                project_work.start_date = start_date
                project_work.deadline = deadline
                project_work.client = client
                project_work.status = status
                project_work.save()

                # Clear and re-add members
                project_work.members.clear()
                for member_id in member_ids:
                    member = Employee.objects.get(id=member_id, status='active')
                    project_work.members.add(member)

                messages.success(request, "Project work updated successfully!")
                return redirect('project_work')

            except Project.DoesNotExist:
                messages.error(request, "Selected project does not exist.")
            except Employee.DoesNotExist:
                messages.error(request, "Selected employee is not active or does not exist.")
            except Exception as e:
                messages.error(request, f"Error updating work: {str(e)}")

        context = {
            'project_work': project_work,
            'projects': projects,
            'employees': employees,
            'selected_members': selected_members,
        }

        return render(request, 'projectwork_edit.html', context)
        
    except ProjectWork.DoesNotExist:
        messages.error(request, "Project work not found.")
        return redirect('project_work')
    except Exception as e:
        messages.error(request, f"Error: {str(e)}")
        return redirect('project_work')
    

@login_required
def delete_project_work(request, work_id):
    """Delete a project work assignment"""
    try:
        project_work = ProjectWork.objects.get(id=work_id)
        project_name = project_work.project.project_name
        
        # Delete the project work
        project_work.delete()
        
        messages.success(request, f"Project work for '{project_name}' has been deleted successfully.")
    except ProjectWork.DoesNotExist:
        messages.error(request, "Project work not found.")
    except Exception as e:
        messages.error(request, f"Error deleting project work: {str(e)}")
        
    return redirect('project_work')



from .models import Task, Project, Employee
from django.utils import timezone

@login_required
def add_task(request):
    projects = Project.objects.all()
    employees = Employee.objects.filter(status='active')

    if request.method == 'POST':
        try:
            title = request.POST['title']
            project_id = request.POST['project']
            start_date = request.POST.get('start_date', timezone.now().date())
            deadline_date = request.POST['deadline_date']
            assigned_to_id = request.POST['assigned_to']

            # Get the current logged-in user
            current_user = request.user
            
            # Find the employee record for the current user
            try:
                assigned_by_employee = Employee.objects.get(user=current_user)
            except Employee.DoesNotExist:
                # If no employee record exists (like for admin), create a dummy one or handle differently
                assigned_by_employee = None
                messages.warning(request, 'No employee record found for your account. Task will be marked as assigned by admin.')

            project = get_object_or_404(Project, id=project_id)
            assigned_to = get_object_or_404(Employee, id=assigned_to_id)

            Task.objects.create(
                title=title,
                project=project,
                start_date=start_date,
                deadline_date=deadline_date,
                assigned_to=assigned_to,
                assigned_by=assigned_by_employee if assigned_by_employee else None,
                status='Not Started'
            )
            messages.success(request, 'Task created successfully!')
            return redirect('task_list')
            
        except Exception as e:
            messages.error(request, f'Error creating task: {str(e)}')
            return render(request, 'add_task.html', {
                'projects': projects,
                'employees': employees,
                'form_data': request.POST
            })

    return render(request, 'add_task.html', {
        'projects': projects,
        'employees': employees
    })

from datetime import date, datetime
from datetime import date

def task_list(request):
    # Get today's date
    today = date.today()
    
    # Check if user is admin from session
    user_level = request.session.get('user_level')
    is_admin = user_level in ['admin_level', '5level'] or request.user.is_superuser
    # Get tasks based on user role

    if is_admin:
        tasks = Task.objects.all()
    else:
        # For non-admin users, get only tasks assigned to them
        try:
            custom_user_id = request.session.get('custom_user_id')
            employee = Employee.objects.get(user_id=custom_user_id)
            tasks = Task.objects.filter(assigned_to=employee)
        except Employee.DoesNotExist:
            tasks = Task.objects.none()
            messages.warning(request, 'No employee record found for your account.')

    task_data = []

    for task in tasks:
        start = task.start_date
        deadline = task.deadline_date

        total_days = (deadline - start).days
        days_remaining = (deadline - today).days
        elapsed_days = (today - start).days

        if total_days > 0:
            percent_complete = min(max(int((elapsed_days / total_days) * 100), 0), 100)
        else:
            percent_complete = 100

        task_data.append({
            'task': task,
            'total_days': total_days,
            'days_remaining': days_remaining,
            'percent_complete': percent_complete,
        })

    return render(request, 'task.html', {
        'task_data': task_data,
        'today': today,
        'is_admin': is_admin  # Pass this to template for conditional rendering
    })


from django.views.decorators.http import require_POST

@require_POST
@login_required
def update_task_status(request, task_id):
    task = get_object_or_404(Task, id=task_id)
    
    # Check if user is admin from session
    user_level = request.session.get('user_level')
    is_admin = user_level in ['admin_level', '5level'] or request.user.is_superuser
    is_assigned_employee = False
    
    try:
        custom_user_id = request.session.get('custom_user_id')
        employee = Employee.objects.get(user_id=custom_user_id)
        is_assigned_employee = (task.assigned_to == employee)
    except Employee.DoesNotExist:
        pass
    
    if not (is_admin or is_assigned_employee):
        messages.error(request, "You don't have permission to update this task.")
        return redirect('task_list')
    
    new_status = request.POST.get('status')
    if new_status in dict(Task.STATUS_CHOICES):
        task.status = new_status
        task.save()
        messages.success(request, "Task status updated successfully.")
    else:
        messages.error(request, "Invalid task status.")
    
    return redirect('task_list')






@login_required
def user_menu_control(request):
    users = User.objects.all()
    
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        if user_id:
            return redirect('configure_user_menu', user_id=user_id)
    
    return render(request, 'user_menu_control.html', {'users': users})

@login_required
def configure_user_menu(request, user_id):
    user = get_object_or_404(User, id=user_id)
    
    # Get all the main menus and their submenus from the template structure
    menus = [
        {
            'name': 'Administration',
            'icon': 'fas fa-tools',
            'submenus': [
                {'id': 'agent_list', 'name': 'Address Book', 'icon': 'fas fa-binoculars'},
                {'id': 'credential_management', 'name': 'Credential Management', 'icon': 'fas fa-key'},  
                {'id': 'document_list', 'name': 'Documentations', 'icon': 'fas fa-scroll'},
                {'id': 'reminders', 'name': 'Reminders', 'icon': 'fas fa-bell'},
                {'id': 'sim_management', 'name': 'SIM Management', 'icon': 'fas fa-sim-card'},

            ]
        },
        # Update the HR menu section in both views to:
        {
            'name': 'HR',
            'icon': 'fas fa-users-cog',
            'submenus': [
                {'id': 'job_roles', 'name': 'Duties and responsiblity', 'icon': 'fas fa-briefcase'},
                {'id': 'cv_management', 'name': 'CV Management', 'icon': 'fas fa-file-contract'},
                {'id': 'interview_management', 'name': 'Interview Management', 'icon': 'fas fa-user-tie'},
                {
                    'id': 'make_offer_letter', 
                    'name': 'Offer Letter', 
                    'icon': 'fas fa-file-signature',
                    'submenus': [
                        {'id': 'generate_offer_letter', 'name': 'Generate Offer Letter', 'icon': 'fas fa-file-export'}
                    ]
                },
                {'id': 'employee_management', 'name': 'Employee Management', 'icon': 'fas fa-users'},
                {'id': 'attendance', 'name': 'Attendance', 'icon': 'fas fa-user-check'},
                {'id': 'attendance_user', 'name': 'Punch in / Punch out', 'icon': 'fas fa-user-clock'},
                {
                    'id': 'make_salary_certificate', 
                    'name': 'Salary Certificate', 
                    'icon': 'fas fa-file-invoice-dollar',
                    'submenus': [
                        {'id': 'generate_salary_certificate', 'name': 'Generate Salary Certificate', 'icon': 'fas fa-file-pdf'}
                    ]
                },
                 {
                    'id': 'make_experience_certificate',
                    'name': 'Experience Certificate',
                    'icon': 'fas fa-award',
                    'submenus':[
                        {'id': 'generate_experience_certificate', 'name': 'Generate Experience Certificate', 'icon': 'fas fa-file-pdf'}
                    ]
                    
                    
                    
                    
                    }
            ]
        },
        {
            'name': 'Marketing',
            'icon': 'fas fa-bullhorn',
            'submenus': [
                {'id': 'all_leads', 'name': 'Leads(Admin Dashboard)', 'icon': 'fas fa-user'},
                {'id': 'user_dashboard', 'name': 'Leads(User Dashboard)', 'icon': 'fas fa-user'}
            ]
        },
        {
            'name': 'Services',
            'icon': 'fas fa-wrench',
            'submenus': [
                {'id': 'service_log',  'name': 'Service Log (Admin Dashboard)',  'icon': 'fas fa-book'},
                {'id': 'user_service_log',   'name': 'Service Log (User Dashboard)',   'icon': 'fas fa-book'},
                {'id': 'service_entry','name': 'Service Entry (Admin Dashboard)', 'icon': 'fas fa-plus-circle'},
                {'id': 'user_service_entry', 'name': 'Service Entry (User Dashboard)', 'icon': 'fas fa-plus-circle'},

                # ⬇️  NEW LINES
                {'id': 'assign_service_logs',      'name': 'Assign Service Logs(Admin Dashboard)',      'icon': 'fas fa-edit'},
                {'id': 'my_assigned_service_logs', 'name': 'My Assigned Service Logs(User Dashboard)', 'icon': 'fas fa-user'},

                
                
            ]
        },
        {
            'name': 'Projects',
            'icon': 'fas fa-project-diagram',
            'submenus': [
                {'id': 'project_work', 'name': 'Project Management(Admin Dashboard)', 'icon': 'fa-solid fa-people-roof'},
                {'id': 'user_projects', 'name': 'Project Works(User Dashboard)', 'icon': 'fa-solid fa-diagram-project'},  # New submenu
                {
                    'id': 'daily_task_admin',
                    'name': 'Daily Task(Admin dashboard)',
                    'icon': 'fa-solid fa-people-roof',
                    'submenus': []
                },
                {
                    'id': 'daily_task_user',
                    'name': 'Daily Task(User dashboard)',
                    'icon': 'fa-solid fa-people-roof',
                    'submenus': []
                },
            ]
        },   
        
       {
    'name': 'Information Centre',
    'icon': 'fas fa-photo-video',
    'submenus': [
        {'id': 'information_center', 'name': 'Information Centre', 'icon': 'fas fa-photo-video'},
        {'id': 'product_type_list', 'name': 'Product Type', 'icon': 'fas fa-tags'},
        {'id': 'product_category_list', 'name': 'Category', 'icon': 'fas fa-list-alt'},
        {'id': 'add_information_center', 'name': 'Add New Media', 'icon': 'fas fa-plus'},
        {'id': 'edit_information_center', 'name': 'Edit Media', 'icon': 'fas fa-edit'},
        {'id': 'delete_information_center', 'name': 'Delete Media', 'icon': 'fas fa-trash'}
    ]
},
{
    'name': 'PLANET',
    'icon': 'fas fa-globe',
    'submenus': [
        {'id': 'show_clients', 'name': 'Clients', 'icon': 'fas fa-users'},
        {'id': 'feeder_list', 'name': 'Feeder', 'icon': 'fas fa-tools'},
        {'id': 'feeder_status', 'name': 'Feeder Status', 'icon': 'fas fa-tools'},
        {'id': 'license_type', 'name': 'License Key', 'icon': 'fas fa-clipboard-check'},
        {'id': 'add_license', 'name': 'Add License', 'icon': 'fas fa-plus-circle'},
        {'id': 'license_edit', 'name': 'Edit License', 'icon': 'fas fa-edit'},
        {'id': 'license_delete', 'name': 'Delete License', 'icon': 'fas fa-trash'},
        {'id': 'key_request_list', 'name': 'Key Request', 'icon': 'fas fa-file-signature'},
        {'id': 'key_request', 'name': 'Add Key Request', 'icon': 'fas fa-plus-circle'},
        {'id': 'collections_list', 'name': 'Collections', 'icon': 'fas fa-coins'},
        {'id': 'image_capture', 'name': 'Image Capture', 'icon': 'fas fa-camera'},
        {'id': 'purchase_order', 'name': 'Purchase Order', 'icon': 'fas fa-file-invoice'},
    
        
    ]
},
{
    'name': 'Vehicle Management',
    'icon': 'fas fa-car',
    'submenus': [
        # include only the ones you actually route; keep/remove vehicle_list as needed
        {'id': 'fuel_management',  'name': 'Fuel Management', 'icon': 'fas fa-gas-pump'},
        {'id': 'fuel_monitoring',  'name': 'Vehicle Ledger',  'icon': 'fas fa-chart-line'},
        # {'id': 'vehicle_list',   'name': 'Vehicles',        'icon': 'fas fa-car-side'},  # optional
    ]
},
{
    'name': 'IMC Drive',
    'icon': 'fas fa-folder',
    'submenus': [
        {'id': 'drive_list',   'name': 'IMC Drive',    'icon': 'fas fa-folder'},
        {'id': 'drive_add',    'name': 'Add Folder',   'icon': 'fas fa-plus-circle'},
        {'id': 'drive_edit',   'name': 'Edit Folder',  'icon': 'fas fa-pen-to-square'},
        {'id': 'drive_delete', 'name': 'Delete Folder','icon': 'fas fa-trash'}
    ]
},


{
    'name': 'SYSMAC',
    'icon': 'fas fa-microchip',
    'submenus': [
        {'id': 'item_list', 'name': 'Stand By', 'icon': 'fas fa-users'},
        {'id': 'app5:jobcard_list', 'name': 'Job Card', 'icon': 'fas fa-id-card'},
        {'id': 'app5:jobcard_assign_table', 'name': 'Assigned Job', 'icon': 'fas fa-id-card-alt'},
    ]
},
{
    'name': 'Social Media',
    'icon': 'fas fa-share-alt',
    'submenus': [
        {'id': 'all_customers', 'name': 'Customer Master', 'icon': 'fas fa-users'},
        {'id': 'socialmedia_all_projects', 'name': 'Projects', 'icon': 'fas fa-project-diagram'},
        {'id': 'socialmedia_project_assignments', 'name': 'Projects Assign', 'icon': 'fas fa-clipboard'},
        {'id': 'socialmedia_all_tasks', 'name': 'Task Master', 'icon': 'fas fa-tasks'},
        {'id': 'user_socialmedia_project_assignments', 'name': 'Your Assignments', 'icon': 'fas fa-user-check'}
    ]
},
        {
            'name': 'ACCOUNTS',
            'icon': 'fas fa-money-bill-wave',
            'submenus': [
                {'id': 'debtors1_list',       'name': 'SYSMAC COMPUTERS-1', 'icon': 'fas fa-file-invoice-dollar'},
                {'id': 'imc1_list',           'name': 'IMCB LLP',           'icon': 'fas fa-coins'},
                {'id': 'imc2_list',           'name': 'IMC',                'icon': 'fas fa-hand-holding-usd'},
                {'id': 'sysmac_info_list',    'name': 'SYSMAC-INFO',        'icon': 'fas fa-money-check'},
                {'id': 'dq_list',             'name': 'DQ',                 'icon': 'fas fa-credit-card'},
            ]
        },
        {
            'name': 'User Management',
            'icon': 'fas fa-user-cog',
            'submenus': [
                {'id': 'users_table', 'name': 'Users List', 'icon': 'fas fa-users'},
                
            ]
        },
        {
            'name': 'Company',
            'icon': 'fas fa-building',
            'submenus': [
                {'id': 'vehicle_list', 'name': 'Vehicle Master', 'icon': 'fas fa-list-alt'},
                {'id': 'all_districts', 'name': 'District', 'icon': 'fas fa-map'},
                {'id': 'all_areas', 'name': 'Area', 'icon': 'fas fa-map-marker-alt'},
                {'id': 'all_locations', 'name': 'Location', 'icon': 'fas fa-chart-area'},
                {'id': 'all_branches', 'name': 'Offices\\Locations', 'icon': 'fas fa-code-branch'},
                {'id': 'department_list', 'name': 'Department', 'icon': 'fas fa-sitemap'},
            ]
        },

        # ======== NEW: Business Menu ========
        {
            'name': 'Business',
            'icon': 'fas fa-briefcase',
            'submenus': [
                {'id': 'reminder_type', 'name': 'Reminder Type', 'icon': 'fas fa-bell'},
                {'id': 'job_titles', 'name': 'Job Title', 'icon': 'fas fa-id-card'},
                {'id': 'all_department', 'name': 'Job Category', 'icon': 'fas fa-layer-group'},
                {'id': 'business_type_list', 'name': 'Business Type', 'icon': 'fas fa-binoculars'},
                {'id': 'all_requirements', 'name': 'Requirements', 'icon': 'fas fa-tasks'},
            ]
        },

        # ======== NEW: Planet Menu (user-control representation) ========
        {
            'name': 'Planet (Extras)',
            'icon': 'fas fa-globe',
            'submenus': [
                {'id': 'item_list', 'name': 'Item Master', 'icon': 'fas fa-boxes'},
                {'id': 'supplier_list', 'name': 'Suppliers', 'icon': 'fas fa-truck'},
                {'id': 'all_complaints', 'name': 'Complaints', 'icon': 'fas fa-bug'},
                {'id': 'software_table', 'name': 'Softwares', 'icon': 'fas fa-puzzle-piece'},
                {'id': 'all_hardwares', 'name': 'Hardware', 'icon': 'fas fa-desktop'},
            ]
        },

    ]
    
    # Get the user's currently allowed menus
    try:
        allowed_menus = json.loads(user.allowed_menus) if user.allowed_menus else []
    except json.JSONDecodeError:
        # If the user doesn't have any menus set up yet, apply default menus
        try:
            default_settings = DefaultSettings.objects.first()
            if default_settings and default_settings.default_menus:
                allowed_menus = json.loads(default_settings.default_menus)
            else:
                allowed_menus = []
        except (DefaultSettings.DoesNotExist, json.JSONDecodeError):
            allowed_menus = []
    
    if request.method == 'POST':
        # Get the selected menu items from the form
        selected_menus = []
        for key in request.POST:
            if key.startswith('menu_'):
                selected_menus.append(key.replace('menu_', ''))
                
        # Save the user's menu permissions
        user.allowed_menus = json.dumps(selected_menus)
        user.save()
        
        # Update session if editing own permissions
        if request.user.id == user.id:
            request.session['allowed_menus'] = selected_menus
        
        messages.success(request, f"Menu permissions for {user.name} have been updated.")
    
    return render(request, 'configure_user_menu.html', {
        'user': user,
        'menus': menus,
        'allowed_menus': allowed_menus
    })







@login_required
def default_menus(request):
    # Get all the main menus and their submenus from the template structure
    menus = [
        {
            'name': 'Administration',
            'icon': 'fas fa-tools',
            'submenus': [
                {'id': 'agent_list', 'name': 'Address Book', 'icon': 'fas fa-binoculars'},
                {'id': 'credential_management', 'name': 'Credential Management', 'icon': 'fas fa-key'},  
                {'id': 'document_list', 'name': 'Documentations', 'icon': 'fas fa-scroll'},
                {'id': 'reminders', 'name': 'Reminders', 'icon': 'fas fa-bell'}
            ]
        },
        {
            'name': 'HR',
            'icon': 'fas fa-users-cog',
            'submenus': [
                {'id': 'cv_management', 'name': 'CV Management', 'icon': 'fas fa-file-contract'},
                {'id': 'interview_management', 'name': 'Interview Management', 'icon': 'fas fa-user-tie'},
                {
                    'id': 'make_offer_letter', 
                    'name': 'Offer Letter', 
                    'icon': 'fas fa-file-signature',
                    'submenus': [
                        {'id': 'generate_offer_letter', 'name': 'Generate Offer Letter', 'icon': 'fas fa-file-export'}
                    ]
                },
                {'id': 'employee_management', 'name': 'Employee Management', 'icon': 'fas fa-users'},
                {'id': 'attendance', 'name': 'Attendance', 'icon': 'fas fa-user-check'},
                {'id': 'attendance_user', 'name': 'Punch in / Punch out', 'icon': 'fas fa-user-clock'},
                {
                    'id': 'make_salary_certificate', 
                    'name': 'Salary Certificate', 
                    'icon': 'fas fa-file-invoice-dollar',
                    'submenus': [
                        {'id': 'generate_salary_certificate', 'name': 'Generate Salary Certificate', 'icon': 'fas fa-file-pdf'}
                    ]
                },
                {
                    'id': 'make_experience_certificate',
                    'name': 'Experience Certificate',
                    'icon': 'fas fa-award',
                    'submenus':[
                        {'id': 'generate_experience_certificate', 'name': 'Generate Experience Certificate', 'icon': 'fas fa-file-pdf'}
                    ]
                    
                    
                    
                    
                    }
            ]
        },
        {
            'name': 'Marketing',
            'icon': 'fas fa-bullhorn',
            'submenus': [
                {'id': 'all_leads', 'name': 'Leads(Admin Dashboard)', 'icon': 'fas fa-user'},
                {'id': 'user_dashboard', 'name': 'Leads(User Dashboard)', 'icon': 'fas fa-user'}
            ]
        },
        {
            'name': 'Services',
            'icon': 'fas fa-wrench',
            'submenus': [
                {'id': 'service_log',  'name': 'Service Log (Admin Dashboard)',  'icon': 'fas fa-book'},
                {'id': 'service_entry','name': 'Service Entry (Admin Dashboard)', 'icon': 'fas fa-plus-circle'},

                # ⬇️  NEW LINES
                {'id': 'assign_service_logs',      'name': 'Assign Service Logs(Admin Dashboard)',      'icon': 'fas fa-edit'},
                {'id': 'my_assigned_service_logs', 'name': 'My Assigned Service Logs(User Dashboard)', 'icon': 'fas fa-user'},

                {'id': 'user_service_log',   'name': 'Service Log (User Dashboard)',   'icon': 'fas fa-book'},
                {'id': 'user_service_entry', 'name': 'Service Entry (User Dashboard)', 'icon': 'fas fa-plus-circle'},
            ]
        },

        {
            'name': 'Projects',
            'icon': 'fas fa-project-diagram',
            'submenus': [
                {'id': 'project_work', 'name': 'Project Management (Admin Dashboard)', 'icon': 'fa-solid fa-people-roof'},
                {'id': 'user_projects', 'name': 'Project Works (User Dashboard)', 'icon': 'fa-solid fa-diagram-project'},
                {
                    'id': 'daily_task_admin',
                    'name': 'Daily Task(Admin dashboard)',
                    'icon': 'fa-solid fa-people-roof',
                    'submenus': []
                },
                {
                    'id': 'daily_task_user',
                    'name': 'Daily Task(User dashboard)',
                    'icon': 'fa-solid fa-people-roof',
                    'submenus': []
                },
            ]
        },
        {
            'name': 'Master',
            'icon': 'fas fa-cog',
            'submenus': [
                {'id': 'all_districts', 'name': 'District', 'icon': 'fas fa-map'},
                {'id': 'all_areas', 'name': 'Area', 'icon': 'fas fa-map-marker-alt'},
                {'id': 'all_locations', 'name': 'Location', 'icon': 'fas fa-chart-area'},
                {'id': 'all_requirements', 'name': 'Requirements', 'icon': 'fas fa-tasks'},

                {'id': 'all_department', 'name': 'Department', 'icon': 'fas fa-building'},
                {'id': 'job_roles', 'name': 'Job Role', 'icon': 'fas fa-briefcase'},



                {'id': 'business_type_list', 'name': 'Business Type', 'icon': 'fas fa-binoculars'},
                {'id': 'job_titles', 'name': 'Job Title', 'icon': 'fas fa-search'},
                {'id': 'all_hardwares', 'name': 'Hardware', 'icon': 'fas fa-desktop'},
                {'id': 'all_complaints', 'name': 'Complaints', 'icon': 'fas fa-bug'},
                {'id': 'all_branches', 'name': 'Branch', 'icon': 'fas fa-code-branch'},
                {'id': 'users_table', 'name': 'Users', 'icon': 'fas fa-users'},
                {'id': 'reminder_type', 'name': 'Reminder Types', 'icon': 'fas fa-bell'}
            ]
        },
        {
            'name': 'Information Centre',
            'icon': 'fas fa-photo-video',
            'submenus': [
                {'id': 'information_center', 'name': 'Information Centre', 'icon': 'fas fa-photo-video'},
                {'id': 'product_type_list', 'name': 'Product Type', 'icon': 'fas fa-tags'},
                {'id': 'product_category_list', 'name': 'Category', 'icon': 'fas fa-list-alt'},
                {'id': 'add_information_center', 'name': 'Add New Media', 'icon': 'fas fa-plus'},
                {'id': 'edit_information_center', 'name': 'Edit Media', 'icon': 'fas fa-edit'},
                {'id': 'delete_information_center', 'name': 'Delete Media', 'icon': 'fas fa-trash'}
            ]
        },
        {
    'name': 'Social Media',
    'icon': 'fas fa-share-alt',
    'submenus': [
        {'id': 'all_customers', 'name': 'Customer Master', 'icon': 'fas fa-users'},
        {'id': 'socialmedia_all_projects', 'name': 'Projects', 'icon': 'fas fa-project-diagram'},
        {'id': 'socialmedia_project_assignments', 'name': 'Projects Assign', 'icon': 'fas fa-clipboard'},
        {'id': 'socialmedia_all_tasks', 'name': 'Task Master', 'icon': 'fas fa-tasks'},
        {'id': 'user_socialmedia_project_assignments', 'name': 'Your Assignments', 'icon': 'fas fa-user-check'}
    ]
},
        {
            'name': 'ACCOUNTS',
            'icon': 'fas fa-money-bill-wave',
            'submenus': [
                {'id': 'debtors1_list',       'name': 'SYSMAC COMPUTERS-1', 'icon': 'fas fa-file-invoice-dollar'},
                {'id': 'imc1_list',           'name': 'IMCB LLP',           'icon': 'fas fa-coins'},
                {'id': 'imc2_list',           'name': 'IMC',                'icon': 'fas fa-hand-holding-usd'},
                {'id': 'sysmac_info_list',    'name': 'SYSMAC-INFO',        'icon': 'fas fa-money-check'},
                {'id': 'dq_list',             'name': 'DQ',                 'icon': 'fas fa-credit-card'},
            ]
        },
    ]
    
    # Fetch current default menus from settings or database
    try:
        default_settings = DefaultSettings.objects.first()
        if default_settings and default_settings.default_menus:
            default_menus = json.loads(default_settings.default_menus)
        else:
            default_menus = []
    except (DefaultSettings.DoesNotExist, json.JSONDecodeError):
        default_menus = []
    
    if request.method == 'POST':
        # Get the selected menu items from the form
        selected_menus = []
        for key in request.POST:
            if key.startswith('menu_'):
                selected_menus.append(key.replace('menu_', ''))
                
        # Save the default menu settings
        if not default_settings:
            default_settings = DefaultSettings()
        
        default_settings.default_menus = json.dumps(selected_menus)
        default_settings.save()
        
        # Apply to all non-admin users if requested
        if 'apply_to_all' in request.POST and request.POST['apply_to_all'] == 'yes':
            users = User.objects.filter(user_level__isnull=True) | User.objects.exclude(user_level='admin')
            for user in users:
                user.allowed_menus = json.dumps(selected_menus)
                user.save()
            messages.success(request, "Default menus have been set and applied to all users.")
        else:
            messages.success(request, "Default menus have been set successfully.")
    
    return render(request, 'default_menus.html', {
        'menus': menus,
        'default_menus': default_menus
    })


from django.shortcuts import render, redirect
from django.utils import timezone
from .models import BreakTime, Employee

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.utils import timezone
from datetime import datetime
import pytz

from django.shortcuts import render, redirect
from django.utils import timezone
from .models import BreakTime, Employee
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.utils import timezone
from datetime import datetime
import pytz

@login_required
def handle_break_punch(request, action):
    if request.method == 'POST':
        employee_id = request.session.get('custom_user_id')
        employee = get_object_or_404(Employee, user_id=employee_id)

        indian_tz = pytz.timezone('Asia/Kolkata')
        now = datetime.now(indian_tz)
        today = now.date()

        if action == 'in':
            # Check if there's an active break (punch in without punch out)
            active_break = BreakTime.objects.filter(
                employee=employee,
                date=today,
                is_active=True,
                break_punch_in__isnull=False,
                break_punch_out__isnull=True
            ).first()
            
            if active_break:
                return JsonResponse({
                    'success': False, 
                    'error': 'You have an active break. Please punch out first.'
                })
                
            # Create new break entry
            break_time = BreakTime.objects.create(
                employee=employee,
                date=today,
                break_punch_in=now,
                is_active=True
            )
            return JsonResponse({
                'success': True, 
                'break_punch_in': now.strftime('%H:%M:%S')
            })

        elif action == 'out':
            # Find the most recent active break
            active_break = BreakTime.objects.filter(
                employee=employee,
                date=today,
                is_active=True,
                break_punch_in__isnull=False,
                break_punch_out__isnull=True
            ).order_by('-break_punch_in').first()
            
            if not active_break:
                return JsonResponse({
                    'success': False, 
                    'error': 'No active break found to punch out'
                })
                
            active_break.break_punch_out = now
            active_break.is_active = False
            active_break.save()
            
            return JsonResponse({
                'success': True, 
                'break_punch_out': now.strftime('%H:%M:%S')
            })

    return JsonResponse({'success': False, 'error': 'Invalid request'})


@login_required
def break_time_management(request):
    # Get selected date from request, default to today's date
    selected_date = request.GET.get('date')
    indian_tz = pytz.timezone('Asia/Kolkata')

    if selected_date:
        date_filter = datetime.strptime(selected_date, '%Y-%m-%d').date()
    else:
        date_filter = datetime.now(indian_tz).date()

    # Filter break times based on the selected date
    break_times = BreakTime.objects.filter(date=date_filter).order_by('-date', '-break_punch_in')

    for bt in break_times:
        if bt.break_punch_in and bt.break_punch_out:
            duration = bt.break_punch_out - bt.break_punch_in
            bt.duration = str(duration).split('.')[0]  # format as HH:MM:SS
        else:
            bt.duration = None

    return render(request, 'break_time_management.html', {
        'break_times': break_times,
        'selected_date': date_filter,
    })




from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from datetime import datetime
import pytz

@login_required
def get_break_status(request):
    employee_id = request.session.get('custom_user_id')
    employee = get_object_or_404(Employee, user_id=employee_id)
    
    indian_tz = pytz.timezone('Asia/Kolkata')
    now = datetime.now(indian_tz)
    today = now.date()
    
    # Check for active break (punch in without punch out)
    active_break = BreakTime.objects.filter(
        employee=employee,
        date=today,
        is_active=True,
        break_punch_in__isnull=False,
        break_punch_out__isnull=True
    ).order_by('-break_punch_in').first()
    
    all_breaks_today = BreakTime.objects.filter(
        employee=employee,
        date=today
    ).order_by('-break_punch_in')
    
    break_list = []
    for break_time in all_breaks_today:
        break_list.append({
            'punch_in': break_time.break_punch_in.astimezone(indian_tz).strftime('%H:%M:%S') if break_time.break_punch_in else None,
            'punch_out': break_time.break_punch_out.astimezone(indian_tz).strftime('%H:%M:%S') if break_time.break_punch_out else None,
            'is_active': break_time.is_active
        })
    
    response_data = {
        'success': True,
        'has_active_break': active_break is not None,
        'can_punch_in': active_break is None,
        'can_punch_out': active_break is not None,
        'breaks_today': break_list,
        'current_break_in': active_break.break_punch_in.astimezone(indian_tz).strftime('%H:%M:%S') if active_break else None
    }

    return JsonResponse(response_data)






# views.py
from django.contrib.auth import get_user_model
DjangoUser = get_user_model()

from datetime import datetime
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse

@login_required
def create_early_request(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method'})

    try:
        data = json.loads(request.body or '{}')

        # who’s submitting
        custom_user_id = request.session.get('custom_user_id')
        if not custom_user_id:
            return JsonResponse({'success': False, 'error': 'Session expired. Please log in again.'})
        try:
            employee = Employee.objects.get(user_id=custom_user_id)
        except Employee.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Employee record not found for the logged-in user'})

        # inputs (same explicit parsing style as leave-create)
        raw_date = (data.get('date') or '').strip()
        raw_time = (data.get('early_time') or '').strip()
        reason   = (data.get('reason') or '').strip()

        if not raw_date or not raw_time or not reason:
            return JsonResponse({'success': False, 'error': 'date, early_time and reason are required'})

        try:
            date_obj = datetime.strptime(raw_date, '%Y-%m-%d').date()
        except ValueError:
            return JsonResponse({'success': False, 'error': 'Invalid date format. Use YYYY-MM-DD'})

        try:
            time_obj = datetime.strptime(raw_time, '%H:%M').time()
        except ValueError:
            return JsonResponse({'success': False, 'error': 'Invalid early_time format. Use HH:MM'})

        # create
        er = EarlyRequest.objects.create(
            employee=employee,
            date=date_obj,
            early_time=time_obj,
            reason=reason,
            status='pending'
        )

        # WhatsApp (same helper/account as leave-create)
        phone_numbers = ["9946545535","7593820007","7593820005","9846754998","8129191379","9061947005"]
        message = (
            f"New early request from {employee.name}.\n"
            f"Date: {date_obj.strftime('%d-%m-%Y')}\n"
            f"Early Time: {time_obj.strftime('%H:%M')}\n"
            f"Reason: {reason}"
        )
        for number in phone_numbers:
            send_whatsapp_message_new_request(number, message)

        return JsonResponse({'success': True, 'message': 'Early request submitted successfully', 'id': er.id})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
def get_early_requests(request):
    status_filter = request.GET.get('status', None)
    
    if request.user.is_superuser or request.session.get('user_level') == 'normal':
        early_requests = EarlyRequest.objects.all().select_related('employee')
        if status_filter:
            early_requests = early_requests.filter(status=status_filter)
    else:
        employee = Employee.objects.get(user_id=request.session.get('custom_user_id'))
        early_requests = EarlyRequest.objects.filter(employee=employee)
        if status_filter:
            early_requests = early_requests.filter(status=status_filter)
            
    data = [{
        'id': req.id,
        'employee_name': req.employee.name,
        'date': req.date.strftime('%Y-%m-%d'),
        'early_time': req.early_time.strftime('%H:%M'),
        'reason': req.reason,
        'status': req.status,
        'created_at': req.created_at.strftime('%Y-%m-%d %H:%M')
    } for req in early_requests]
    
    return JsonResponse({'success': True, 'early_requests': data})


# import logging

# logger = logging.getLogger(__name__)

# Make sure these imports exist at the top of views.py:
# import json
# import requests
# from datetime import timedelta
# from django.utils import timezone
# from django.http import JsonResponse
# from django.contrib.auth.decorators import login_required
# from django.contrib.auth import get_user_model
# from .models import User  # <-- your custom User model with `name`

DjangoUser = get_user_model()

@login_required
def process_early_request(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method'})

    try:
        payload = json.loads(request.body or '{}')
        req_id = payload.get('request_id')
        action = (payload.get('action') or '').strip().lower()
        if action not in ('approve', 'reject'):
            return JsonResponse({'success': False, 'error': 'Invalid action'})

        er = EarlyRequest.objects.get(id=req_id)

        # 1) Status
        er.status = 'approved' if action == 'approve' else 'rejected'

        # 2) Audit
        er.processed_by = request.user
        er.processed_at = timezone.now()
        er.save()

        # 3) WhatsApp (same helper as leave-create)
        approver_name = _display_name_for_user(request.user, request)
        emp = er.employee
        emp_name = getattr(emp, 'name', None) or getattr(emp, 'employee_name', None) \
                   or f"{getattr(emp, 'first_name', '')} {getattr(emp, 'last_name', '')}".strip() \
                   or getattr(emp, 'userid', None) or "Employee"
        emp_poss = emp_name + ("'" if emp_name.lower().endswith('s') else "'s")

        if action == 'approve':
            msg = (
                f"✅ {emp_poss} early request approved.\n"
                f"📅 Date: {er.date.strftime('%d-%m-%Y')}\n"
                f"⏰ Early Time: {er.early_time.strftime('%H:%M')}\n"
                f"📝 Reason: {er.reason}\n"
                f"👤 Approved By: {approver_name}"
            )
        else:
            msg = (
                f"❌ {emp_poss} early request rejected.\n"
                f"📅 Date: {er.date.strftime('%d-%m-%Y')}\n"
                f"⏰ Early Time: {er.early_time.strftime('%H:%M')}\n"
                f"📝 Reason: {er.reason}\n"
                f"👤 Rejected By: {approver_name}"
            )

        recipients = []
        emp_phone = getattr(emp, 'phone_personal', None) or getattr(emp, 'phone_number', None)
        if emp_phone:
            recipients.append(str(emp_phone))
        if action == 'approve':
            recipients += ["9946545535","7593820007","7593820005","9846754998","8129191379","9061947005"]

        for r in recipients:
            send_whatsapp_message_new_request(r, msg)

        return JsonResponse({'success': True, 'id': er.id, 'action': action, 'status': er.status})
    except EarlyRequest.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Early request not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})




@login_required
def delete_early_request(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            early_request = EarlyRequest.objects.get(id=data['request_id'])
            
            # Only allow deletion if status is pending (for all users)
            if early_request.status != 'pending':
                return JsonResponse({'success': False, 'error': 'Only pending requests can be deleted'})
            
            # Check if user is superuser or has user_level='normal'
            if not (request.user.is_superuser or request.session.get('user_level') == 'normal'):
                # For regular users, check ownership
                if early_request.employee.user_id != request.session.get('custom_user_id'):
                    return JsonResponse({'success': False, 'error': 'You can only delete your own early requests'})
            
            early_request.delete()
            return JsonResponse({'success': True})
        except EarlyRequest.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Early request not found'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Invalid request method'})



# views.py

from django.core.paginator import Paginator
from django.shortcuts import render, redirect, get_object_or_404
from .models import ServiceLog, Complaint, ServiceLogComplaint, User
from django.utils import timezone
from django.db.models import Q, Count, Case, When
from datetime import datetime
from datetime import datetime, date
from django.contrib.auth.decorators import login_required
from .forms import ComplaintForm

from datetime import datetime, date
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import render
from .models import ServiceLog, User


# ✅ Updated `views.py`
from django.shortcuts import render
from django.core.paginator import Paginator
from datetime import date, datetime
from django.db.models import Count, Q
from .models import ServiceLog
from django.contrib.auth.models import User

def servicelog_list(request):
    today = date.today().strftime('%Y-%m-%d')

    customer_search        = request.GET.get('customer_search', '')
    added_by_filter        = request.GET.get('added_by', '')
    assigned_person_filter = request.GET.get('assigned_person', '')
    status_filter          = request.GET.get('status', '')
    complaint_status_filter = request.GET.get('complaint_status', 'Pending')
    complaint_filter       = request.GET.get('complaint_type', '')
    start_date_filter      = request.GET.get('start_date', today)
    end_date_filter        = request.GET.get('end_date', today)
    rows_str = request.GET.get('rows', '')          # let empty string be the default
    rows = int(rows_str) if rows_str else 10   # 🔁 rows parameter

    service_logs = (
        ServiceLog.objects
        .annotate(
            total_complaints=Count('servicelogcomplaint'),
            completed_complaints=Count(
                'servicelogcomplaint',
                filter=Q(servicelogcomplaint__status='Completed')
            )
        )
        .order_by('-id')
    )

    if customer_search:
        service_logs = service_logs.filter(customer_name__icontains=customer_search)

    if added_by_filter:
        try:
            added_by_id = int(added_by_filter)
            service_logs = service_logs.filter(added_by_id=added_by_id)
        except (ValueError, TypeError):
            pass

    if assigned_person_filter:
        try:
            assigned_person_id = int(assigned_person_filter)
            service_logs = service_logs.filter(assigned_person_id=assigned_person_id)
        except (ValueError, TypeError):
            pass

    if status_filter:
        service_logs = service_logs.filter(status=status_filter)

    if complaint_status_filter:
        logs_with_matching_status = set(
            service_logs.filter(servicelogcomplaint__status=complaint_status_filter)
            .values_list('id', flat=True)
        )
        logs_with_different_status = set(
            service_logs.exclude(servicelogcomplaint__status=complaint_status_filter)
            .filter(servicelogcomplaint__isnull=False)
            .values_list('id', flat=True)
        )
        logs_with_all_matching = logs_with_matching_status - logs_with_different_status
        service_logs = service_logs.filter(id__in=logs_with_all_matching)

    if complaint_filter:
        if complaint_filter == 'hardware':
            service_logs = service_logs.filter(
                servicelogcomplaint__complaint__complaint_type='hardware'
            ).distinct()
        elif complaint_filter == 'software':
            service_logs = service_logs.filter(
                servicelogcomplaint__complaint__complaint_type='software'
            ).distinct()

    if start_date_filter:
        try:
            start_date = datetime.strptime(start_date_filter, '%Y-%m-%d').date()
            service_logs = service_logs.filter(date__date__gte=start_date)
        except ValueError:
            pass

    if end_date_filter:
        try:
            end_date = datetime.strptime(end_date_filter, '%Y-%m-%d').date()
            service_logs = service_logs.filter(date__date__lte=end_date)
        except ValueError:
            pass

    for log in service_logs:
        if '-' in log.customer_name:
            log.customer_name = log.customer_name.split('-')[0].strip()

    paginator = Paginator(service_logs, rows)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    users = User.objects.all()

    return render(request, 'servic_log_admin.html', {
        'page_obj': page_obj,
        'users': users,
        'customer_search': customer_search,
        'added_by_filter': added_by_filter,
        'assigned_person_filter': assigned_person_filter,
        'status_filter': status_filter,
        'complaint_status_filter': complaint_status_filter,
        'complaint_filter': complaint_filter,
        'start_date_filter': start_date_filter,
        'end_date_filter': end_date_filter,
        'start_index': page_obj.start_index(),
        'rows_options': [10, 25, 50, 100],  # 🔁 add row options list
        'selected_rows': rows              # 🔁 currently selected value
    })


from app1.models import User, Complaint, ServiceLog, ServiceLogComplaint

import requests
import json
from django.shortcuts import render, redirect
from .models import ServiceLog, Complaint, ServiceLogComplaint, User
from django.utils import timezone

import requests

import requests

def fetch_customers():
    try:
        response = requests.get('https://rrcpython.imcbs.com/api/clients/all')
        response.raise_for_status()
        customers_data = response.json().get('data', [])
        customers = {
            customer['code']: {
                'name': customer['name'],
                'address': customer.get('address', '')
            } for customer in customers_data
        }
        return customers
    except requests.RequestException as e:
        print(f"Error fetching customers: {e}")
        return {}


import requests
from django.contrib import messages
from django.shortcuts import render, redirect
from .models import ServiceLog, Complaint, ServiceLogComplaint, User,ComplaintImage
from django.utils import timezone
from django.core.files.base import ContentFile
import base64
import requests
from django.contrib import messages
from django.shortcuts import render, redirect
from .models import ServiceLog, Complaint, ServiceLogComplaint, User, ComplaintImage
from django.utils import timezone
from django.core.files.base import ContentFile
import base64

# new import for software model
from software_master.models import Software

@login_required
def add_service_log(request):
    """
    Add a new ServiceLog.
    - Accepts optional `next` in GET or POST to redirect back to calling page after save.
    - Security: only allows relative-path `next` (starts with '/') or same-site absolute URL.
    """
    complaints = Complaint.objects.all()
    customers = fetch_customers()
    softwares = Software.objects.all()

    if request.method == 'POST':
        customer_input = request.POST.get('customer')  # dropdown search input
        customer_name = request.POST.get('customer_name')  # manual entry
        place = request.POST.get('place')
        complaint_type = request.POST.get('complaint_type', 'software')
        remarks = request.POST.get('remarks')
        phone_number = request.POST.get('phone_number')
        voice_blob = request.POST.get('voice_blob')

        # read selected software id (may be empty)
        software_id = request.POST.get('software', '')

        # Basic validation: require dropdown or manual name
        if not customer_input and not customer_name:
            return render(request, 'add_service_log.html', {
                'complaints': complaints,
                'customers': customers,
                'softwares': softwares,
                'error_message': 'Please select a customer from the dropdown or enter a customer name manually.'
            })

        # Get the custom user record (this project maps request.user.username -> User.userid)
        try:
            custom_user = User.objects.get(userid=request.user.username)
        except User.DoesNotExist:
            messages.error(request, "Authenticated user not found in custom User model.")
            return redirect('login')

        # If customer_input matches one of the fetched customers, append address like earlier logic
        if customer_input:
            matched = False
            for code, data in customers.items():
                if data.get('name', '').strip().lower() == customer_input.strip().lower():
                    address = data.get('address', '')
                    customer_name = f"{data.get('name')} - {address}" if address else data.get('name')
                    matched = True
                    break
            if not matched:
                customer_name = customer_input  # fallback to raw typed text

        # Create the ServiceLog (set assigned_person to the creator by default)
        log = ServiceLog.objects.create(
            customer_name=customer_name,
            place=place,
            complaint_type=complaint_type,
            remarks=remarks,
            phone_number=phone_number,
            added_by=custom_user,
            assigned_person=custom_user,
        )

        # Attach software if provided and if model supports it (defensive)
        if software_id:
            try:
                selected_software = Software.objects.get(id=software_id)
                try:
                    log.software = selected_software
                    log.save()
                except Exception:
                    try:
                        setattr(log, 'software_id', selected_software.id)
                        log.save()
                    except Exception:
                        # model does not support software field; ignore
                        pass
            except Software.DoesNotExist:
                # invalid id provided -> ignore
                pass
        else:
            # If empty selection and model supports it, ensure field is cleared
            try:
                if hasattr(log, 'software'):
                    log.software = None
                    log.save()
                elif hasattr(log, 'software_id'):
                    setattr(log, 'software_id', None)
                    log.save()
            except Exception:
                pass

        # Create ServiceLogComplaint rows and attach images
        complaint_ids = request.POST.getlist('complaints')
        for cid in complaint_ids:
            # safe: some browsers may send empty strings
            if not cid:
                continue
            try:
                int_cid = int(cid)
            except (ValueError, TypeError):
                continue
            note = request.POST.get(f'note_{cid}', '') or ''
            complaint_log = ServiceLogComplaint.objects.create(
                service_log=log,
                complaint_id=int_cid,
                note=note,
                assigned_person=custom_user
            )

            # Handle multiple images for each complaint
            images = request.FILES.getlist(f'images_{cid}')
            for image in images:
                ComplaintImage.objects.create(complaint_log=complaint_log, image=image)

        # Save voice blob if provided
        if voice_blob:
            try:
                format_part, audio_str = voice_blob.split(';base64,')
                audio_file = ContentFile(base64.b64decode(audio_str), name=f"voice_{log.id}.webm")
                log.voice_note.save(audio_file.name, audio_file)
                log.save()
            except Exception:
                # If anything goes wrong with voice blob handling, continue without failing save
                pass

        # Prepare and send WhatsApp message (keep your original message format)
        try:
            complaint_list = ', '.join([c.description for c in Complaint.objects.filter(id__in=complaint_ids)])
        except Exception:
            complaint_list = ''

        registered_person_name = getattr(custom_user, 'name', '')
        registered_person_phone = getattr(custom_user, 'phone_number', '')

        message = (
            f"Dear {customer_name.split('-')[0].strip()},\n\n"
            f"Your complaint has been added successfully.\n"
            f"Ticket Number: {getattr(log, 'ticket_number', '')}\n"
            f"Registered by: {registered_person_name}\n"
            f"Registered Person's Phone: {registered_person_phone}\n"
            f"Thank you for choosing our services.\n"
            f"Best regards,\n"
            f"IMC Business Solutions"
        )

        try:
            send_whatsapp_message_for_service_log(phone_number, message)
        except Exception:
            # Log/send silently — don't break the user flow if messaging fails
            pass

        # Redirect: respect `next` param if present (GET or POST). Only allow relative paths for safety.
        next_url = request.POST.get('next') or request.GET.get('next') or ''
        if next_url and (next_url.startswith('/') or next_url.startswith(request.build_absolute_uri('/'))):
            return redirect(next_url)

        # Fallback by user level (existing behavior)
        if custom_user.user_level == 'admin_level':
            return redirect('servicelog_list')
        else:
            return redirect('user_service_log')

    # GET -> render form
    return render(request, 'add_service_log.html', {
        'complaints': complaints,
        'customers': customers,
        'softwares': softwares
    })


from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from .models import ServiceLog, ServiceLogComplaint

@login_required
def get_service_history(request):
    customer_name = request.GET.get('customer_name', '')
    
    if not customer_name:
        return JsonResponse([], safe=False)
    
    # Get service logs for this customer - using 'date' field for ordering
    service_logs = ServiceLog.objects.filter(customer_name__icontains=customer_name).order_by('-date')
    
    service_history = []
    for log in service_logs:
        # Get complaints for this service log
        complaints = ServiceLogComplaint.objects.filter(service_log=log).select_related('complaint')
        complaint_data = [{
            'description': sc.complaint.description,
            'note': sc.note,
            'status': sc.status  # Get status from ServiceLogComplaint
        } for sc in complaints]
        
        # Format the customer name (remove address part if exists)
        display_customer_name = log.customer_name
        if '-' in log.customer_name:
            display_customer_name = log.customer_name.split('-')[0].strip()
        
        # Determine overall status based on complaints
        overall_status = 'Pending'
        if complaints:
            statuses = [sc.status for sc in complaints]
            if all(status == 'Completed' for status in statuses):
                overall_status = 'Completed'
            elif any(status == 'In Progress' for status in statuses):
                overall_status = 'In Progress'
            elif any(status == 'Completed' for status in statuses):
                overall_status = 'Partially Completed'
        
        service_history.append({
            'ticket_number': log.ticket_number,
            'service_date': log.date.isoformat() if log.date else '',
            'complaints': complaint_data,
            'remarks': log.remarks,
            'complaint_type': log.complaint_type,  # Use the raw value
            'status': overall_status,
            'assigned_person': log.assigned_person.name if log.assigned_person else 'Not assigned',
            'customer_name': display_customer_name
        })
    
    return JsonResponse(service_history, safe=False)
from django.shortcuts import render, redirect
import json

@login_required
def customer_details(request):
    """Render customer details page"""
    customer_data_json = request.GET.get('data', '{}')
    try:
        customer_data = json.loads(customer_data_json)
    except json.JSONDecodeError:
        customer_data = {}
    
    return render(request, 'customer_details.html', {
        'customer_data': customer_data
    })

from django.shortcuts import render, redirect
from .models import ServiceLog, Complaint, ServiceLogComplaint, ComplaintImage, User
from django.core.files.base import ContentFile
from django.utils import timezone
import base64
from django.contrib.auth.decorators import login_required  # added import

@login_required
def edit_service_log(request, log_id):
    # Load the service log and reference data
    log = get_object_or_404(ServiceLog, id=log_id)
    complaints = Complaint.objects.all()
    selected_complaints = ServiceLogComplaint.objects.filter(service_log=log)
    customers = fetch_customers()
    softwares = Software.objects.all()

    # Determine the "custom user" object for the logged-in user (same as in add_service_log)
    try:
        custom_user = User.objects.get(userid=request.user.username)
    except User.DoesNotExist:
        custom_user = None

    if request.method == 'POST':
        # Basic service log fields
        customer_input = request.POST.get('customer')
        customer_name = request.POST.get('customer_name')
        place = request.POST.get('place')
        complaint_type = request.POST.get('complaint_type', log.complaint_type)
        remarks = request.POST.get('remarks')
        phone_number = request.POST.get('phone_number')
        voice_blob = request.POST.get('voice_blob')

        # software handling (if provided)
        software_id = request.POST.get('software', '')

        # Normalize customer name (same logic as add_service_log)
        if customer_input:
            matched = False
            for code, data in customers.items():
                if data.get('name', '').strip().lower() == customer_input.strip().lower():
                    address = data.get('address', '')
                    customer_name = f"{data.get('name')} - {address}" if address else data.get('name')
                    matched = True
                    break
            if not matched:
                customer_name = customer_input
        elif not customer_name:
            customer_name = log.customer_name

        # Save main ServiceLog fields
        log.customer_name = customer_name
        log.place = place
        log.complaint_type = complaint_type
        log.remarks = remarks
        log.phone_number = phone_number

        # attach software safely if present
        if software_id:
            try:
                selected_software = Software.objects.get(id=software_id)
                try:
                    log.software = selected_software
                except Exception:
                    try:
                        setattr(log, 'software_id', selected_software.id)
                    except Exception:
                        pass
            except Software.DoesNotExist:
                pass
        else:
            try:
                if hasattr(log, 'software'):
                    log.software = None
                elif hasattr(log, 'software_id'):
                    setattr(log, 'software_id', None)
            except Exception:
                pass

        log.save()

        # --- Complaints sync logic (update/create/delete) ---
        posted_complaint_ids = request.POST.getlist('complaints')
        try:
            posted_ids = [int(x) for x in posted_complaint_ids if x and str(x).strip() != '']
        except ValueError:
            posted_ids = []

        # Map existing complaints by complaint_id
        existing_qs = ServiceLogComplaint.objects.filter(service_log=log)
        existing_map = {int(obj.complaint_id): obj for obj in existing_qs}

        processed_complaint_ids = set()

        if posted_ids:
            for cid in posted_ids:
                note = request.POST.get(f'note_{cid}', '') or ''

                # Determine default assigned_person for this new/updated complaint:
                # 1) prefer a per-complaint assigned_person_<cid> posted value (if you include this in template)
                # 2) else use the service log's assigned_person
                # 3) else fallback to the current custom_user
                assigned_person = None
                posted_assignee = request.POST.get(f'assigned_person_{cid}')
                if posted_assignee:
                    # Try interpret as pk first, then as userid string
                    try:
                        assigned_person = User.objects.get(id=int(posted_assignee))
                    except (ValueError, User.DoesNotExist):
                        try:
                            assigned_person = User.objects.get(userid=posted_assignee)
                        except User.DoesNotExist:
                            assigned_person = None

                if not assigned_person:
                    assigned_person = log.assigned_person or custom_user

                if cid in existing_map:
                    # Update existing ServiceLogComplaint
                    complaint_log = existing_map[cid]
                    complaint_log.note = note
                    # If form explicitly supplied assigned_person_<cid> overwrite; otherwise preserve existing
                    if request.POST.get(f'assigned_person_{cid}') or not complaint_log.assigned_person:
                        complaint_log.assigned_person = assigned_person
                    complaint_log.save()
                else:
                    # CREATE new ServiceLogComplaint and ensure assigned_person is set
                    complaint_log = ServiceLogComplaint.objects.create(
                        service_log=log,
                        complaint_id=cid,
                        note=note,
                        assigned_person=assigned_person
                    )

                processed_complaint_ids.add(cid)

                # Attach uploaded images for this complaint (works for new & existing complaints)
                images = request.FILES.getlist(f'images_{cid}')
                for image in images:
                    ComplaintImage.objects.create(complaint_log=complaint_log, image=image)

            # Remove any complaint rows that were unchecked/removed in the edit form
            to_delete_ids = [cid for cid in existing_map.keys() if cid not in processed_complaint_ids]
            if to_delete_ids:
                ServiceLogComplaint.objects.filter(service_log=log, complaint_id__in=to_delete_ids).delete()
        else:
            # No complaints posted: preserve existing complaint rows but still attach any uploaded images for them
            for cid, complaint_log in existing_map.items():
                images = request.FILES.getlist(f'images_{cid}')
                for image in images:
                    ComplaintImage.objects.create(complaint_log=complaint_log, image=image)

        # Redirect back to service log list (same behavior as before)
        return redirect('servicelog_list')

    # GET -> render the same add/edit template with existing data
    return render(request, 'add_service_log.html', {
        'log': log,
        'complaints': complaints,
        'selected_complaints': selected_complaints,
        'customers': customers,
        'softwares': softwares
    })






    
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from .models import ServiceLog, User

@login_required
def delete_service_log(request, log_id):
    # grab the log (404 if it doesn’t exist)
    log = get_object_or_404(ServiceLog, id=log_id)

    # delete it
    log.delete()

    # decide where to go next
    custom_user = User.objects.get(userid=request.user.username)
    if custom_user.user_level == 'admin_level':
        # admins → full admin list
        return redirect('servicelog_list')      #  renders servic_log_admin.html
    else:
        # normal users → their own list
        return redirect('user_service_log')     #  renders user_service_log.html





from django.core.paginator import Paginator
from django.utils import timezone
from django.shortcuts import render, redirect
from .models import ServiceLog, User
from django.contrib.auth.decorators import login_required

# views.py

def user_service_log(request):
    if request.user.is_authenticated:
        custom_user = User.objects.get(userid=request.user.username)
        user_service_logs = ServiceLog.objects.filter(added_by=custom_user).order_by('-id')

        # Preprocess customer_name to extract only the name part
        for log in user_service_logs:
            if '-' in log.customer_name:
                log.customer_name = log.customer_name.split('-')[0].strip()

        status_filter = request.GET.get('status', '')
        complaint_status_filter = request.GET.get('complaint_status', '')
        customer_search = request.GET.get('customer_search', '')
        start_date_filter = request.GET.get('start_date')
        end_date_filter = request.GET.get('end_date')

        if status_filter:
            user_service_logs = user_service_logs.filter(status=status_filter)

        if complaint_status_filter:
            user_service_logs = user_service_logs.filter(servicelogcomplaint__status=complaint_status_filter).distinct()

        if customer_search:
            user_service_logs = user_service_logs.filter(customer_name__icontains=customer_search)

        if start_date_filter and end_date_filter:
            user_service_logs = user_service_logs.filter(date__date__range=[start_date_filter, end_date_filter])

        users = User.objects.all()

        today_date = timezone.now().date().isoformat()

        # Pagination
        paginator = Paginator(user_service_logs, 10)  # Show 10 logs per page
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        return render(request, 'user_service_log.html', {
            'page_obj': page_obj,
            'users': users,
            'status_filter': status_filter,
            'complaint_status_filter': complaint_status_filter,
            'customer_search': customer_search,
            'start_date_filter': start_date_filter,
            'end_date_filter': end_date_filter,
            'today_date': today_date,
        })
    else:
        return redirect('login')


from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from .models import ServiceLog

@csrf_exempt
@require_POST
def update_status(request):
    data = json.loads(request.body)
    log_id = data.get('log_id')
    new_status = data.get('status')

    try:
        service_log = ServiceLog.objects.get(id=log_id)
        service_log.status = new_status
        service_log.save()
        return JsonResponse({'success': True})
    except ServiceLog.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Service log not found'})



from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from .models import ServiceLog

@login_required
def assign_service_logs(request):
    # Get the status filter from the request, default to 'Pending'
    status_filter = request.GET.get('status', 'Pending')
    
    # Fetch all service logs based on the status filter
    if status_filter == 'all':
        service_logs = ServiceLog.objects.all().order_by('-date')
    else:
        service_logs = ServiceLog.objects.filter(status=status_filter).order_by('-date')
    
    # Pagination - 10 items per page
    paginator = Paginator(service_logs, 10)
    page_number = request.GET.get('page')
    pending_service_logs = paginator.get_page(page_number)
    
    return render(request, 'assign_service_logs.html', {
        'pending_service_logs': pending_service_logs,
        'status_filter': status_filter,
        'paginator': paginator,
    })

import json
import requests
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.core.files.base import ContentFile
import base64
from .models import ServiceLog, Complaint, ServiceLogComplaint, User



@login_required
def assign_work(request, log_id):
    service_log = get_object_or_404(ServiceLog, id=log_id)
    users = User.objects.filter(status='active').order_by('name')
    complaints = service_log.servicelogcomplaint_set.all()
    
    if request.method == 'POST':
        # Handle individual complaint assignments
        for complaint_log in complaints:
            assigned_person_id = request.POST.get(f'assigned_person_{complaint_log.id}')
            if assigned_person_id:
                assigned_person = get_object_or_404(User, id=assigned_person_id)
                complaint_log.assigned_person = assigned_person
                complaint_log.save()
                
                # Send WhatsApp message to the assigned user
                message = (
                    f"Dear {assigned_person.name},\n\n"
                    f"You have been assigned a new service log.\n"
                    f"Ticket Number: {service_log.ticket_number}\n"
                    f"Customer Name: {service_log.customer_name}\n"
                    f"Complaint: {complaint_log.complaint.description}\n"
                    f"Please check the details and take necessary action.\n"
                    f"Best regards,\n"
                    f"IMC Business Solutions"
                )
                send_whatsapp_message_for_service_log(assigned_person.phone_number, message)
        
        messages.success(request, "Complaints assigned successfully")
        return redirect('assign_service_logs')
    
    return render(request, 'assign_work.html', {
        'service_log': service_log,
        'users': users,
        'complaints': complaints,
    })

@login_required
def my_assigned_service_logs(request):
    try:
        # Get the custom User instance based on the logged-in user
        custom_user = User.objects.get(userid=request.user.username)
    except User.DoesNotExist:
        messages.error(request, "User not found.")
        return redirect('login')

    # Get the status filter from the request, default to 'Active'
    status_filter = request.GET.get('status', 'Active')

    # Fetch service logs where user has assigned complaints
    if status_filter == 'all':
        assigned_complaints = ServiceLogComplaint.objects.filter(
            assigned_person=custom_user
        ).select_related('service_log', 'complaint').order_by('-assigned_date')
    elif status_filter == 'Active':
        assigned_complaints = ServiceLogComplaint.objects.filter(
            assigned_person=custom_user, 
            status__in=['Pending', 'In Progress']
        ).select_related('service_log', 'complaint').order_by('-assigned_date')
    elif status_filter == 'Completed':
        assigned_complaints = ServiceLogComplaint.objects.filter(
            assigned_person=custom_user, 
            status='Completed'
        ).select_related('service_log', 'complaint').order_by('-assigned_date')

    # Group complaints by service log
    service_logs_dict = {}
    for complaint_log in assigned_complaints:
        service_log = complaint_log.service_log
        if service_log.id not in service_logs_dict:
            service_logs_dict[service_log.id] = {
                'service_log': service_log,
                'assigned_complaints': [],
            }
        service_logs_dict[service_log.id]['assigned_complaints'].append(complaint_log)

    # Get all active users
    users = User.objects.filter(status='active').order_by('name')

    return render(request, 'my_assigned_service_logs.html', {
        'service_logs_data': service_logs_dict.values(),
        'status_filter': status_filter,
        'default_assigned_person': custom_user,
        'users': users
    })


from django.utils import timezone
# views.py
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils import timezone
from .models import ServiceLogComplaint

@csrf_exempt
@require_POST
def update_complaint_status(request):
    """
    Update the status of a ServiceLogComplaint.
    Automatically sets started_time when status becomes 'In Progress'
    and completed_time when status becomes 'Completed'.
    When status becomes 'Completed', send a WhatsApp notification to:
      - the assigned person (if phone number present)
      - the customer (if service_log.phone_number present)
    """
    try:
        data = json.loads(request.body)
        cid = data.get('complaint_log_id') or data.get('complaint_id') or data.get('id')
        new_status = data.get('status')

        if not cid or not new_status:
            return JsonResponse({'success': False, 'error': 'Missing complaint_log_id or status'}, status=400)

        try:
            cid = int(cid)
        except (ValueError, TypeError):
            return JsonResponse({'success': False, 'error': 'complaint_log_id must be an integer'}, status=400)

        try:
            complaint_log = ServiceLogComplaint.objects.select_related('service_log', 'complaint', 'assigned_person').get(id=cid)
        except ServiceLogComplaint.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Complaint log not found'}, status=404)

        # Update timestamps
        if new_status == 'In Progress' and not complaint_log.started_time:
            complaint_log.started_time = timezone.now()
        elif new_status == 'Completed' and not complaint_log.completed_time:
            complaint_log.completed_time = timezone.now()

        complaint_log.status = new_status
        complaint_log.save()

        # If completed, send notifications
        if new_status == 'Completed':
            service_log = complaint_log.service_log
            complaint_desc = ''
            try:
                complaint_desc = complaint_log.complaint.description if complaint_log.complaint else ''
            except Exception:
                complaint_desc = ''

            completed_time_str = complaint_log.completed_time.strftime('%d-%m-%Y %H:%M') if complaint_log.completed_time else ''

            # Message to assigned person (if any)
            assigned_person = getattr(complaint_log, 'assigned_person', None)
            if assigned_person and getattr(assigned_person, 'phone_number', None):
                msg_assigned = (
                    f"✅ Work Completed\n\n"
                    f"Ticket: {service_log.ticket_number or '-'}\n"
                    f"Complaint: {complaint_desc or '-'}\n"
                    f"Completed On: {completed_time_str}\n"
                    f"Remarks: {complaint_log.note or '-'}\n\n"
                    f"Thanks,\nIMC Business Solutions"
                )
                # URL-encode the message to be safe in the GET URL
                try:
                    send_whatsapp_message_for_service_log(assigned_person.phone_number, requests.utils.quote(msg_assigned))
                except Exception as e:
                    # Don't fail the API if messaging fails; log to console
                    print(f"Error sending WhatsApp to assigned person: {e}")

            # Message to customer phone (if present on ServiceLog)
            customer_phone = getattr(service_log, 'phone_number', None) or getattr(service_log, 'customer_phone', None)
            if customer_phone:
                msg_customer = (
                    f"Hello {service_log.customer_name or ''},\n\n"
                    f"Your complaint '{complaint_desc or '-'}' (Ticket: {service_log.ticket_number or '-'}) has been completed on {completed_time_str}.\n"
                    f"If you have any further issues, please contact us.\n\n"
                    f"Thank you,\nIMC Business Solutions"
                )
                try:
                    send_whatsapp_message_for_service_log(customer_phone, requests.utils.quote(msg_customer))
                except Exception as e:
                    print(f"Error sending WhatsApp to customer: {e}")

        # return timestamps in ISO format (same as earlier behaviour)
        return JsonResponse({
            'success': True,
            'started_time': complaint_log.started_time.isoformat() if complaint_log.started_time else None,
            'completed_time': complaint_log.completed_time.isoformat() if complaint_log.completed_time else None,
        })

    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
    
@login_required
def reassign_work(request, log_id):
    service_log = get_object_or_404(ServiceLog, id=log_id)
    users = User.objects.filter(status='active').order_by('name')
    complaints = service_log.servicelogcomplaint_set.all()
    
    if request.method == 'POST':
        # Handle individual complaint reassignments
        for complaint_log in complaints:
            assigned_person_id = request.POST.get(f'assigned_person_{complaint_log.id}')
            if assigned_person_id:
                assigned_person = get_object_or_404(User, id=assigned_person_id)
                complaint_log.assigned_person = assigned_person
                complaint_log.assigned_date = timezone.now()  # Update assignment date
                complaint_log.status = 'Pending'  # Reset status to Pending
                complaint_log.completed_date = None  # Clear completed date
                
                # Send WhatsApp message to the assigned user
                message = (
                    f"Dear {assigned_person.name},\n\n"
                    f"You have been reassigned a service log.\n"
                    f"Ticket Number: {service_log.ticket_number}\n"
                    f"Customer Name: {service_log.customer_name}\n"
                    f"Complaint: {complaint_log.complaint.description}\n"
                    f"Please check the details and take necessary action.\n"
                    f"Best regards,\n"
                    f"IMC Business Solutions"
                )
                send_whatsapp_message_for_service_log(assigned_person.phone_number, message)
        
        messages.success(request, "Complaints reassigned successfully")
        return redirect('my_assigned_service_logs')
    
    return render(request, 'reassign_work.html', {
        'service_log': service_log,
        'users': users,
        'complaints': complaints,
    })

@csrf_exempt
@require_POST
def reassign_complaint(request):
    """Reassign a complaint from current user to another user"""
    data = json.loads(request.body)
    complaint_log_id = data.get('complaint_log_id')
    user_id = data.get('user_id')
    reason = data.get('reason', '')

    try:
        # Get the current user
        current_user = User.objects.get(userid=request.user.username)
        
        # Get the complaint log
        complaint_log = ServiceLogComplaint.objects.get(id=complaint_log_id)
        
        # Verify that the current user is the one assigned to this complaint
        if complaint_log.assigned_person != current_user:
            return JsonResponse({
                'success': False, 
                'error': 'You can only reassign complaints assigned to you'
            })
        
        # Get the new user to assign to
        new_user = User.objects.get(id=user_id)
        
        # Update the complaint log
        complaint_log.assigned_person = new_user
        complaint_log.assigned_date = timezone.now()  # Update assignment date
        complaint_log.status = 'Pending'  # Reset status to Pending
        complaint_log.completed_date = None  # Clear completed date
        
        # Add reassignment reason to note if provided
        if reason:
            original_note = complaint_log.note or ''
            reassignment_note = f"\n[Reassigned from {current_user.name} to {new_user.name}]\nReason: {reason}"
            complaint_log.note = original_note + reassignment_note
        
        complaint_log.save()
        
        # Send WhatsApp message to the new assigned user
        service_log = complaint_log.service_log
        message = (
            f"Dear {new_user.name},\n\n"
            f"You have been reassigned a service log.\n"
            f"Ticket Number: {service_log.ticket_number}\n"
            f"Customer Name: {service_log.customer_name}\n"
            f"Complaint: {complaint_log.complaint.description}\n"
            f"Please review the details and take the necessary actions.\n"
            f"Thank you for your prompt attention to this matter.\n"
            f"Best regards,\n"
            f"IMC Business Solutions"
        )
        send_whatsapp_message_for_service_log(new_user.phone_number, message)
        
        return JsonResponse({
            'success': True,
            'message': f'Complaint successfully reassigned to {new_user.name}'
        })
        
    except ServiceLogComplaint.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Complaint log not found'})
    except User.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'User not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})



from django.shortcuts import render
from django.http import JsonResponse
from django.utils import timezone
from datetime import datetime, timedelta
from .models import LeaveRequest, LateRequest, EarlyRequest, Employee

def all_requests_summary(request):
    # Get current month and year
    now = timezone.now()
    current_year = now.year
    current_month = now.month
    
    # Get selected month from request
    selected_month = request.GET.get('month')
    if selected_month:
        try:
            selected_date = datetime.strptime(selected_month, '%Y-%m')
            current_year = selected_date.year
            current_month = selected_date.month
        except ValueError:
            pass
    
    # Get all employees
    employees = Employee.objects.filter(status='active').order_by('name')
    
    # Prepare data for each employee
    employee_requests = []
    
    for employee in employees:
        # Get leave requests for the month
        leave_requests = LeaveRequest.objects.filter(
            employee=employee,
            start_date__year=current_year,
            start_date__month=current_month
        ).order_by('start_date')
        
        # Get late requests for the month
        late_requests = LateRequest.objects.filter(
            employee=employee,
            date__year=current_year,
            date__month=current_month
        ).order_by('date')
        
        # Get early requests for the month
        early_requests = EarlyRequest.objects.filter(
            employee=employee,
            date__year=current_year,
            date__month=current_month
        ).order_by('date')
        
        # Count total requests
        total_requests = leave_requests.count() + late_requests.count() + early_requests.count()
        
        employee_data = {
            'employee': employee,
            'leave_requests': leave_requests,
            'late_requests': late_requests,
            'early_requests': early_requests,
            'total_requests': total_requests,
            'leave_count': leave_requests.count(),
            'late_count': late_requests.count(),
            'early_count': early_requests.count(),
        }
        
        employee_requests.append(employee_data)
    
    context = {
        'employee_requests': employee_requests,
        'current_year': current_year,
        'current_month': current_month,
        'selected_month': f"{current_year}-{str(current_month).zfill(2)}",
    }
    
    return render(request, 'all_requests.html', context)

def get_employee_requests_details(request, employee_id):
    """API endpoint to get detailed requests for a specific employee"""
    if request.method == 'GET':
        # Get current month and year
        now = timezone.now()
        current_year = now.year
        current_month = now.month
        
        # Get selected month from request
        selected_month = request.GET.get('month')
        if selected_month:
            try:
                selected_date = datetime.strptime(selected_month, '%Y-%m')
                current_year = selected_date.year
                current_month = selected_date.month
            except ValueError:
                pass
        
        try:
            employee = Employee.objects.get(id=employee_id)
            
            # Get all requests for the employee in the selected month
            leave_requests = LeaveRequest.objects.filter(
                employee=employee,
                start_date__year=current_year,
                start_date__month=current_month
            ).order_by('start_date')
            
            late_requests = LateRequest.objects.filter(
                employee=employee,
                date__year=current_year,
                date__month=current_month
            ).order_by('date')
            
            early_requests = EarlyRequest.objects.filter(
                employee=employee,
                date__year=current_year,
                date__month=current_month
            ).order_by('date')
            
            # Prepare response data
            data = {
                'success': True,
                'employee_name': employee.name,
                'leave_requests': [
                    {
                        'type': 'Leave',
                        'start_date': req.start_date.strftime('%d-%m-%Y'),
                        'end_date': req.end_date.strftime('%d-%m-%Y'),
                        'reason': req.reason,
                        'note': req.note,   
                        'leave_type': req.get_leave_type_display(),
                        'status': req.status,
                        'created_at': req.created_at.strftime('%d-%m-%Y %H:%M'),
                    }
                    for req in leave_requests
                ],
                'late_requests': [
                    {
                        'type': 'Late',
                        'date': req.date.strftime('%d-%m-%Y'),
                        'delay_time': req.delay_time,
                        'reason': req.reason,
                        'status': req.status,
                        'created_at': req.created_at.strftime('%d-%m-%Y %H:%M'),
                    }
                    for req in late_requests
                ],
                'early_requests': [
                    {
                        'type': 'Early',
                        'date': req.date.strftime('%d-%m-%Y'),
                        'early_time': req.early_time.strftime('%H:%M'),
                        'reason': req.reason,
                        'status': req.status,
                        'created_at': req.created_at.strftime('%d-%m-%Y %H:%M'),
                    }
                    for req in early_requests
                ],
            }
            
            return JsonResponse(data)
            
        except Employee.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Employee not found'})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

  