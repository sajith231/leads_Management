from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import Field, Credentials, CredentialDetail, Category

from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from django.contrib.auth.decorators import login_required
from app1.models import User  # Import the User model from app1

from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import Field, Credentials, CredentialDetail, Category
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from app1.models import User  # Import your User model from app1

def credential_management(request):
    # Get search parameters from request
    search_query = request.GET.get('search', '')
    category_filter = request.GET.get('category', '')
    
    # Start with all credentials
    credentials_queryset = Credentials.objects.all()
    
    # Check user level from session
    user_level = request.session.get('user_level', 'normal')
    
    # Filter credentials based on user level
    if user_level not in ['normal', 'admin_level']:
        # For non-admin users, show only priority 2 credentials
        credentials_queryset = credentials_queryset.filter(credential_type='priority 2')
    
    # Apply search filter if provided
    if search_query:
        credentials_queryset = credentials_queryset.filter(
            name__icontains=search_query
        ) | credentials_queryset.filter(
            category__icontains=search_query
        ) | credentials_queryset.filter(
            remark__icontains=search_query
        )
    
    # Apply category filter if provided
    if category_filter:
        credentials_queryset = credentials_queryset.filter(category__iexact=category_filter)
    
    # Set up pagination on the filtered results
    paginator = Paginator(credentials_queryset, 12)  # 12 credentials per page
    
    # Get the current page number from the request
    page_number = request.GET.get('page', 1)
    
    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)
    
    # Get unique categories for the dropdown filter
    categories = Category.objects.all()
    fields = Field.objects.all()
    
    return render(request, 'credential_management.html', {
        'fields': fields,
        'credentials': credentials_queryset,
        'page_obj': page_obj,
        'categories': categories,
        'search_query': search_query,
        'category_filter': category_filter
    })

def add_field(request):
    if request.method == 'POST':
        field_name = request.POST.get('field_name')
        if field_name:
            Field.objects.create(name=field_name)
            return redirect('credential_management')
    return redirect('credential_management')

def edit_field(request, field_id):
    field = get_object_or_404(Field, id=field_id)
    if request.method == 'POST':
        new_name = request.POST.get('field_name')
        if new_name:
            field.name = new_name
            field.save()
        return redirect('credential_management')
    return render(request, 'edit_field_modal.html', {'field': field})

def delete_field(request, field_id):
    field = get_object_or_404(Field, id=field_id)
    field.delete()
    return redirect('credential_management')

def add_credential(request):
    if request.method == 'POST':
        credential_name = request.POST.get('credential_name')
        category = request.POST.get('category')
        remark = request.POST.get('remark')
        credential_type = request.POST.get('credential_type')
        
        if credential_name:
            # Get the current user from the session
            user_id = request.session.get('user_id')
            user = None
            if user_id:
                try:
                    user = User.objects.get(id=user_id)
                except User.DoesNotExist:
                    pass
                
            # Create the credential with the user who added it
            Credentials.objects.create(
                name=credential_name,
                category=category,
                remark=remark,
                credential_type=credential_type,
                
            )
            return redirect('credential_management')
    
    categories = Category.objects.all()
    return render(request, 'add_credential.html', {'categories': categories})


def delete_credential(request, id):
    credential = get_object_or_404(Credentials, id=id)
    credential.delete()
    return redirect('credential_management')

# views.py
def edit_credential(request, id):
    credential = get_object_or_404(Credentials, id=id)
    categories = Category.objects.all()

    if request.method == 'POST':
        credential_name = request.POST.get('credential_name')
        category = request.POST.get('category')
        remark = request.POST.get('remark')
        credential_type = request.POST.get('credential_type')

        if credential_name:
            credential.name = credential_name
            credential.category = category
            credential.remark = remark
            credential.credential_type = credential_type
            credential.save()
            return redirect('credential_management')

    return render(request, 'edit_credential.html', {
        'credential': credential,
        'categories': categories
    })


