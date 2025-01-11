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
                custom_user = User.objects.get(userid=userid, password=password, is_active=True)
                # Create or retrieve Django user for session management
                django_user, created = DjangoUser.objects.get_or_create(
                    username=custom_user.userid,
                    defaults={
                        'is_staff': custom_user.user_level == 'admin_level',
                        'is_superuser': custom_user.user_level == 'admin_level',
                        'password': 'dummy_password'  # Will be updated below
                    }
                )

                if created:
                    django_user.set_password(password)
                    django_user.save()

                auth_login(request, django_user)
                request.session['custom_user_id'] = custom_user.id

                # Redirect based on user level
                if custom_user.user_level == 'admin_level':
                    return redirect("all_leads")
                else:
                    return redirect("user_dashboard")
            except User.DoesNotExist:
                messages.error(request, "Invalid username or password")
                return redirect("login")

    return render(request, "login.html")

def logout(request):
    auth_logout(request)
    if 'custom_user_id' in request.session:
        del request.session['custom_user_id']
    return redirect("login")

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
@login_required
def add_user(request):
    if request.method == "POST":
        form = UserForm(request.POST)
        
        if request.POST.get("userid") == "admin":
            messages.error(request, "The User ID 'admin' is not allowed.")
            return render(request, "add_user.html", {"form": form})
        
        if form.is_valid():
            try:
                user = form.save()
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
def edit_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    
    if request.method == "POST":
        form = UserForm(request.POST, instance=user, edit_mode=True)
        if form.is_valid():
            form.save()
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

    context = {
        'leads': leads
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
            return redirect('all_leads')
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

                # Redirect based on user level
                if current_user.user_level == 'admin_level':
                    return redirect('all_leads')
                else:
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
    return render(request, 'agent.html', {'agents': agents})

def add_agent(request):
    if request.method == 'POST':
        name = request.POST['name']
        business_type = request.POST['business_type']
        location = request.POST['location']
        district = request.POST['district']
        contact_number = request.POST['contact_number']
        Agent.objects.create(
            name=name,
            business_type=business_type,
            location=location,
            district=district,
            contact_number=contact_number
        )
        return redirect('agent_list')
    return render(request, 'add_agent.html')


def edit_agent(request, agent_id):
    agent = Agent.objects.get(id=agent_id)
    if request.method == 'POST':
        agent.name = request.POST['name']
        agent.business_type = request.POST['business_type']
        agent.location = request.POST['location']
        agent.district = request.POST['district']
        agent.contact_number = request.POST['contact_number']
        agent.save()
        return redirect('agent_list')
    return render(request, 'edit_agent.html', {'agent': agent})

def delete_agent(request, agent_id):
    agent = get_object_or_404(Agent, id=agent_id)
    agent.delete()
    return redirect('agent_list')



from django.shortcuts import render, redirect
from .models import CV

def cv_management(request):
    job_titles = JobTitle.objects.all()
    selected_job_title = request.GET.get('job_title')
    
    cv_list = CV.objects.all()
    
    if selected_job_title:
        try:
            cv_list = cv_list.filter(job_title_id=selected_job_title)
        except ValueError:
            pass  # Handle invalid ID gracefully
    
    context = {
        'cv_list': cv_list,
        'job_titles': job_titles,
        'selected_job_title': selected_job_title,
    }
    
    return render(request, 'cv_management.html', context)



def add_cv(request):
    job_titles = JobTitle.objects.all()  # Fetch all job titles
    if request.method == 'POST':
        try:
            name = request.POST['name']
            address = request.POST['address']
            place = request.POST['place']
            district = request.POST['district']
            education = request.POST['education']
            experience = request.POST['experience']
            job_title_id = request.POST['job_title']  # Get the ID from the form
            job_title = JobTitle.objects.get(id=job_title_id)  # Get the actual JobTitle instance
            dob = request.POST['dob']
            remarks = request.POST.get('remarks', '')
            cv_attachment = request.FILES['cv_attachment']
            
            CV.objects.create(
                name=name,
                address=address,
                place=place,
                district=district,
                education=education,
                experience=experience,
                job_title=job_title,  # Pass the JobTitle instance
                dob=dob,
                remarks=remarks,
                cv_attachment=cv_attachment
            )
            return redirect('cv_management')
        except JobTitle.DoesNotExist:
            messages.error(request, 'Invalid job title selected.')
        except Exception as e:
            messages.error(request, f'Error creating CV: {str(e)}')
            
    return render(request, 'add_cv.html', {'job_titles': job_titles})



def edit_cv(request, id):
    cv = get_object_or_404(CV, id=id)
    job_titles = JobTitle.objects.all()
    districts = CV.KERALA_DISTRICTS

    if request.method == 'POST':
        try:
            cv.name = request.POST['name']
            cv.address = request.POST['address']
            cv.place = request.POST['place']
            cv.district = request.POST['district']
            cv.education = request.POST['education']
            cv.experience = request.POST['experience']
            # Get JobTitle instance instead of string
            job_title_id = request.POST['job_title']
            cv.job_title = JobTitle.objects.get(id=job_title_id)
            cv.dob = request.POST['dob']
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
