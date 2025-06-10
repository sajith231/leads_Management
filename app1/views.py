from django.shortcuts import render, redirect, get_object_or_404
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

    return render(request, "add_user.html", {"form": form})

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
@login_required
def edit_user(request, user_id):
    user = get_object_or_404(User, id=user_id)

    if request.method == "POST":
        form = UserForm(request.POST, request.FILES, instance=user, edit_mode=True)
        if form.is_valid():
            user = form.save(commit=False)

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

    return render(request, "edit_user.html", {"form": form, "user": user})


from django.db.models import Prefetch

@login_required
def user_dashboard(request):
    # Get the custom user ID from session
    custom_user_id = request.session.get('custom_user_id')
    
    # Fetch only leads for the logged-in user with related data
    leads = Lead.objects.filter(
        user_id=custom_user_id
    ).prefetch_related(
        'requirements',
        'requirement_amounts',
        'requirement_amounts__requirement'
    ).order_by('-created_at')
    username = f" {request.user.username}" if request.user.is_authenticated else ""
    context = {
        'leads': leads,
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
            return redirect('all_leads')  # Redirect super admin to a different page
    else:
        try:
            current_user = User.objects.get(id=request.session['custom_user_id'])
        except User.DoesNotExist:
            messages.error(request, "User session is invalid.")
            return redirect('logout')

    # Handle POST requests
    if request.method == 'POST':
        form = LeadForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                lead = form.save(commit=False)
                lead.user = current_user

                # Get location data from the request
                location_data = request.POST.get('location_data', '')
                if location_data:
                    try:
                        location = json.loads(location_data)
                        lead.added_latitude = location.get('latitude')
                        lead.added_longitude = location.get('longitude')
                    except json.JSONDecodeError:
                        messages.warning(request, 'Invalid location data format.')

                lead.save()
                form.save_m2m()  # Save Many-to-Many relationships

                # Save requirement amounts and remarks
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

                # Save custom hardware prices
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

                messages.success(request, 'Lead added successfully!')

                # Redirect based on user type
                if request.user.is_superuser:  # Redirect super admin
                    return redirect('all_leads')
                elif current_user.user_level == 'normal':  # Redirect admin (normal user)
                    return redirect('all_leads')
                else:  # Redirect all other users
                    return redirect('user_dashboard')

            except Exception as e:
                messages.error(request, f"Error saving lead: {str(e)}")
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = LeadForm()
        form.fields['location'].queryset = Location.objects.all()

    # Fetch all requirements and hardware for the form
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
    # Fetch the lead or return 404 if it does not exist
    lead = get_object_or_404(Lead, id=lead_id)

    if request.method == 'POST':
        form = LeadForm(request.POST, request.FILES, instance=lead)
        if form.is_valid():
            lead = form.save()  # Save the form instance

            try:
                # Handle hardware prices
                hardware_prices_data = request.POST.get('hardware_prices_data', '{}')
                hardware_prices = json.loads(hardware_prices_data)

                # First, delete all existing hardware prices for this lead
                LeadHardwarePrice.objects.filter(lead=lead).delete()

                # Then create new entries only for the selected hardware
                for hardware_id, custom_price in hardware_prices.items():
                    try:
                        hardware = Hardware.objects.get(id=int(hardware_id))
                        LeadHardwarePrice.objects.create(
                            lead=lead,
                            hardware=hardware,
                            custom_price=float(custom_price)
                        )
                    except Hardware.DoesNotExist:
                        messages.warning(request, f"Hardware with ID {hardware_id} not found.")
                    except ValueError:
                        messages.warning(request, f"Invalid price value for hardware ID {hardware_id}.")

                # Handle requirements
                amounts_data = request.POST.get('requirement_amounts_data', '{}')
                remarks_data = request.POST.get('requirement_remarks_data', '{}')

                amounts = json.loads(amounts_data)
                remarks = json.loads(remarks_data)

                # Clear existing requirement amounts
                LeadRequirementAmount.objects.filter(lead=lead).delete()

                # Create new requirement amounts
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

    # Get existing hardware prices
    existing_hardware_prices = {
        hp.hardware.id: hp.custom_price
        for hp in LeadHardwarePrice.objects.filter(lead=lead)
    }

    # Get existing requirement amounts
    existing_amounts = {
        ra.requirement_id: ra.amount
        for ra in LeadRequirementAmount.objects.filter(lead=lead)
    }

    return render(request, 'edit_lead.html', {
        'form': form,
        'lead': lead,
        'requirements': requirements,
        'hardwares': hardwares,
        'existing_hardware_prices': existing_hardware_prices,
        'existing_amounts': existing_amounts,
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








from .models import Complaint
from .forms import ComplaintForm

@login_required
def add_complaint(request):
    if request.method == 'POST':
        form = ComplaintForm(request.POST)
        if form.is_valid():
            complaint = form.save(commit=False)
            # Get the custom User instance from session or however you store it
            # Option 1: If you store user_id in session
            if 'user_id' in request.session:
                try:
                    custom_user = User.objects.get(id=request.session['user_id'])
                    complaint.created_by = custom_user
                except User.DoesNotExist:
                    complaint.created_by = None
            else:
                complaint.created_by = None
            complaint.save()
            return redirect('all_complaints')
    else:
        form = ComplaintForm()
    return render(request, 'add_complaints.html', {'form': form})


from django.core.paginator import Paginator
from django.shortcuts import render
from .models import Complaint


from django.core.paginator import Paginator

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import render
from .models import Complaint

@login_required
def all_complaints(request):
    selected_type = request.GET.get('type', 'all')
    
    if selected_type == 'all':
        complaints = Complaint.objects.all().order_by('description')  # Alphabetic order
    else:
        complaints = Complaint.objects.filter(complaint_type=selected_type).order_by('description')  # Alphabetic order
    
    paginator = Paginator(complaints, 10)  # Show 10 complaints per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Calculate start index for pagination
    start_index = (page_obj.number - 1) * paginator.per_page
    
    context = {
        'page_obj': page_obj,
        'selected_type': selected_type,
        'start_index': start_index,
    }
    return render(request, 'all_complaints.html', context)


# Edit complaint view
def edit_complaint(request, complaint_id):
    complaint = get_object_or_404(Complaint, id=complaint_id)
    if request.method == 'POST':
        form = ComplaintForm(request.POST, instance=complaint)
        if form.is_valid():
            form.save()
            return redirect('all_complaints')
    else:
        form = ComplaintForm(instance=complaint)
    return render(request, 'edit_complaint.html', {'form': form})

# Delete complaint view
def delete_complaint(request, complaint_id):
    complaint = get_object_or_404(Complaint, id=complaint_id)
    complaint.delete()
    return redirect('all_complaints')




from django.http import JsonResponse
from .models import User, ServiceLog

@login_required
def assign_user(request, log_id):
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        assigned_date = request.POST.get('assigned_date')
        try:
            service_log = ServiceLog.objects.get(id=log_id)
            assigned_user = User.objects.get(id=user_id)
            service_log.assigned_person = assigned_user
            service_log.assigned_date = assigned_date
            service_log.save()
            return JsonResponse({
                'success': True,
                'assigned_person': assigned_user.name,
                'assigned_date': assigned_date
            })
        except (ServiceLog.DoesNotExist, User.DoesNotExist):
            return JsonResponse({'success': False}, status=400)
    return JsonResponse({'success': False}, status=405)




from django.core.paginator import Paginator
from django.db.models import Q
from datetime import datetime

@login_required
def service_log(request):
    try:
        current_user = get_current_user(request)
        allowed_menus = request.session.get('allowed_menus', [])

        if (request.user.is_superuser or 
            current_user.user_level == 'admin_level' or 
            'service_log' in allowed_menus):

            logs = ServiceLog.objects.select_related(
                'added_by', 
                'complaint', 
                'assigned_person'
            ).all()

            # Get filter parameters
            status_filter = request.GET.get('status', 'Not Completed')
            user_filter = request.GET.get('user')
            assigned_user_filter = request.GET.get('assigned_user')
            start_date = request.GET.get('start_date')
            end_date = request.GET.get('end_date')

            # Apply filters
            if status_filter and status_filter != 'all':
                logs = logs.filter(status=status_filter)
            
            if user_filter:
                logs = logs.filter(added_by_id=user_filter)
            
            if assigned_user_filter and assigned_user_filter != 'all':
                logs = logs.filter(assigned_person_id=assigned_user_filter)
            
            if start_date and end_date:
                try:
                    start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
                    end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
                    logs = logs.filter(assigned_date__range=[start_date_obj, end_date_obj])
                except ValueError:
                    pass  # Invalid date format, ignore filter

            paginator = Paginator(logs, 15)  # Show 15 logs per page
            page_number = request.GET.get('page')
            page_obj = paginator.get_page(page_number)

            # Calculate start index for continuous numbering
            start_index = (page_obj.number - 1) * paginator.per_page + 1

            all_users = User.objects.all()

            # Create filter parameters string for pagination
            filter_params = []
            if status_filter:
                filter_params.append(f'status={status_filter}')
            if user_filter:
                filter_params.append(f'user={user_filter}')
            if assigned_user_filter:
                filter_params.append(f'assigned_user={assigned_user_filter}')
            if start_date:
                filter_params.append(f'start_date={start_date}')
            if end_date:
                filter_params.append(f'end_date={end_date}')
            
            filter_query_string = '&'.join(filter_params)

            return render(request, 'service_log.html', {
                'logs': page_obj,
                'all_users': all_users,
                'current_user': current_user,
                'filter_query_string': filter_query_string,
                'start_index': start_index,
                'current_filters': {
                    'status': status_filter,
                    'user': user_filter,
                    'assigned_user': assigned_user_filter,
                    'start_date': start_date,
                    'end_date': end_date,
                }
            })
        else:
            return redirect('user_service_log')

    except Exception as e:
        messages.error(request, f'Error accessing service logs: {str(e)}')
        return redirect('login')



from django.shortcuts import render, get_object_or_404, redirect
from .models import ServiceLog
from django.core.exceptions import ValidationError

@login_required
def edit_service_log(request, log_id):
    log = get_object_or_404(ServiceLog, id=log_id)
    complaints = Complaint.objects.all()  # Fetch all complaints

    if request.method == 'POST':
        # Get the updated data from the request
        customer_name = request.POST.get('customer_name')
        log_type = request.POST.get('type')
        complaint_id = request.POST.get('complaint')
        remark = request.POST.get('remark')
        voice_note = request.FILES.get('voice_note')

        # Fetch the complaint instance if it exists
        complaint = None
        if complaint_id:
            complaint = Complaint.objects.filter(id=complaint_id).first()

        try:
            # Manually update the ServiceLog instance
            log.customer_name = customer_name
            log.type = log_type
            log.complaint = complaint
            log.remark = remark

            # If a new voice note is uploaded, save it
            if voice_note:
                log.voice_note = voice_note

            # Save the updated log
            log.save()

            return redirect('service_log')  # Redirect to the service log list view (not 'service_log_list')

        except Exception as e:
            return render(request, 'edit_service_log.html', {'log': log, 'complaints': complaints, 'error': str(e)})

    return render(request, 'edit_service_log.html', {'log': log, 'complaints': complaints})

def delete_service_log(request, log_id):
    log = get_object_or_404(ServiceLog, id=log_id)
    log.delete()
    return redirect('service_log')  # This redirects to the service_log_list view




@login_required
def user_service_log(request):
    # Redirect admin users to the admin service log view
    if request.user.is_superuser:
        return redirect('service_log')
    
    # Get the current user
    current_user = User.objects.get(id=request.session['custom_user_id'])
    
    # Get all service logs, not just the current user's
    logs = ServiceLog.objects.select_related(
        'added_by', 
        'complaint', 
        'assigned_person'
    ).all()
    all_users = User.objects.all()
    
    return render(request, 'user_service_log.html', {
        'logs': logs,
        'current_user': current_user,  # Pass the current user to the template
        'all_users': all_users
    })



@login_required
@require_POST
def toggle_service_status(request, log_id):
    try:
        log = ServiceLog.objects.get(id=log_id)
        # Toggle the status
        log.status = 'Completed' if log.status == 'Not Completed' else 'Not Completed'
        log.save()
        return JsonResponse({
            'success': True,
            'status': log.status
        })
    except ServiceLog.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Log not found'
        }, status=404)


@require_POST
def save_assigned_date(request, log_id):
    try:
        data = json.loads(request.body)
        log = ServiceLog.objects.get(id=log_id)
        log.assigned_date = data['assigned_date']
        log.save()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})
    