@require_POST
def add_credential_detail(request, credential_id):
    credential = get_object_or_404(Credentials, id=credential_id)
    field_id = request.POST.get('field_id')
    value = request.POST.get('value')
    
    if field_id and value:
        field = get_object_or_404(Field, id=field_id)
        CredentialDetail.objects.create(
            credential=credential,
            field=field,
            value=value
        )
    return redirect('credential_detail', id=credential_id)

def credential_detail(request, id):
    credential = get_object_or_404(Credentials, id=id)
    details = credential.details.all().select_related('field')
    fields = Field.objects.all()
    return render(request, 'credential_detail.html', {
        'credential': credential,
        'details': details,
        'fields': fields
    })

def edit_credential_detail(request, detail_id):
    detail = get_object_or_404(CredentialDetail, id=detail_id)
    if request.method == 'POST':
        field_id = request.POST.get('field_id')
        value = request.POST.get('value')
        
        if field_id and value:
            field = get_object_or_404(Field, id=field_id)
            detail.field = field
            detail.value = value
            detail.save()
            
    return redirect('credential_detail', id=detail.credential.id)

def delete_credential_detail(request, detail_id):
    detail = get_object_or_404(CredentialDetail, id=detail_id)
    credential_id = detail.credential.id
    detail.delete()
    return redirect('credential_detail', id=credential_id)

# New Category Management Views
def add_category(request):
    if request.method == 'POST':
        category_name = request.POST.get('category_name')
        if category_name:
            Category.objects.create(name=category_name)
            return redirect('add_credential')
    return redirect('add_credential')

