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
from .models import Requirement  # Ensure the correct model is imported
from .models import Lead,ServiceEntry,JobTitle
import json
from django.utils import timezone
from .models import Employee, Attendance
from django.db import transaction
from django.db import models



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

                # Move these lines here after custom_user is assigned
                request.session['custom_user_id'] = custom_user.id
                request.session['user_level'] = custom_user.user_level  

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



@login_required
def add_user(request):
    if request.method == "POST":
        form = UserForm(request.POST, request.FILES)  # Process submitted form data

        # Prevent using "admin" as a User ID
        if request.POST.get("userid") == "admin":
            messages.error(request, "The User ID 'admin' is not allowed.")
            return render(request, "add_user.html", {"form": form})

        if form.is_valid():
            try:
                user = form.save(commit=False)  # Create a user instance but don't save yet
                
                # Handle the optional image field
                if "image" in request.FILES:
                    user.image = request.FILES["image"]  # Assign uploaded image
                
                user.save()  # Save the user to the database

                messages.success(request, f"User '{user.name}' created successfully!")
                return redirect("users_table")
            except Exception as e:
                messages.error(request, f"Error creating user: {str(e)}")
        else:
            # Display form errors as messages
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = UserForm()  # Initialize an empty form for GET requests

    return render(request, "add_user.html", {"form": form})

@login_required
def users_table(request):
    users = User.objects.all().select_related('branch')
    return render(request, 'users_table.html', {'users': users})


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

def add_complaint(request):
    if request.method == 'POST':
        form = ComplaintForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('all_complaints')
    else:
        form = ComplaintForm()
    return render(request, 'add_complaints.html', {'form': form})

def all_complaints(request):
    complaints = Complaint.objects.all().order_by('created_at')  # Ascending order
    return render(request, 'all_complaints.html', {'complaints': complaints})

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