from .models import ServiceLog

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

def get_customers(request):
    response = requests.get("https://rrc.imcbs.com/api/rrc-clients-data")
    return JsonResponse(response.json(), safe=False)

@login_required
def add_service_log(request):
    try:
        current_user = get_current_user(request)
        complaints = Complaint.objects.all()

        if request.method == 'POST':
            customer_name = request.POST.get('customer_name')
            type = request.POST.get('type')
            complaint_id = request.POST.get('complaint')
            remark = request.POST.get('remark')
            voice_note = request.FILES.get('voice_note')

            complaint = Complaint.objects.get(id=complaint_id) if complaint_id else None

            service_log = ServiceLog(
                customer_name=customer_name,  # This will store the selected customer name
                type=type,
                complaint=complaint,
                remark=remark,
                voice_note=voice_note,
                added_by=current_user
            )
            service_log.save()
            
            messages.success(request, 'Service log added successfully!')
            
            if current_user.user_level == 'admin_level' or request.user.is_superuser:
                return redirect('service_log')
            else:
                return redirect('user_service_log')
                
        return render(request, 'add_service.html', {'complaints': complaints})
        
    except Exception as e:
        messages.error(request, f'Error adding service log: {str(e)}')
        return redirect('service_log')
    


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
            response = requests.get('https://rrc.imcbs.com/api/rrc-clients-data')
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
        response = requests.get('https://rrc.imcbs.com/api/rrc-clients-data')
        if response.status_code == 200:
            customers = response.json()
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
        response = requests.get('https://rrc.imcbs.com/api/rrc-clients-data')
        if response.status_code == 200:
            customers = response.json()
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
from .models import CV, Rating, InterviewTakenBy
import json
import base64
import tempfile
from django.core.files import File
import os
from django.utils import timezone