def edit_category(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    if request.method == 'POST':
        new_name = request.POST.get('category_name')
        if new_name:
            category.name = new_name
            category.save()
        return redirect('add_credential')
    return redirect('add_credential')

def delete_category(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    category.delete()
    return redirect('add_credential')




from django.shortcuts import render, redirect
from django.views.generic import ListView
from .models import InformationCenter, ProductType, ProductCategory
from django.contrib.auth.decorators import login_required

from django.utils import timezone
from datetime import timedelta

class InformationCenterListView(ListView):
    model = InformationCenter
    template_name = 'information_center.html'
    context_object_name = 'information_items'
    ordering = ['product_category__name', '-added_date']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        product_type = self.request.GET.get('product_type')
        product_category = self.request.GET.get('product_category')
        search_query = self.request.GET.get('search', '').strip()
        
        # Filter by priority based on user status
        if not self.request.user.is_superuser:
            queryset = queryset.filter(priority='priority2')
        
        if product_type:
            queryset = queryset.filter(product_type_id=product_type)
        if product_category:
            queryset = queryset.filter(product_category_id=product_category)
        if search_query:
            queryset = queryset.filter(title__icontains=search_query)
        
        # Ensure proper ordering for regroup to work correctly
        return queryset.select_related('product_category', 'product_type').order_by('product_category__name', '-added_date')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['product_types'] = ProductType.objects.all()
        context['product_categories'] = ProductCategory.objects.all()
        
        # Get items from the last two days
        two_days_ago = timezone.now() - timedelta(days=1)
        whats_new_items = InformationCenter.objects.filter(added_date__gte=two_days_ago).order_by('-added_date')
        context['whats_new_items'] = whats_new_items
        
        return context

# views.py
@login_required
def add_information_center(request):
    if request.method == 'POST':
        title = request.POST.get('title')
        remark = request.POST.get('remark')
        url = request.POST.get('url')
        added_date = request.POST.get('added_date')
        product_type_id = request.POST.get('product_type')
        product_category_id = request.POST.get('product_category')
        thumbnail = request.FILES.get('thumbnail')
        priority = request.POST.get('priority')
        language = request.POST.get('language')
        duration = request.POST.get('duration')
        host = request.POST.get('host')
        
        product_type = ProductType.objects.get(id=product_type_id)
        product_category = ProductCategory.objects.get(id=product_category_id)
        
        # Calculate the next position number for this category
        last_position = InformationCenter.objects.filter(
            product_category=product_category
        ).aggregate(Max('position'))['position__max']
        position = (last_position or 0) + 1

        InformationCenter.objects.create(
            title=title,
            remark=remark,
            url=url,
            added_date=added_date,
            uploaded_by=request.user,
            product_type=product_type,
            product_category=product_category,
            thumbnail=thumbnail,
            priority=priority,
            language=language,
            duration=duration,
            host=host,
            position=position
        )
        return redirect('information_center')

    product_types = ProductType.objects.all()
    product_categories = ProductCategory.objects.all()

    return render(request, 'add_information_center.html', {
        'product_types': product_types,
        'product_categories': product_categories,
    })

from django.http import JsonResponse
from .models import InformationCenter
from django.db.models import Max

def get_next_position(request):
    category_id = request.GET.get('category_id')
    if not category_id:
        return JsonResponse({'error': 'Category ID is required'}, status=400)
    
    last_position = InformationCenter.objects.filter(
        product_category_id=category_id
    ).aggregate(Max('position'))['position__max']
    
    next_position = (last_position or 0) + 1
    
    return JsonResponse({'next_position': next_position})

# views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView
from .models import InformationCenter, ProductType, ProductCategory
from django.contrib.auth.decorators import login_required

# views.py
@login_required
def edit_information_center(request, pk):
    item = get_object_or_404(InformationCenter, pk=pk)

    if request.method == 'POST':
        item.title = request.POST.get('title')
        item.remark = request.POST.get('remark')
        item.url = request.POST.get('url')
        item.added_date = request.POST.get('added_date')
        item.product_type_id = request.POST.get('product_type')
        item.product_category_id = request.POST.get('product_category')
        item.priority = request.POST.get('priority')
        item.language = request.POST.get('language')
        item.duration = request.POST.get('duration')
        item.host = request.POST.get('host')
        
        # Handle position update
        new_position = int(request.POST.get('position', 1))
        if new_position != item.position:
            # Get all items in the same category
            items_in_category = InformationCenter.objects.filter(
                product_category=item.product_category
            ).exclude(id=item.id).order_by('position')
            
            # Adjust positions if needed
            if new_position < 1:
                new_position = 1
            elif new_position > items_in_category.count() + 1:
                new_position = items_in_category.count() + 1
                
            # Update positions of other items
            for idx, other_item in enumerate(items_in_category, start=1):
                if idx >= new_position:
                    other_item.position = idx + 1
                    other_item.save()
            
            item.position = new_position

        if 'thumbnail' in request.FILES:
            item.thumbnail = request.FILES['thumbnail']

        item.save()
        return redirect('information_center')

    product_types = ProductType.objects.all()
    product_categories = ProductCategory.objects.all()

    return render(request, 'edit_information_center.html', {
        'item': item,
        'product_types': product_types,
        'product_categories': product_categories,
    })

@login_required
def delete_information_center(request, pk):
    item = get_object_or_404(InformationCenter, pk=pk)
    item.delete()
    return redirect('information_center')

# views.py (add these to your existing views)
from django.shortcuts import render, redirect, get_object_or_404
from .models import ProductType, ProductCategory

@login_required
def add_product_type(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        if name:
            ProductType.objects.create(name=name)
            return redirect('product_type_list')
    return render(request, 'add_product_type.html')

@login_required
def edit_product_type(request, id):
    product_type = get_object_or_404(ProductType, id=id)
    if request.method == 'POST':
        name = request.POST.get('name')
        if name:
            product_type.name = name
            product_type.save()
            return redirect('product_type_list')
    return render(request, 'edit_product_type.html', {'product_type': product_type})

@login_required
def delete_product_type(request, id):
    product_type = get_object_or_404(ProductType, id=id)
    product_type.delete()
    return redirect('product_type_list')

@login_required
def product_type_list(request):
    product_types = ProductType.objects.all()
    return render(request, 'product_type_list.html', {'product_types': product_types})

@login_required
def add_product_category(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        if name:
            ProductCategory.objects.create(name=name)
            return redirect('product_category_list')
    return render(request, 'add_product_category.html')
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from .models import ProductCategory

@login_required
def edit_product_category(request, id):
    product_category = get_object_or_404(ProductCategory, id=id)

    if request.method == 'POST':
        name = request.POST.get('name')
        if name:
            product_category.name = name
            product_category.save()
            return redirect('product_category_list')

    return render(request, 'edit_product_category.html', {
        'product_category': product_category
    })


@login_required
def delete_product_category(request, id):
    product_category = get_object_or_404(ProductCategory, id=id)
    product_category.delete()
    return redirect('product_category_list')

@login_required
def product_category_list(request):
    product_categories = ProductCategory.objects.all()
    return render(request, 'product_category_list.html', {'product_categories': product_categories})













from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import DailyTask
from django.utils import timezone

from app1.models import Project, ProjectWork, Employee


from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.core.paginator import Paginator
from .models import DailyTask
from app1.models import User  # Ensure you import User from the correct app
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from .models import DailyTask
from app1.models import User  # Ensure you import User from the correct app
from datetime import date
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from .models import DailyTask
from app1.models import User  # Ensure you import User from the correct app
from datetime import date, datetime, timedelta

@login_required
def daily_task_admin(request):
    status_filter = request.GET.get('status', '')
    user_filter = request.GET.get('user', '')
    project_filter = request.GET.get('project', '')  # Add project filter
    start_date = request.GET.get('start_date', date.today().strftime('%Y-%m-%d'))
    end_date = request.GET.get('end_date', date.today().strftime('%Y-%m-%d'))

    daily_tasks = DailyTask.objects.all().select_related('added_by').order_by('-created_at')

    if status_filter:
        daily_tasks = daily_tasks.filter(status=status_filter)
    if user_filter:
        daily_tasks = daily_tasks.filter(added_by_id=user_filter)
    if project_filter:
        daily_tasks = daily_tasks.filter(project=project_filter)  # Filter by project
    if start_date:
        start_datetime = datetime.strptime(start_date, '%Y-%m-%d')
        daily_tasks = daily_tasks.filter(created_at__gte=start_datetime)
    if end_date:
        end_datetime = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1) - timedelta(seconds=1)
        daily_tasks = daily_tasks.filter(created_at__lte=end_datetime)

    paginator = Paginator(daily_tasks, 15)
    page = request.GET.get('page', 1)
    try:
        page_obj = paginator.page(page)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    users = User.objects.all()
    projects = Project.objects.all()  # Fetch all projects

    return render(request, 'daily_task_admin.html', {
        'page_obj': page_obj,
        'users': users,
        'projects': projects,  # Pass projects to the template
        'status_filter': status_filter,
        'user_filter': user_filter,
        'project_filter': project_filter,  # Pass project filter value
        'start_date': start_date,
        'end_date': end_date
    })

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from .models import DailyTask
from django.views.decorators.http import require_POST

@login_required
def daily_task_user(request):
    daily_tasks = DailyTask.objects.filter(added_by=request.user).order_by('-created_at')

    paginator = Paginator(daily_tasks, 15)  # Change the number of rows per page to 15
    page = request.GET.get('page', 1)
    try:
        page_obj = paginator.page(page)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    return render(request, 'daily_task_user.html', {'page_obj': page_obj})

import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from .models import DailyTask
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt

from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from .models import DailyTask
from django.utils import timezone
from django.contrib.auth.decorators import login_required

@login_required
@require_POST
def stop_task(request):
    try:
        task_id = request.POST.get('task_id')
        if not task_id:
            return JsonResponse({'success': False, 'error': 'No task_id provided'})

        task = get_object_or_404(DailyTask, id=task_id, added_by=request.user)
        if task.status == 'in_progress':
            task.status = 'completed'
            duration_delta = timezone.now() - task.created_at
            hours, remainder = divmod(duration_delta.total_seconds(), 3600)
            minutes, seconds = divmod(remainder, 60)
            task.duration = f"{int(hours)}h {int(minutes)}m {int(seconds)}s"
            task.save()
            return JsonResponse({'success': True})
        else:
            return JsonResponse({'success': False, 'error': f'Task is not in progress. Current status: {task.status}'})

    except DailyTask.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Task not found or you do not have permission to stop this task'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})
    


    
@login_required
def add_daily_task(request):
    if request.method == 'POST':
        project = request.POST.get('project', '').strip()
        project_assigned = request.POST.get('project_assigned', '').strip()
        task = request.POST.get('task', '').strip()
        remark = request.POST.get('remark', '')

        # Validate fields
        if not project and not project_assigned:
            messages.error(request, 'Either "Project (Assigned)" or "Project (Manual Entry)" must be filled.')
            return redirect('add_daily_task')
        
        if not task:
            messages.error(request, 'Task field is required.')
            return redirect('add_daily_task')

        # Get current time
        current_time = timezone.now()

        # Get the user's last task
        last_task = DailyTask.objects.filter(added_by=request.user).order_by('-created_at').first()

        # Update previous task if it exists
        if last_task and last_task.status == 'in_progress':
            # Mark the last task as completed
            last_task.status = 'completed'
            
            # Calculate duration
            duration_delta = current_time - last_task.created_at
            hours, remainder = divmod(duration_delta.total_seconds(), 3600)
            minutes, seconds = divmod(remainder, 60)
            last_task.duration = f"{int(hours)}h {int(minutes)}m {int(seconds)}s"
            
            last_task.save()

        # Create new task
        DailyTask.objects.create(
            project=project or project_assigned,
            task=task,
            added_by=request.user,
            remark=remark,
            status='in_progress',  # New task is in progress
            duration=''  # Duration will be set when next task is added or stopped
        )

        messages.success(request, 'Task added successfully!')
        return redirect('daily_task_user')

    assigned_projects = []
    try:
        custom_user_id = request.session.get('custom_user_id')
        employee = Employee.objects.get(user_id=custom_user_id)
        assigned_projects = ProjectWork.objects.filter(members=employee).values_list('project__project_name', flat=True)
    except Employee.DoesNotExist:
        messages.warning(request, 'No employee record found for your account.')

    return render(request, 'add_daily_task.html', {
        'assigned_projects': assigned_projects
    })

@login_required
def edit_daily_task(request, task_id):
    task = get_object_or_404(DailyTask, id=task_id)
    if request.method == 'POST':
        project = request.POST.get('project', '')
        project_assigned = request.POST.get('project_assigned', '')
        task.task = request.POST['task']
        task.remark = request.POST.get('remark', '')  # Update the remark field

        if not project and not project_assigned:
            messages.error(request, 'Either "Project" or "Project (Assigned)" must be filled.')
            return redirect('edit_daily_task', task_id=task.id)

        task.project = project or project_assigned
        task.save()
        messages.success(request, 'Task updated successfully!')
        return redirect('daily_task_user')

    assigned_projects = []  # Fetch assigned projects for the current user
    try:
        custom_user_id = request.session.get('custom_user_id')
        employee = Employee.objects.get(user_id=custom_user_id)
        assigned_projects = ProjectWork.objects.filter(members=employee).values_list('project__project_name', flat=True)
    except Employee.DoesNotExist:
        messages.warning(request, 'No employee record found for your account.')

    return render(request, 'edit_daily_task.html', {'task': task, 'assigned_projects': assigned_projects})

@login_required
def delete_daily_task(request, task_id):
    task = get_object_or_404(DailyTask, id=task_id)
    task.delete()
    messages.success(request, 'Task deleted successfully!')
    return redirect('daily_task_user')




from .models import InformationCenter, ProductCategory

@login_required
def category_detail(request, category_id):
    category = get_object_or_404(ProductCategory, id=category_id)
    product_type_id = request.GET.get('product_type')
    
    items = InformationCenter.objects.filter(product_category_id=category_id)

    # Filter by product_type if provided
    if product_type_id:
        items = items.filter(product_type_id=product_type_id)
    
    items = items.order_by('product_type__name', '-added_date')
    product_types = ProductType.objects.all()
    
    return render(request, 'category_detail.html', {
        'category': category,
        'items': items,
        'product_types': product_types,
        'selected_product_type': product_type_id
    })





import requests
from django.shortcuts import render

import requests
from django.shortcuts import render
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
import requests
from django.shortcuts import render
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

import requests
from django.shortcuts import render
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
import re

def show_clients(request):
    api_url = "https://rrcpython.imcbs.com/api/clients/all"
    clients = []
    error_message = None
    
    try:
        response = requests.get(api_url, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        # Handle different response formats
        if isinstance(data, list):
            clients = data
        elif isinstance(data, dict):
            # Try common nested data patterns
            clients = data.get('data', data.get('clients', data.get('results', [])))
            
        print(f"Successfully fetched {len(clients)} clients")
        
    except requests.exceptions.Timeout:
        error_message = "API request timed out"
    except requests.exceptions.ConnectionError:
        error_message = "Could not connect to API"
    except requests.exceptions.HTTPError as e:
        error_message = f"HTTP Error: {e}"
    except Exception as e:
        error_message = f"Error fetching data: {str(e)}"
    
    # Search functionality
    search_query = request.GET.get('search', '').strip()
    original_count = len(clients)
    
    if search_query:
        filtered_clients = []
        search_terms = search_query.lower().split()  # Split multiple search terms
        
        for client in clients:
            # Search in ALL available fields
            searchable_fields = [
                str(client.get('name', '')),
                str(client.get('code', '')),
                str(client.get('mobile', '')),
                str(client.get('address', '')),
                str(client.get('branch', '')),
                str(client.get('district', '')),
                str(client.get('state', '')),
                str(client.get('software', '')),
                str(client.get('installationdate', '')),
                str(client.get('priorty', '')),
                str(client.get('directdealing', '')),
                str(client.get('rout', '')),
                str(client.get('amc', '')),
                str(client.get('amcamt', '')),
                str(client.get('accountcode', '')),
                str(client.get('address3', '')),
                str(client.get('lictype', '')),
                str(client.get('clients', '')),
                str(client.get('sp', '')),
                str(client.get('nature', '')),
            ]
            
            # Create a combined text for searching
            combined_text = ' '.join(searchable_fields).lower()
            
            # Check if ALL search terms are found (AND logic)
            # Change to any() for OR logic if preferred
            if all(term in combined_text for term in search_terms):
                filtered_clients.append(client)
        
        clients = filtered_clients
        print(f"Search '{search_query}' found {len(clients)} results out of {original_count} total clients")
    
    # Pagination logic
    paginator = Paginator(clients, 15)  # 15 clients per page
    page = request.GET.get('page')
    
    try:
        clients_page = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        clients_page = paginator.page(1)
    except EmptyPage:
        # If page is out of range, deliver last page of results.
        clients_page = paginator.page(paginator.num_pages)
    
    return render(request, 'clients_table.html', {
        'clients': clients_page,
        'error_message': error_message,
        'total_clients': original_count,
        'filtered_count': len(clients),
        'search_query': search_query,
        'search_terms': search_query.lower().split() if search_query else []
    })










# views.py

# views.py

# views.py

from django.shortcuts import render
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from .models import InformationCenter
from django.utils import timezone
from datetime import datetime

@login_required
def information_center_table(request):
    # Get search parameters from request
    search_query = request.GET.get('search', '')
    start_date_str = request.GET.get('start_date', '')
    end_date_str = request.GET.get('end_date', '')

    # Start with all information items
    information_items = InformationCenter.objects.all().order_by('-added_date')

    # Apply search filter if provided
    if search_query:
        information_items = information_items.filter(title__icontains=search_query)

    # Apply date filter if provided
    if start_date_str:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        information_items = information_items.filter(added_date__gte=start_date)
    
    if end_date_str:
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        information_items = information_items.filter(added_date__lte=end_date)

    # Set up pagination
    paginator = Paginator(information_items, 15)  # 15 items per page
    page_number = request.GET.get('page', 1)

    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    return render(request, 'information_center_table.html', {
        'page_obj': page_obj,
        'search_query': search_query,
        'start_date': start_date_str,  # Pass the original string, not the date object
        'end_date': end_date_str,      # Pass the original string, not the date object
    })




# views.py
from django.shortcuts import render, redirect, get_object_or_404
from .models import Department,JobRoleDescription

def all_department(request):
    departments = Department.objects.all()
    return render(request, 'all_department.html', {'departments': departments})

def add_department(request):
    if request.method == 'POST':
        name = request.POST['name']
        Department.objects.create(name=name)
        return redirect('all_department')
    return render(request, 'add_department.html')

def edit_department(request, id):
    department = get_object_or_404(Department, id=id)
    if request.method == 'POST':
        department.name = request.POST['name']
        department.save()
        return redirect('all_department')
    return render(request, 'edit_department.html', {'department': department})



def delete_department(request, id):
    dept = get_object_or_404(Department, id=id)
    dept.delete()
    return redirect('all_department')


from django.shortcuts import render, redirect, get_object_or_404
from .models import JobRole, Department

@login_required
def job_roles(request):
    # Get the custom user ID from session
    custom_user_id = request.session.get('custom_user_id')
    
    # If no custom_user_id in session, try to get from request.user
    if not custom_user_id:
        # Fallback: try to find user by username if using Django's built-in auth
        try:
            # Assuming you have a way to map Django user to your custom User model
            # You might need to adjust this based on your authentication setup
            custom_user = User.objects.get(userid=request.user.username)
        except User.DoesNotExist:
            # If still no user found, redirect to login or show error
            from django.contrib import messages
            messages.error(request, "User session not found. Please login again.")
            return redirect('login')
    else:
        # Fetch the user object using session ID
        try:
            custom_user = User.objects.get(id=custom_user_id)
        except User.DoesNotExist:
            from django.contrib import messages
            messages.error(request, "User not found. Please login again.")
            return redirect('login')
    
    # Check if user is superuser (admin_level or 4level)
    if custom_user.user_level in ['admin_level', '4level']:
        # Superuser can see all job roles
        roles = JobRole.objects.select_related('department').all()
    else:
        # Regular users can only see their assigned job role
        if custom_user.job_role:
            roles = JobRole.objects.select_related('department').filter(id=custom_user.job_role.id)
        else:
            # If user has no job role assigned, show empty queryset
            roles = JobRole.objects.none()
    
    # Pass custom_user instead of user to avoid overriding request.user
    return render(request, 'job_roles.html', {'roles': roles, 'custom_user': custom_user})

# views.py

def add_job_role(request):
    departments = Department.objects.all()
    if request.method == 'POST':
        dept_id = request.POST.get('department')
        title = request.POST.get('title')
        job_role = JobRole.objects.create(department_id=dept_id, title=title)
        
        # Handle multiple headings and descriptions
        headings = request.POST.getlist('heading')
        descriptions = request.POST.getlist('description')
        
        for heading, description in zip(headings, descriptions):
            if heading or description:
                JobRoleDescription.objects.create(job_role=job_role, heading=heading, description=description)
        
        return redirect('job_roles')
    return render(request, 'add_job_role.html', {'departments': departments})

def edit_job_role(request, id):
    role = get_object_or_404(JobRole, id=id)
    departments = Department.objects.all()
    if request.method == 'POST':
        role.department_id = request.POST.get('department')
        role.title = request.POST.get('title')
        role.save()
        
        # Clear existing descriptions
        JobRoleDescription.objects.filter(job_role=role).delete()
        
        # Handle multiple headings and descriptions
        headings = request.POST.getlist('heading')
        descriptions = request.POST.getlist('description')
        
        for heading, description in zip(headings, descriptions):
            if heading or description:
                JobRoleDescription.objects.create(job_role=role, heading=heading, description=description)
        
        return redirect('job_roles')
    return render(request, 'add_job_role.html', {'departments': departments, 'role': role})

def delete_job_role(request, id):
    role = get_object_or_404(JobRole, id=id)
    role.delete()
    return redirect('job_roles')





