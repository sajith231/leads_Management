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
from .forms import BranchForm, RequirementForm, UserForm,LeadRequirementAmount,AreaForm,LocationForm,Location,Hardware,HardwareForm
from .models import Lead
from .forms import LeadForm
from django.db.models import Q
from datetime import datetime, timedelta
from .models import Requirement  # Ensure the correct model is imported
from .models import Lead
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
        current_user = User.objects.get(id=request.session['custom_user_id'])

    # Handle POST requests
    if request.method == 'POST':
        form = LeadForm(request.POST, request.FILES)
        if form.is_valid():
            lead = form.save(commit=False)
            lead.user = current_user
            lead.save()
            form.save_m2m()  # Save Many-to-Many relationships including hardware

            # Save LeadRequirementAmount and other custom data
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

                messages.success(request, 'Lead added successfully!')
                if request.user.is_superuser or current_user.user_level == 'admin_level':
                    return redirect('all_leads')
                else:
                    return redirect('user_dashboard')

            except json.JSONDecodeError:
                messages.error(request, 'Invalid requirement data format')
            except (ValueError, TypeError):
                messages.error(request, 'Invalid amount value')
            except Exception as e:
                messages.error(request, f'Error saving lead: {str(e)}')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = LeadForm()

    requirements = Requirement.objects.all()
    hardwares = Hardware.objects.all()

    return render(request, 'add_lead.html', {
        'form': form,
        'requirements': requirements,
        'hardwares': hardwares,
        'existing_amounts': {}
    })

@login_required
def edit_lead(request, lead_id):
    """
    View to edit a lead.
    """
    lead = get_object_or_404(Lead, id=lead_id)

    # Determine the user type
    if request.user.is_superuser:
        current_user = User.objects.filter(userid=request.user.username, user_level='admin_level').first()
    else:
        current_user = User.objects.get(id=request.session['custom_user_id'])

    if request.method == "POST":
        form = LeadForm(request.POST, request.FILES, instance=lead)
        if form.is_valid():
            lead = form.save()

            # Handle requirement amounts and remarks
            amounts_data = request.POST.get('requirement_amounts_data', '{}')
            remarks_data = request.POST.get('requirement_remarks_data', '{}')

            # Handle hardware amounts
            hardware_data = request.POST.get('hardware_amounts_data', '{}')

            try:
                # Save requirements amounts and remarks
                amounts = json.loads(amounts_data)
                remarks = json.loads(remarks_data)

                # Delete existing requirement amounts
                LeadRequirementAmount.objects.filter(lead=lead).delete()

                # Create new requirement amounts with remarks
                for req_id, amount in amounts.items():
                    LeadRequirementAmount.objects.create(
                        lead=lead,
                        requirement_id=int(req_id),
                        amount=float(amount),
                        remarks=remarks.get(req_id, '')
                    )

                # Save hardware data
                hardware_amounts = json.loads(hardware_data)
                lead.hardwares.clear()  # Clear existing hardware relationships
                for hw_id, amount in hardware_amounts.items():
                    hardware = Hardware.objects.get(id=int(hw_id))
                    lead.hardwares.add(hardware)
                    # Optionally store the custom amount (if needed)

                messages.success(request, f'Lead "{lead.firm_name}" updated successfully!')

                # Redirect based on user level
                if request.user.is_superuser or current_user.user_level == 'admin_level':
                    return redirect('all_leads')
                else:
                    return redirect('user_dashboard')

            except json.JSONDecodeError:
                messages.error(request, 'Invalid requirement or hardware data format')
            except (ValueError, TypeError):
                messages.error(request, 'Invalid value in input data')
            except Exception as e:
                messages.error(request, f'Error saving lead: {str(e)}')
    else:
        form = LeadForm(instance=lead)

    # Get existing requirement amounts and remarks
    existing_amounts = {
        str(ra.requirement_id): str(ra.amount)
        for ra in LeadRequirementAmount.objects.filter(lead=lead)
    }

    # Get existing hardware amounts
    existing_hardware_amounts = {
        hw.id: hw.price for hw in lead.hardwares.all()
    }

    return render(request, 'edit_lead.html', {
        'form': form,
        'lead': lead,
        'requirements': Requirement.objects.all(),
        'hardwares': Hardware.objects.all(),
        'existing_amounts': existing_amounts,
        'existing_hardware_amounts': existing_hardware_amounts,
    })



@login_required
def all_leads(request):
    # Check if the user is a superuser or a normal user
    if request.user.is_superuser or request.session.get('custom_user_id'):
        # Fetch the current user for lead creation
        if request.user.is_superuser:
            # For superuser, get the first admin-level user or create one if not exists
            try:
                current_user = User.objects.filter(user_level='admin_level').first()
                if not current_user:
                    # Create a default admin user
                    current_user = User.objects.create(
                        name='System Admin',
                        userid=request.user.username,
                        password='default_password',
                        branch=Branch.objects.first() or Branch.objects.create(name='Default Branch'),
                        user_level='admin_level'
                    )
                    messages.warning(request, "Created a default admin user for lead management.")
            except Exception as e:
                messages.error(request, f"Error creating admin user: {str(e)}")
                current_user = None
        else:
            current_user = User.objects.get(id=request.session['custom_user_id'])

        # Fetch leads for the logged-in user or all leads if superuser
        if request.user.is_superuser:
            leads = Lead.objects.all()
        else:
            leads = Lead.objects.filter(user=current_user)

        leads = leads.select_related('user', 'user__branch', 'location', 'location__area', 'location__district').prefetch_related('requirements')

        # Filter leads based on date range, if provided
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        if start_date and end_date:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date() + timedelta(days=1)
            leads = leads.filter(created_at__gte=start_date, created_at__lt=end_date)

        # Filter leads based on branch, if provided and valid
        branches = Branch.objects.all()
        branch_id = request.GET.get('branch')
        if branch_id and branch_id.isdigit():
            leads = leads.filter(user__branch_id=branch_id)

        # Filter leads based on user, if provided and valid
        users = User.objects.all().select_related('branch')
        user_id = request.GET.get('user')
        if user_id and user_id.isdigit():
            leads = leads.filter(user_id=user_id)

        # Filter leads based on requirements
        requirement_ids = request.GET.getlist('requirements')
        requirement_ids = [req_id for req_id in requirement_ids if req_id.isdigit()]
        if requirement_ids:
            leads = leads.filter(requirements__id__in=requirement_ids).distinct()

        # Filter by firm name, if provided
        firm_name = request.GET.get('firm_name')
        if firm_name:
            leads = leads.filter(firm_name__icontains=firm_name)

       # Filter by planet entry status, if provided
        planet_entry = request.GET.get('planet_entry', 'false')  # Default to 'false' (Not Entered)
        if planet_entry == 'false':  # Not Entered
            leads = leads.filter(planet_entry=False)
        elif planet_entry == 'true':  # Entered
            leads = leads.filter(planet_entry=True)
        # If planet_entry is None or other, do not filter
        # If planet_entry is None, do not filter (default behavior)





        # Get all requirements for the filters
        requirements = Requirement.objects.all()

        # Get all districts for the dropdown
        districts = District.objects.all()

        # Prepare the LeadForm for adding new leads
        lead_form = LeadForm()

        return render(request, 'all_leads.html', {
            'leads': leads,
            'branches': branches,
            'users': users,
            'requirements': requirements,
            'districts': districts,
            'selected_user': user_id,
            'selected_branch': branch_id,
            'selected_requirements': requirement_ids,
            'selected_planet_entry': planet_entry,
            'lead_form': lead_form,
            'current_user': current_user,
        })
    else:
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