@csrf_exempt
def save_ratings(request, cv_id):
    if request.method == 'POST':
        try:
            cv = CV.objects.get(id=cv_id)
        except CV.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'CV not found'})

        data = request.POST

        # Process voice note if present
        voice_note_data = data.get('voice_note')
        temp_file_path = None
        if voice_note_data and voice_note_data.startswith('data:audio/wav;base64,'):
            format, base64_str = voice_note_data.split(',', 1)

            try:
                # Decode base64 to binary
                voice_note_binary = base64.b64decode(base64_str)
                
                # Create temporary file
                with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                    temp_file.write(voice_note_binary)
                    temp_file_path = temp_file.name
            except Exception as e:
                return JsonResponse({'success': False, 'error': 'Invalid voice note data'})

        # Create or update rating
        rating, created = Rating.objects.get_or_create(cv=cv)
        rating.knowledge = data.get('knowledgeRating')
        rating.confidence = data.get('confidenceRating')
        rating.attitude = data.get('attitudeRating')
        rating.communication = data.get('communicationRating')
        rating.appearance = data.get('appearanceRating')
        rating.languages = request.POST.getlist('languages[]')
        rating.expected_salary = data.get('expectedSalary') or None
        rating.experience = data.get('experience') or None
        rating.remark = data.get('remark') or None

        # Save voice note if present
        if temp_file_path:
            with open(temp_file_path, 'rb') as temp_file:
                file_name = f'voice_note_{cv_id}_{timezone.now().strftime("%Y%m%d_%H%M%S")}.wav'
                rating.voice_note.save(file_name, File(temp_file), save=False)
            os.unlink(temp_file_path)

        rating.save()

        # Create an entry in InterviewTakenBy model
        InterviewTakenBy.objects.create(cv=cv, created_by=request.user)

        return JsonResponse({'success': True})
    
    return JsonResponse({'success': False})


