from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login as auth_login  # Alias the imported login function
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .forms import BranchForm,RequirementForm
from django.http import JsonResponse
from django.contrib.auth import logout as auth_logout
from .forms import UserForm
from .models import Branch, Requirement, User
from django.shortcuts import get_object_or_404
from django.contrib.auth import authenticate, login as auth_login
from django.contrib.auth.models import User as DjangoUser  # Added this import
from .forms import BranchForm, RequirementForm, UserForm,LeadRequirementAmount
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

        # First try Django's built-in authentication for superuser
        django_user = authenticate(request, username=userid, password=password)
        
        if django_user and django_user.is_superuser:
            auth_login(request, django_user)
            return redirect("all_leads")

        else:
            # Try custom authentication for regular users
            try:
                custom_user = User.objects.get(userid=userid, password=password)
                if custom_user:
                    # Create or get Django user for session management
                    django_user, created = DjangoUser.objects.get_or_create(
                        username=custom_user.userid,
                        defaults={
                            'is_staff': False, 
                            'is_superuser': False,
                            'password': 'dummy_password'  # This will be replaced
                        }
                    )
                    
                    if created:
                        django_user.set_password(password)
                        django_user.save()
                    
                    auth_login(request, django_user)
                    request.session['custom_user_id'] = custom_user.id
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
        
        # Check if username is admin
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
    if request.method == 'POST':
        form = LeadForm(request.POST, request.FILES)
        if form.is_valid():
            lead = form.save(commit=False)
            custom_user = User.objects.get(id=request.session['custom_user_id'])
            lead.user = custom_user
            lead.save()
            
            form.save_m2m()
            
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
                        remarks=remarks.get(req_id, '')  # Save remarks for each requirement
                    )
                
                messages.success(request, 'Lead added successfully!')
                return redirect('user_dashboard')
                
            except json.JSONDecodeError:
                messages.error(request, 'Invalid requirement data format')
            except (ValueError, TypeError):
                messages.error(request, 'Invalid amount value')
            except Exception as e:
                messages.error(request, f'Error saving lead: {str(e)}')
    else:
        form = LeadForm()
    
    requirements = Requirement.objects.all()
    return render(request, 'add_lead.html', {
        'form': form,
        'requirements': requirements,
        'existing_amounts': {}
    })

@login_required
def edit_lead(request, lead_id):
    lead = get_object_or_404(Lead, id=lead_id)
    # Get the referring page
    referer = request.META.get('HTTP_REFERER', '')
    is_from_all_leads = 'all_leads' in referer
    
    if request.method == "POST":
        form = LeadForm(request.POST, request.FILES, instance=lead)
        if form.is_valid():
            lead = form.save()
            
            # Handle requirement amounts and remarks
            amounts_data = request.POST.get('requirement_amounts_data', '{}')
            remarks_data = request.POST.get('requirement_remarks_data', '{}')
            
            try:
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
                
                messages.success(request, f'Lead "{lead.firm_name}" updated successfully!')
                # Redirect based on where the request came from
                if is_from_all_leads:
                    return redirect('all_leads')
                return redirect('all_leads')
                
            except json.JSONDecodeError:
                messages.error(request, 'Invalid requirement data format')
            except (ValueError, TypeError):
                messages.error(request, 'Invalid amount value')
            except Exception as e:
                messages.error(request, f'Error saving lead: {str(e)}')
    else:
        form = LeadForm(instance=lead)
    
    # Get existing requirement amounts and remarks
    existing_amounts = {
        str(ra.requirement_id): str(ra.amount)
        for ra in LeadRequirementAmount.objects.filter(lead=lead)
    }
    
    return render(request, 'edit_lead.html', {
        'form': form,
        'lead': lead,
        'requirements': Requirement.objects.all(),
        'existing_amounts': existing_amounts,
        'is_from_all_leads': is_from_all_leads  # Pass this to the template
    })



@login_required
def all_leads(request):
    if request.user.is_superuser:
        leads = Lead.objects.all().select_related('user', 'user__branch').prefetch_related('requirements')

        # Filter leads based on date range, if provided
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        if start_date and end_date:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date() + timedelta(days=1)
            leads = leads.filter(created_at__gte=start_date, created_at__lt=end_date)

        # Filter leads based on branch, if provided and valid
        branch_id = request.GET.get('branch')
        if branch_id and branch_id.isdigit():
            leads = leads.filter(user__branch_id=branch_id)

        # Filter leads based on user, if provided and valid
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

        # Get all branches, users and requirements for the filters
        branches = Branch.objects.all()
        users = User.objects.all().select_related('branch')
        requirements = Requirement.objects.all()

        return render(request, 'all_leads.html', {
            'leads': leads,
            'branches': branches,
            'users': users,
            'requirements': requirements,
            'selected_user': user_id,
            'selected_branch': branch_id,
            'selected_requirements': requirement_ids,
        })
    else:
        # messages.error(request, "You don't have permission to view this page.")
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