@login_required
def service_log(request):
    try:
        current_user = get_current_user(request)
        
        # Allow both superusers and admin_level users to access all logs
        if request.user.is_superuser or current_user.user_level == 'admin_level':
            logs = ServiceLog.objects.select_related(
                'added_by', 
                'complaint', 
                'assigned_person'
            ).all()
            all_users = User.objects.all()
            
            return render(request, 'service_log.html', {
                'logs': logs,
                'all_users': all_users,
                'current_user': current_user
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

            complaint = Complaint.objects.get(id=complaint_id)

            service_log = ServiceLog(
                customer_name=customer_name,
                type=type,
                complaint=complaint,
                remark=remark,
                voice_note=voice_note,
                added_by=current_user
            )
            service_log.save()
            
            messages.success(request, 'Service log added successfully!')
            
            # Redirect based on user level
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

@login_required
def service_entry(request):
    try:
        current_user = get_current_user(request)
        service_entries = ServiceEntry.objects.all().order_by('-date')
        return render(request, 'service_entry.html', {
            'service_entries': service_entries,
            'current_user': current_user
        })
    except Exception as e:
        messages.error(request, f'Error accessing service entries: {str(e)}')
        return redirect('login')



@login_required
def add_service_entry(request):
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
            
            # Create new service entry
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
            
            # Redirect based on user level
            if current_user.user_level == 'admin_level' or request.user.is_superuser:
                return redirect('service_entry')
            else:
                return redirect('user_service_entry')
        
        return render(request, 'add_service_entry.html', {
            'complaints': complaints,
            'current_user': current_user
        })
        
    except Exception as e:
        messages.error(request, f'Error adding service entry: {str(e)}')
        # Redirect based on user level
        if current_user.user_level == 'admin_level' or request.user.is_superuser:
            return redirect('service_entry')
        else:
            return redirect('user_service_entry')

@login_required
def edit_service_entry(request, entry_id):
    entry = get_object_or_404(ServiceEntry, id=entry_id)
    current_user = get_current_user(request)
    complaints = Complaint.objects.all().order_by('created_at')

    if request.method == 'POST':
        entry.customer = request.POST.get('customer')
        complaint_description = request.POST.get('complaint')
        entry.complaint = complaint_description
        entry.remarks = request.POST.get('remarks')
        entry.place = request.POST.get('place')
        entry.status = request.POST.get('status')
        entry.save()
        
        # Redirect based on user level
        if current_user.user_level == 'admin_level' or request.user.is_superuser:
            return redirect('service_entry')
        else:
            return redirect('user_service_entry')

    context = {
        'entry': entry,
        'complaints': complaints,
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



# Add user-specific edit and delete views
@login_required
def user_edit_service_entry(request, entry_id):
    # Get entry and verify it belongs to current user
    entry = get_object_or_404(ServiceEntry, id=entry_id)
    current_user = get_current_user(request)
    
    if entry.user != current_user:
        messages.error(request, "You don't have permission to edit this entry.")
        return redirect('user_service_entry')
    
    complaints = Complaint.objects.all().order_by('created_at')

    if request.method == 'POST':
        entry.customer = request.POST.get('customer')
        complaint_description = request.POST.get('complaint')
        entry.complaint = complaint_description
        entry.remarks = request.POST.get('remarks')
        entry.place = request.POST.get('place')
        entry.status = request.POST.get('status')
        entry.save()
        return redirect('user_service_entry')

    context = {
        'entry': entry,
        'complaints': complaints,
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

def agent_list(request):
    agents = Agent.objects.all()
    business_types = BusinessType.objects.all()
    return render(request, 'agent.html', {'agents': agents, 'business_types': business_types})

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
                created_by=request.user
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



@login_required
def employee_management(request):
    employees = Employee.objects.select_related("user").all()
    return render(request, "employee_management.html", {"employees": employees})


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
        photo = request.FILES.get('photo')
        address = request.POST.get('address', '')
        phone_personal = request.POST['phone_personal']
        phone_residential = request.POST.get('phone_residential', '')
        place = request.POST['place']
        district = request.POST['district']
        education = request.POST['education']
        experience = request.POST.get('experience', '')
        job_title = request.POST['job_title']
        organization = request.POST.get("organization", "")
        joining_date = request.POST['joining_date']
        dob = request.POST['dob']
        bank_account_number = request.POST.get('bank_account_number', '')
        ifsc_code = request.POST.get('ifsc_code', '')
        bank_name = request.POST.get('bank_name', '')
        branch = request.POST.get('branch', '')
        status = request.POST.get("status", "active")

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
        )

        # Handle multiple file uploads
        for file in request.FILES.getlist('attachments'):
            Attachment.objects.create(employee=employee, file=file)

        messages.success(request, "Employee added successfully.")
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

    # Get users who are not assigned to another employee OR the current employee's user
    users = User.objects.exclude(employee__isnull=False).union(
        User.objects.filter(id=employee.user.id if employee.user else None)
    )

    if request.method == "POST":
        user_id = request.POST.get("user_id")
        selected_user = User.objects.get(id=user_id) if user_id else None

        # Ensure User ID is unique
        if selected_user and Employee.objects.exclude(id=employee.id).filter(user=selected_user).exists():
            messages.error(request, f"User '{selected_user.name}' is already assigned to another employee.")
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
        employee.status = request.POST.get("status", "active")

        employee.save()
        messages.success(request, "Employee updated successfully.")
        return redirect("employee_management")

    context = {
        "employee": employee,
        "users": users,  # Pass only available users
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


@login_required
def make_experience_certificate(request):
    employees = Employee.objects.all()
    return render(request, 'make_experience_certificate.html', {'employees': employees})



from django.utils import timezone

def make_salary_certificate(request):
    employees = Employee.objects.all()
    current_date = timezone.now().strftime("%d/%m/%Y")  # Format the date as DD/MM/YYYY
    return render(request, 'make_salary_certificate.html', {
        'employees': employees,
        'current_date': current_date
    })





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



from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from .models import Employee

def salary_certificate(request, employee_id):
    employee = get_object_or_404(Employee, id=employee_id)
    clicked_date = request.GET.get("date", timezone.now().strftime("%d/%m/%Y"))  # Default to current date if not provided
    salary_details = getattr(employee, "salary_details", None)

    if salary_details and salary_details.salary:
        salary_words = num2words(salary_details.salary, lang="en_IN") + " Rupees Only"
    else:
        salary_words = "Zero Rupees Only"

    return render(request, "salary_certificate.html", {
        "employee": employee,
        "salary_words": salary_words,
        "clicked_date": clicked_date  # Pass the clicked date to the template
    })





from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import EmployeeSalary, Employee  # Ensure Employee is imported

@csrf_exempt
def add_salary_details(request):
    if request.method == "POST":
        employee_id = request.POST.get("employee_id")
        joining_date = request.POST.get("joining_date")
        salary = request.POST.get("salary")

        try:
            employee = Employee.objects.get(id=employee_id)
            salary_details, created = EmployeeSalary.objects.get_or_create(employee=employee)
            salary_details.joining_date = joining_date
            salary_details.salary = salary
            salary_details.save()

            return JsonResponse({"success": True})
        except Employee.DoesNotExist:
            return JsonResponse({"success": False, "error": "Employee not found"})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})

    return JsonResponse({"success": False, "error": "Invalid request"})


from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from .models import EmployeeSalary, Employee  # Ensure Employee is imported

def get_salary_details(request, employee_id):
    try:
        salary_details = EmployeeSalary.objects.get(employee_id=employee_id)
        return JsonResponse({
            "joining_date": salary_details.joining_date.strftime("%Y-%m-%d") if salary_details.joining_date else "",
            "salary": str(salary_details.salary),
        })
    except EmployeeSalary.DoesNotExist:
        return JsonResponse({"error": "No salary details found"}, status=404)
    

def user_control(request):
    return render(request, 'user_control.html')


from django.shortcuts import render
from .models import Employee

def attendance(request):
    # Get all employees with their related user data
    employees = Employee.objects.select_related('user').all()
    
    # Get the current month and year
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
        
        # Convert the date to day of month for the key
        day = str(record.date.day)
        
        # Determine attendance status
        status = 'initial'
        if record.punch_in and record.punch_out:
            status = 'full'
        elif record.punch_in:
            status = 'half'
        elif record.status == 'leave':
            status = 'leave'
        
        # Store the attendance data for this day
        attendance_data[employee_id][day] = {
            'status': status,
            'punch_in': record.punch_in.isoformat() if record.punch_in else None,
            'punch_out': record.punch_out.isoformat() if record.punch_out else None
        }
    
    # Calculate days in current month
    days_in_month = (today.replace(day=1) + timezone.timedelta(days=32)).replace(day=1).day - 1
    
    context = {
        'employees': employees,
        'attendance_data': json.dumps(attendance_data),
        'current_month': today.strftime('%B %Y'),
        'days_in_month': days_in_month,
        'today': today.day,
        'range': range(1, days_in_month + 1)
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

from django.utils import timezone

@login_required
def punch_in(request):
    if request.method == 'POST':
        try:
            # Get the custom user from session
            custom_user_id = request.session.get('custom_user_id')
            if not custom_user_id:
                return JsonResponse({'success': False, 'error': 'User session not found'})
            
            # Get the custom user
            custom_user = User.objects.get(id=custom_user_id)
            
            # Get the employee associated with the custom user
            employee = Employee.objects.get(user=custom_user)
            now = timezone.now()
            today = now.date()
            
            # Try to get existing attendance record for today
            try:
                attendance = Attendance.objects.get(
                    employee=employee,
                    date=today,
                    day=today.day
                )
                # If record exists but no punch-in, update it
                if not attendance.punch_in:
                    attendance.punch_in = now
                    attendance.status = 'half'
                    attendance.save()
                else:
                    return JsonResponse({
                        'success': False,
                        'error': 'Already punched in for today'
                    })
            except Attendance.DoesNotExist:
                # Create new attendance record
                attendance = Attendance.objects.create(
                    employee=employee,
                    date=today,
                    day=today.day,
                    status='half',
                    punch_in=now
                )
            except Attendance.MultipleObjectsReturned:
                # Handle case of multiple records
                # Get the latest record
                attendance = Attendance.objects.filter(
                    employee=employee,
                    date=today,
                    day=today.day
                ).order_by('-created_at').first()
                
                if not attendance.punch_in:
                    attendance.punch_in = now
                    attendance.status = 'half'
                    attendance.save()
                else:
                    return JsonResponse({
                        'success': False,
                        'error': 'Already punched in for today'
                    })
            
            # Return the updated attendance status and time
            return JsonResponse({
                'success': True,
                'status': 'half',
                'punch_in': now.strftime('%H:%M:%S'),
                'employee_id': str(employee.id),
                'day': str(now.day)
            })
            
        except User.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'User not found'})
        except Employee.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'No employee record found for this user'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Invalid request'})

@login_required
def punch_out(request):
    if request.method == 'POST':
        try:
            # Get the custom user from session
            custom_user_id = request.session.get('custom_user_id')
            if not custom_user_id:
                return JsonResponse({'success': False, 'error': 'User session not found'})
            
            # Get the custom user
            custom_user = User.objects.get(id=custom_user_id)
            
            # Get the employee associated with the custom user
            employee = Employee.objects.get(user=custom_user)
            now = timezone.now()
            today = now.date()
            
            # Get today's attendance record and update punch-out time
            attendance = Attendance.objects.get(
                employee=employee,
                date=today,
                day=today.day  # Add the day field to make the query more specific
            )
            
            if attendance.punch_in:  # Only update if already punched in
                attendance.punch_out = now
                attendance.status = 'full'  # Set to full day when punching out
                attendance.save()
                return JsonResponse({'success': True})
            else:
                return JsonResponse({'success': False, 'error': 'Must punch in before punching out'})
            
        except Attendance.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'No attendance record found for today'})
        except User.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'User not found'})
        except Employee.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'No employee record found for this user'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Invalid request'})