@csrf_exempt
def get_ratings(request, cv_id):
    if request.method == 'GET':
        try:
            cv = CV.objects.get(id=cv_id)
        except CV.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'CV not found'})

        rating = Rating.objects.filter(cv=cv).first()
        if rating:
            response_data = {
                'success': True,
                'knowledge': rating.knowledge,
                'confidence': rating.confidence,
                'attitude': rating.attitude,
                'communication': rating.communication,
                'appearance': rating.appearance,
                'languages': rating.languages,
                'expected_salary': rating.expected_salary,
                'experience': rating.experience,
                'remark': rating.remark,
            }
            if rating.voice_note:
                response_data['voice_note_url'] = rating.voice_note.url
            return JsonResponse(response_data)
        
        return JsonResponse({'success': False, 'error': 'No rating found'})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})


from django.http import JsonResponse
from .models import InterviewTakenBy

def get_interview_taken_by(request, cv_id):
    try:
        interview_taken_by = InterviewTakenBy.objects.filter(cv_id=cv_id).latest('created_at')
        return JsonResponse({
            'success': True,
            'username': interview_taken_by.created_by.username
        })
    except InterviewTakenBy.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'No interview taken by information found'
        })



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




from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from .models import Employee

def save_experience_certificate_details(request, employee_id):
    if request.method == "POST":
        employee = get_object_or_404(Employee, id=employee_id)
        start_date = request.POST.get("start_date")
        end_date = request.POST.get("end_date")

        # Save data to the employee model
        employee.experience_start_date = start_date
        employee.experience_end_date = end_date
        employee.save()

        return JsonResponse({
            "success": True,
            "employee": {
                "name": employee.name,
                "address": employee.address,
                "phone_personal": employee.phone_personal,
                "phone_residential": employee.phone_residential,
                "job_title": employee.job_title,
                "joining_date": employee.joining_date.strftime("%Y-%m-%d"),
                "dob": employee.dob.strftime("%Y-%m-%d"),
                "experience_start_date": employee.experience_start_date,
                "experience_end_date": employee.experience_end_date,
            }
        })

    return JsonResponse({"success": False, "error": "Invalid request"})


