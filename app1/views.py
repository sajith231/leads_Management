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

def user_dashboard(request):
    leads = Lead.objects.prefetch_related(
        Prefetch('requirement_amounts', queryset=LeadRequirementAmount.objects.all())
    ).all()

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
            form.save()  # This will handle both m2m and requirement amounts
            messages.success(request, 'Lead added successfully!')
            return redirect('user_dashboard')
    else:
        form = LeadForm()
    
    # Get all requirements for initial rendering
    requirements = Requirement.objects.all()
    return render(request, 'add_lead.html', {
        'form': form,
        'requirements': requirements,
        'existing_amounts': {}  # For edit mode
    })


@login_required
def edit_lead(request, lead_id):
    lead = get_object_or_404(Lead, id=lead_id)
    
    if request.method == "POST":
        form = LeadForm(request.POST, request.FILES, instance=lead)
        if form.is_valid():
            lead_instance = form.save(commit=False)
            lead_instance.save()
            form.save_m2m()
            
            # Handle requirement amounts
            amounts_data = request.POST.get('requirement_amounts_data', '')
            if amounts_data:
                try:
                    amounts = json.loads(amounts_data)
                    LeadRequirementAmount.objects.filter(lead=lead_instance).delete()
                    for req_id, amount in amounts.items():
                        if amount:
                            LeadRequirementAmount.objects.create(
                                lead=lead_instance,
                                requirement_id=int(req_id),
                                amount=float(amount)
                            )
                except Exception as e:
                    messages.warning(request, f"Error saving requirement amounts: {str(e)}")
            
            messages.success(request, f'Lead "{lead_instance.firm_name}" updated successfully!')
            return redirect('user_dashboard')
    else:
        form = LeadForm(instance=lead)
    
    # Get existing requirement amounts - convert all keys to strings
    existing_amounts = {
        str(ra.requirement_id): str(ra.amount)
        for ra in LeadRequirementAmount.objects.filter(lead=lead)
    }
    
    context = {
        'form': form,
        'lead': lead,
        'requirements': Requirement.objects.all(),
        'existing_amounts': existing_amounts
    }
    
    return render(request, 'edit_lead.html', context)


@login_required
def all_leads(request):
    if request.user.is_superuser:
        leads = Lead.objects.all().select_related('user', 'user__branch').prefetch_related('requirements')

        # Filter leads based on date range, if provided
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        if start_date and end_date:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date() + timedelta(days=1)  # Add one day to include the end date
            leads = leads.filter(created_at__gte=start_date, created_at__lt=end_date)

        # Filter leads based on branch, if provided and valid
        branch_id = request.GET.get('branch')
        if branch_id and branch_id.isdigit():  # Check if branch_id is a valid number
            leads = leads.filter(user__branch_id=branch_id)

        # Filter leads based on requirements, if provided and valid
        requirement_ids = request.GET.getlist('requirements')
        requirement_ids = [req_id for req_id in requirement_ids if req_id.isdigit()]  # Filter out empty values
        if requirement_ids:
            leads = leads.filter(requirements__id__in=requirement_ids).distinct()

        # Filter by firm name, if provided
        firm_name = request.GET.get('firm_name')
        if firm_name:
            leads = leads.filter(firm_name__icontains=firm_name)

        # Get all branches and requirements for the filters
        branches = Branch.objects.all()
        requirements = Requirement.objects.all()

        return render(request, 'all_leads.html', {
            'leads': leads,
            'branches': branches,
            'requirements': requirements
        })
    else:
        messages.error(request, "You don't have permission to view this page.")
        return redirect('user_dashboard')





@login_required
def delete_lead(request, lead_id):
    if request.method == 'POST':
        lead = get_object_or_404(Lead, id=lead_id)
        lead_name = lead.firm_name
        
        try:
            # Since SoftwareAmount has a foreign key to Lead with CASCADE,
            # we don't need to explicitly delete SoftwareAmount records
            lead.delete()
            messages.success(request, f'Lead "{lead_name}" deleted successfully.')
        except Exception as e:
            messages.error(request, f'Error deleting lead: {str(e)}')
            # Log the error for debugging
            print(f"Error deleting lead {lead_id}: {str(e)}")
            
    return redirect('user_dashboard')