@login_required
def get_attendance_status(request):
    try:
        date_str = request.GET.get('date')
        date = timezone.datetime.strptime(date_str, '%Y-%m-%d').date()
        
        # Get the custom user from session
        custom_user_id = request.session.get('custom_user_id')
        if not custom_user_id:
            return JsonResponse({'error': 'User session not found'}, status=400)
        
        # Get the custom user
        custom_user = User.objects.get(id=custom_user_id)
        
        # Get the employee associated with the custom user
        employee = Employee.objects.get(user=custom_user)
        attendance = Attendance.objects.filter(
            employee=employee,
            date=date
        ).first()
        
        if attendance:
            return JsonResponse({
                'punch_in': attendance.punch_in.isoformat() if attendance.punch_in else None,
                'punch_out': attendance.punch_out.isoformat() if attendance.punch_out else None
            })
        return JsonResponse({'punch_in': None, 'punch_out': None})
    except User.DoesNotExist:
        return JsonResponse({'error': 'User not found'}, status=400)
    except Employee.DoesNotExist:
        return JsonResponse({'error': 'No employee record found for this user'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

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





from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Attendance, User
import json

@csrf_exempt
def update_attendance(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            user_id = data.get("user_id")
            date = data.get("date")
            status = data.get("status")

            attendance, created = Attendance.objects.get_or_create(user_id=user_id, date=date)
            attendance.status = status
            attendance.save()

            return JsonResponse({"success": True, "message": "Attendance updated successfully!"})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})
    return JsonResponse({"success": False, "error": "Invalid request"})