def experience_certificate(request, employee_id):
    employee = get_object_or_404(Employee, id=employee_id)
    clicked_date = request.GET.get("date", employee.joining_date.strftime("%d/%m/%Y"))

    context = {
        'employee': employee,
        'clicked_date': clicked_date,
    }
    return render(request, 'experience_certificate.html', context)







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
    


from django.core.paginator import Paginator
from django.shortcuts import render
from .models import CV

@login_required
def interview_management(request):
    cv_list = CV.objects.filter(interview_status=True).order_by('-interview_date', '-created_date')  
    # Ordering by interview_date first, then by created_date (latest first)

    paginator = Paginator(cv_list, 10)  # Show 10 CVs per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'interview_management.html', {'cv_list': page_obj})




from .models import CV

from django.core.paginator import Paginator
from django.shortcuts import render
from .models import CV

@login_required
def make_offer_letter(request):
    cv_list = CV.objects.filter(selected=True).order_by('-interview_date')

    paginator = Paginator(cv_list, 10)  # Show 10 CVs per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'make_offer_letter.html', {'cv_list': page_obj})






from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from .forms import CVSelectionForm
from .models import CV

@login_required
def toggle_selection_status(request):
    if request.method == 'POST':
        form = CVSelectionForm(request.POST)
        if form.is_valid():
            cv_id = form.cleaned_data['cv_id']
            selected = form.cleaned_data['selected']
            cv = get_object_or_404(CV, id=cv_id)
            cv.selected = selected
            cv.save()
            messages.success(request, f'Status updated for {cv.name}.')
        else:
            messages.error(request, 'Invalid form submission.')
    return redirect('interview_management')  # Redirect back to the interview management page


from django.core.paginator import Paginator
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import Employee

def make_experience_certificate(request):
    search_query = request.GET.get('q', '')
    employees = Employee.objects.all().order_by('name')

    if search_query:
        employees = employees.filter(name__icontains=search_query)

    paginator = Paginator(employees, 15)  # 15 per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'make_experience_certificate.html', {
        'page_obj': page_obj,
        'search_query': search_query
    })




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


@login_required
def attendance_user(request):
    return render(request, 'attendance_user.html')


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
            end_date = datetime.strptime(data['end_date'], '%Y-%m-%d').date()

            leave_request = LeaveRequest.objects.create(
                employee=employee,
                start_date=start_date,
                end_date=end_date,
                leave_type=data['leave_type'],
                reason=data['reason'],
                status='pending'
            )

            
            # List of phone numbers to send the WhatsApp message
            phone_numbers = ["9946545535", "7593820007", "7593820005","9846754998"]
            
            formatted_start = start_date.strftime('%d %m %Y')
            formatted_end = end_date.strftime('%d %m %Y')

            message = (
                f"New leave request from {employee.name}. "
                f"Type: {leave_request.get_leave_type_display()}, "
                f"Start Date: {formatted_start}, End Date: {formatted_end}, "
                f"Reason: {data['reason']}"
            )
            
            # Send WhatsApp message to each phone number
            for number in phone_numbers:
                send_whatsapp_message_new_request(number, message)
            
            return JsonResponse({'success': True, 'message': 'Leave request submitted successfully'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

def send_whatsapp_message_new_request(phone_number, message):
    secret = "7b8ae820ecb39f8d173d57b51e1fce4c023e359e"
    account = "1748250982812b4ba287f5ee0bc9d43bbf5bbe87fb683431662a427"
    
    url = f"https://app.dxing.in/api/send/whatsapp?secret={secret}&account={account}&recipient={phone_number}&type=text&message={message}&priority=1"
    
    response = requests.get(url)
    
    if response.status_code == 200:
        print(f"WhatsApp message sent successfully to {phone_number}")
    else:
        print(f"Failed to send WhatsApp message to {phone_number}. Status code: {response.status_code}, Response: {response.text}")

@login_required
def get_leave_requests(request):
    status_filter = request.GET.get('status', None)
    
    if request.user.is_superuser or request.session.get('user_level') == 'normal':
        leave_requests = LeaveRequest.objects.all().select_related('employee').order_by('-created_at')
        if status_filter:
            leave_requests = leave_requests.filter(status=status_filter)
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
        'status': req.status,
        'processed_by': req.processed_by.username if req.processed_by else None,
        'processed_at': req.processed_at.strftime('%Y-%m-%d %H:%M') if req.processed_at else None,
        'created_at': req.created_at.strftime('%d-%m-%Y')
    } for req in leave_requests]
    
    return JsonResponse({'leave_requests': data})

@login_required
def process_leave_request(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            leave_request = LeaveRequest.objects.get(id=data['request_id'])

            if data['action'] == 'approve':
                # Remove old rejected leave marks if any
                if leave_request.status == 'rejected':
                    current_date = leave_request.start_date
                    while current_date <= leave_request.end_date:
                        Attendance.objects.filter(
                            employee=leave_request.employee,
                            date=current_date,
                            status='leave'
                        ).delete()
                        current_date += timedelta(days=1)

                # Approve and add leave attendance
                leave_request.status = 'approved'
                current_date = leave_request.start_date
                while current_date <= leave_request.end_date:
                    attendance, created = Attendance.objects.get_or_create(
                        employee=leave_request.employee,
                        date=current_date,
                        defaults={
                            'day': current_date.day,
                            'status': 'leave' if leave_request.leave_type == 'full_day' else 'half'
                        }
                    )
                    if not created:
                        attendance.status = 'leave' if leave_request.leave_type == 'full_day' else 'half'
                        attendance.save()
                    current_date += timedelta(days=1)

            else:
                # Reject and delete leave attendance
                leave_request.status = 'rejected'
                current_date = leave_request.start_date
                while current_date <= leave_request.end_date:
                    Attendance.objects.filter(
                        employee=leave_request.employee,
                        date=current_date,
                        status='leave'
                    ).delete()
                    current_date += timedelta(days=1)

            leave_request.processed_by = request.user
            leave_request.processed_at = timezone.now()
            leave_request.save()

            # Send WhatsApp message with leave request details
            send_whatsapp_message_status_update(leave_request, data['action'])

            return JsonResponse({
                'success': True,
                'employee_id': leave_request.employee.id,
                'start_date': leave_request.start_date.strftime('%d %m %Y'),
                'end_date': leave_request.end_date.strftime('%d %m %Y'),
                'action': data['action'],
                'leave_type': leave_request.leave_type
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

    return JsonResponse({'success': False, 'error': 'Invalid request method'})

def send_whatsapp_message_status_update(leave_request, action):
    """Send WhatsApp message with detailed leave request information"""
    secret = "7b8ae820ecb39f8d173d57b51e1fce4c023e359e"
    account = "1748250982812b4ba287f5ee0bc9d43bbf5bbe87fb683431662a427"

    # Format the message with leave request details based on action
    if action == 'approve':
        message = f"Your leave request has been approved. Start Date: {leave_request.start_date.strftime('%d-%m-%Y')}, End Date: {leave_request.end_date.strftime('%d-%m-%Y')}, Reason: {leave_request.reason}"
    elif action == 'reject':
        message = f"Your leave request has been rejected. Start Date: {leave_request.start_date.strftime('%d-%m-%Y')}, End Date: {leave_request.end_date.strftime('%d-%m-%Y')}, Reason: {leave_request.reason}"
    else:
        # This replaces the generic "Your leave request status has been updated." message
        message = f"Leave request status updated. Start Date: {leave_request.start_date.strftime('%d-%m-%Y')}, End Date: {leave_request.end_date.strftime('%d-%m-%Y')}, Reason: {leave_request.reason}, Status: {leave_request.status}"

    phone_number = leave_request.employee.phone_personal

    # Construct API URL
    url = (
        f"https://app.dxing.in/api/send/whatsapp?"
        f"secret={secret}&account={account}"
        f"&recipient={phone_number}"
        f"&type=text&message={message}&priority=1"
    )

    response = requests.get(url)

    if response.status_code == 200:
        print(f"WhatsApp message sent successfully to {phone_number}")
    else:
        print(f"Failed to send WhatsApp message to {phone_number}. Status code: {response.status_code}, Response: {response.text}")




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
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            employee = Employee.objects.get(user_id=request.session.get('custom_user_id'))
            
            # Convert date string to datetime object
            date_str = data['date']
            date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
            
            late_request = LateRequest.objects.create(
                employee=employee,
                date=date_obj,
                delay_time=data['delay_time'],  # New field
                reason=data['reason'],
                status='pending'
            )
            
            # Send WhatsApp message to managers
            phone_numbers = ["9946545535", "7593820007", "7593820005","9846754998"]
            message = (
                f"New late request from {employee.name}. "
                f"Date: {date_obj.strftime('%d-%m-%Y')}, "
                f"Delay Time: {late_request.delay_time}, "
                f"Reason: {late_request.reason}"
            )
            
            for number in phone_numbers:
                send_whatsapp_message(number, message)
            
            return JsonResponse({'success': True, 'message': 'Late request submitted successfully'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

def send_whatsapp_message(phone_number, message):
    secret = "7b8ae820ecb39f8d173d57b51e1fce4c023e359e"
    account = "1748250982812b4ba287f5ee0bc9d43bbf5bbe87fb683431662a427"
    
    url = f"https://app.dxing.in/api/send/whatsapp?secret={secret}&account={account}&recipient={phone_number}&type=text&message={message}&priority=1"
    
    response = requests.get(url)
    
    if response.status_code == 200:
        print(f"WhatsApp message sent successfully to {phone_number}")
    else:
        print(f"Failed to send WhatsApp message to {phone_number}. Status code: {response.status_code}, Response: {response.text}")
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

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

@login_required
def process_late_request(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            late_request = LateRequest.objects.get(id=data['request_id'])
            
            if data['action'] == 'approve':
                late_request.status = 'approved'
                message = (
                    f"Your late request for {late_request.date.strftime('%d-%m-%Y')} has been approved. "
                    f"Delay Time: {late_request.delay_time}, Reason: {late_request.reason}"
                )
            else:
                late_request.status = 'rejected'
                message = (
                    f"Your late request for {late_request.date.strftime('%d-%m-%Y')} has been rejected. "
                    f"Delay Time: {late_request.delay_time}, Reason: {late_request.reason}"
                )
            
            late_request.processed_by = request.user
            late_request.processed_at = timezone.now()
            late_request.save()
            
            # Send WhatsApp message to the employee
            send_whatsapp_message(late_request.employee.phone_personal, message)
            
            return JsonResponse({
                'success': True,
                'employee_id': late_request.employee.id,
                'date': late_request.date.strftime('%Y-%m-%d'),
                'action': data['action']
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

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

def attendance_summary(request, employee_id):
    employee = get_object_or_404(Employee, id=employee_id)
    now = timezone.now()
    year = request.GET.get('year', now.year)
    month = request.GET.get('month', now.month)

    try:
        year = int(year)
        month = int(month)
    except (ValueError, TypeError):
        year = now.year
        month = now.month

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
                {'id': 'reminders', 'name': 'Reminders', 'icon': 'fas fa-bell'}
            ]
        },
        # Update the HR menu section in both views to:
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
                {'id': 'service_log', 'name': 'Service Log (Admin Dashboard)', 'icon': 'fas fa-book'},
                {'id': 'service_entry', 'name': 'Service Entry (Admin Dashboard)', 'icon': 'fas fa-plus-circle'},
                {'id': 'user_service_log', 'name': 'Service Log(User Dashboard)', 'icon': 'fas fa-book'},
                {'id': 'user_service_entry', 'name': 'Service Entry(User Dashboard)', 'icon': 'fas fa-plus-circle'}
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
            'name': 'Master',
            'icon': 'fas fa-cog',
            'submenus': [
                {'id': 'all_districts', 'name': 'District', 'icon': 'fas fa-map'},
                {'id': 'all_areas', 'name': 'Area', 'icon': 'fas fa-map-marker-alt'},
                {'id': 'all_locations', 'name': 'Location', 'icon': 'fas fa-chart-area'},
                {'id': 'all_requirements', 'name': 'Requirements', 'icon': 'fas fa-tasks'},
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
    'name': 'PLANET',
    'icon': 'fas fa-globe',
    'submenus': [
        {'id': 'show_clients', 'name': 'Clients', 'icon': 'fas fa-users'}
    ]
}

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
                {'id': 'service_log', 'name': 'Service Log (Admin Dashboard)', 'icon': 'fas fa-book'},
                {'id': 'service_entry', 'name': 'Service Entry (Admin Dashboard)', 'icon': 'fas fa-plus-circle'},
                {'id': 'user_service_log', 'name': 'Service Log(User Dashboard)', 'icon': 'fas fa-book'},
                {'id': 'user_service_entry', 'name': 'Service Entry(User Dashboard)', 'icon': 'fas fa-plus-circle'}
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
        }
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
@login_required
def create_early_request(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            employee = Employee.objects.get(user_id=request.session.get('custom_user_id'))
            
            early_request = EarlyRequest.objects.create(
                employee=employee,
                date=data['date'],
                early_time=data['early_time'],
                reason=data['reason'],
                status='pending'
            )
            
            # Send WhatsApp message to managers
            phone_numbers = ["9946545535", "7593820007", "7593820005","9846754998"]
            message = (
                f"New early request from {employee.name}. "
                f"Date: {data['date']}, "
                f"Early Time: {data['early_time']}, "
                f"Reason: {data['reason']}"
            )
            
            for number in phone_numbers:
                send_whatsapp_message(number, message)
            
            return JsonResponse({'success': True, 'message': 'Early request submitted successfully'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

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


@login_required
def process_early_request(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            early_request_id = data['request_id']
            action = data['action']

            # Fetch the early request
            early_request = EarlyRequest.objects.get(id=early_request_id)

            # Fetch the currently logged-in user
            if not request.user.is_authenticated:
                logger.error("User is not authenticated.")
                return JsonResponse({'success': False, 'error': 'User not authenticated'})

            try:
                processed_by_user = DjangoUser.objects.get(id=request.user.id)
                logger.info(f"User found with ID: {request.user.id}")
            except DjangoUser.DoesNotExist:
                logger.error(f"User not found with ID: {request.user.id}")
                return JsonResponse({'success': False, 'error': 'User not found'})

            # Update the early request status
            if action == 'approve':
                early_request.status = 'approved'
                message = (
                    f"Your early request for {early_request.date.strftime('%d-%m-%Y')} has been approved. "
                    f"Early Time: {early_request.early_time.strftime('%H:%M')}, Reason: {early_request.reason}"
                )
            elif action == 'reject':
                early_request.status = 'rejected'
                message = (
                    f"Your early request for {early_request.date.strftime('%d-%m-%Y')} has been rejected. "
                    f"Early Time: {early_request.early_time.strftime('%H:%M')}, Reason: {early_request.reason}"
                )
            else:
                logger.error(f"Invalid action: {action}")
                return JsonResponse({'success': False, 'error': 'Invalid action'})

            early_request.processed_by = processed_by_user
            early_request.processed_at = timezone.now()
            early_request.save()

            # Send WhatsApp message to the employee
            send_whatsapp_message(early_request.employee.phone_personal, message)

            return JsonResponse({
                'success': True,
                'employee_id': early_request.employee.id,
                'date': early_request.date.strftime('%Y-%m-%d'),
                'action': action
            })
        except EarlyRequest.DoesNotExist:
            logger.error(f"Early request not found with ID: {data['request_id']}")
            return JsonResponse({'success': False, 'error': 'Early request not found'})
        except Exception as e:
            logger.error(f"Error processing early request: {str(e)}")
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

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



