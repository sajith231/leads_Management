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







from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from datetime import datetime
import requests
from django.shortcuts import render
from django.shortcuts import render
import requests
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.utils.dateparse import parse_date
from app1.models import User, Branch  # Import User and Branch from app1
from datetime import datetime, timedelta
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.shortcuts import render
from django.contrib.auth import get_user_model
import requests
# NOTE: No direct import of app1.models.User here; we use get_user_model()
# to work whether you're on the default auth.User or a custom user.

@login_required
def show_clients(request):
    api_url = "https://accmaster.imcbs.com/api/sync/rrc-clients/"
    clients = []
    error_message = None

    # ------------------------------------------------------------------
    # 1.  Determine the logged-in user's branch (fallback to None)
    #     - Works whether your user model has `userid` or only `username`
    # ------------------------------------------------------------------
    UserModel = get_user_model()
    custom_user = (
        UserModel.objects.filter(userid=request.user.username).first()  # custom field case
        or UserModel.objects.filter(username=request.user.username).first()  # default auth case
        or UserModel.objects.filter(id=request.user.id).first()  # absolute fallback
    )
    user_branch = (
        getattr(getattr(custom_user, "branch", None), "name", None)
        if custom_user else None
    )

    # ------------------------------------------------------------------
    # 2.  Fetch external data (same as before)
    # ------------------------------------------------------------------
    try:
        response = requests.get(api_url, timeout=30)
        response.raise_for_status()
        data = response.json()
        clients = data if isinstance(data, list) else \
                  data.get('data', data.get('clients', data.get('results', [])))
    except requests.exceptions.RequestException as e:
        error_message = str(e)
    except Exception:
        error_message = "Could not load client data."

    # ------------------------------------------------------------------
    # 3.  Format / enrich data
    # ------------------------------------------------------------------
    def fmt_date(d):
        if not d or str(d).strip() in {"", "-"}:
            return "-"
        for f in ('%Y-%m-%d', '%d-%m-%Y', '%m/%d/%Y', '%d/%m/%Y'):
            try:
                return datetime.strptime(str(d).strip(), f).strftime('%d-%m-%Y')
            except ValueError:
                continue
        return str(d).strip()

    for c in clients:
        c['formatted_installationdate'] = fmt_date(c.get('installationdate'))

    # ------------------------------------------------------------------
    # 4.  Build filter choices
    # ------------------------------------------------------------------
    unique_branches   = sorted({c.get('branch', '')         for c in clients if c.get('branch')})
    unique_software   = sorted({c.get('software', '')       for c in clients if c.get('software')})
    unique_natures    = sorted({c.get('nature', '')         for c in clients if c.get('nature')})
    unique_amc_labels = sorted({c.get('amc_label', '')      for c in clients if c.get('amc_label')})
    unique_sp         = sorted({c.get('sp', '')             for c in clients if c.get('sp')})
    unique_lic_types  = sorted({c.get('lictype_label', '')  for c in clients if c.get('lictype_label')})

    # ------------------------------------------------------------------
    # 5.  Read filter parameters with automatic branch restriction
    # ------------------------------------------------------------------
    search_query = request.GET.get('search', '').strip()

    # Auto-apply branch filter for non-IMC/SYSMAC users
    if user_branch and user_branch not in ['IMC', 'SYSMAC']:
        # For restricted users, always use their branch (ignore URL parameter)
        selected_branch = user_branch
    else:
        # For IMC/SYSMAC users, use the URL parameter or empty
        selected_branch = request.GET.get('branch', '')

    selected_software = request.GET.get('software', '')
    selected_nature   = request.GET.get('nature', '')
    selected_amc      = request.GET.get('amc', '')
    selected_sp       = request.GET.get('sp', '')
    selected_lictype  = request.GET.get('lictype', '')
    selected_direct   = request.GET.get('direct_dealing', 'Yes')   # default
    try:
        selected_rows = int(request.GET.get('rows', 15))
    except (TypeError, ValueError):
        selected_rows = 15

    # ------------------------------------------------------------------
    # 6.  Apply filters
    # ------------------------------------------------------------------
    filtered = clients
    if search_query:
        terms = search_query.lower().split()
        filtered = [
            c for c in filtered
            if all(t in ' '.join([str(v) for v in c.values()]).lower() for t in terms)
        ]

    for key, val, field in (
        ('branch',   selected_branch,   'branch'),
        ('software', selected_software, 'software'),
        ('nature',   selected_nature,   'nature'),
        ('amc',      selected_amc,      'amc_label'),
        ('sp',       selected_sp,       'sp'),
        ('lictype',  selected_lictype,  'lictype_label'),
    ):
        if val:
            filtered = [c for c in filtered if str(c.get(field, '')) == val]

    if selected_direct != 'All':
        filtered = [
            c for c in filtered
            if str(c.get('directdealing_label', '')).lower() == selected_direct.lower()
        ]

    # ------------------------------------------------------------------
    # 7.  Pagination
    # ------------------------------------------------------------------
    paginator = Paginator(filtered, selected_rows)
    page = request.GET.get('page', 1)
    try:
        clients_page = paginator.page(page)
    except PageNotAnInteger:
        clients_page = paginator.page(1)
    except EmptyPage:
        clients_page = paginator.page(paginator.num_pages)

    # ------------------------------------------------------------------
    # 8.  Template context
    # ------------------------------------------------------------------
    return render(request, 'clients_table.html', {
        'clients': clients_page,
        'error_message': error_message,
        'total_clients': len(clients),
        'filtered_count': len(filtered),
        'search_query': search_query,
        'search_terms': search_query.lower().split() if search_query else [],
        'unique_branches': unique_branches,
        'unique_software': unique_software,
        'unique_natures': unique_natures,
        'unique_amc_labels': unique_amc_labels,
        'unique_sp': unique_sp,
        'unique_lic_types': unique_lic_types,
        'rows_options': [10, 20, 50, 100],
        'selected_rows': selected_rows,
        'selected_direct_dealing': selected_direct,
        'user_branch': user_branch,          # for template
        'selected_branch': selected_branch,  # for template
        'is_branch_restricted': bool(user_branch and user_branch not in ['IMC', 'SYSMAC']),
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
# views.py - replace your existing job_roles function with this
from django.apps import apps
from django.contrib import messages
from django.shortcuts import redirect

@login_required
def job_roles(request):
    AppUser = apps.get_model('app1', 'User')   # always the custom user model
    JobRole = apps.get_model('app2', 'JobRole')
    Department = apps.get_model('app2', 'Department')

    # prefer explicit custom_user id stored in session (your code uses this in places)
    custom_user = None
    custom_user_id = request.session.get('custom_user_id')

    if custom_user_id:
        try:
            custom_user = AppUser.objects.get(id=custom_user_id)
        except AppUser.DoesNotExist:
            custom_user = None

    # If we still don't have custom_user, try several sensible fallbacks.
    if not custom_user:
        # 1) try by custom userid field (app1.User.userid)
        custom_user = AppUser.objects.filter(userid=request.user.username).first()

    if not custom_user:
        # 2) try by username field (in case you have username column on app1.User)
        custom_user = AppUser.objects.filter(username=getattr(request.user, 'username', None)).first()

    if not custom_user:
        # 3) try by id matching request.user.id
        custom_user = AppUser.objects.filter(id=getattr(request.user, 'id', None)).first()

    # If still None, create a safe shim object so templates won't crash.
    if not custom_user:
        class _Shim:
            pass
        custom_user = _Shim()
        # if request.user is a Django superuser, give the shim admin privileges so page shows all roles
        if getattr(request.user, 'is_superuser', False):
            custom_user.user_level = 'admin_level'
            # also indicate superuser in template via 'is_superuser' property if useful:
            custom_user.is_superuser = True
        else:
            custom_user.user_level = 'normal'
            custom_user.is_superuser = False

    # Now determine which roles to show
    if getattr(custom_user, 'user_level', None) in ['admin_level', '4level'] or getattr(request.user, 'is_superuser', False):
        # show all roles to admins / superusers
        roles = JobRole.objects.select_related('department').all().order_by('department__name', 'title')
    else:
        # regular users see only their assigned job role (if any)
        if getattr(custom_user, 'job_role', None):
            roles = JobRole.objects.select_related('department').filter(id=custom_user.job_role.id)
        else:
            roles = JobRole.objects.none()

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





from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from app1.models import BusinessType
from .models import Customer

from django.shortcuts import render
from .models import Customer

from django.core.paginator import Paginator
from django.shortcuts import render
from django.db import models
from .models import Customer

def all_customers(request):
    search_query = request.GET.get('q', '').strip()

    if search_query:
        customers_list = Customer.objects.filter(
            models.Q(customer_name__icontains=search_query) |
            models.Q(firm_name__icontains=search_query)
        ).select_related('business_type').order_by('-created_at')
    else:
        customers_list = Customer.objects.all().select_related('business_type').order_by('-created_at')

    paginator = Paginator(customers_list, 15)
    page_number = request.GET.get('page')
    customers = paginator.get_page(page_number)

    return render(request, 'all_customers_table.html', {'customers': customers})

def add_customer(request):
    business_types = BusinessType.objects.all()
    
    if request.method == 'POST':
        # Create new customer from POST data
        customer = Customer(
            customer_name=request.POST.get('customerName'),
            firm_name=request.POST.get('firmName'),
            place=request.POST.get('place'),
            district=request.POST.get('district'),
            state=request.POST.get('state'),
            country=request.POST.get('country'),
            phone=request.POST.get('phone'),
            business_type_id=request.POST.get('businessType'),
            contact_person=request.POST.get('contactPerson'),
            phone1=request.POST.get('phone1'),
            phone2=request.POST.get('phone2'),
            email=request.POST.get('email')
        )
        customer.save()
        return redirect(reverse('all_customers'))
    
    return render(request, 'add_customer.html', {'business_types': business_types})

from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from app1.models import BusinessType
from .models import Customer

def edit_customer(request, id):
    customer = get_object_or_404(Customer, id=id)
    business_types = BusinessType.objects.all()
    districts = [
        'Alappuzha', 'Ernakulam', 'Idukki', 'Kannur', 'Kasaragod', 
        'Kollam', 'Kottayam', 'Kozhikode', 'Malappuram', 'Palakkad',
        'Pathanamthitta', 'Thiruvananthapuram', 'Thrissur', 'Wayanad'
    ]
    
    if request.method == 'POST':
        # Update customer from POST data
        customer.customer_name = request.POST.get('customerName')
        customer.firm_name = request.POST.get('firmName')
        customer.place = request.POST.get('place')
        customer.district = request.POST.get('district')
        customer.state = request.POST.get('state')
        customer.country = request.POST.get('country')
        customer.phone = request.POST.get('phone')
        customer.business_type_id = request.POST.get('businessType')
        customer.contact_person = request.POST.get('contactPerson')
        customer.phone1 = request.POST.get('phone1')
        customer.phone2 = request.POST.get('phone2')
        customer.email = request.POST.get('email')
        customer.save()
        return redirect(reverse('all_customers'))
    
    return render(request, 'edit_customer.html', {  # Corrected template path
        'customer': customer,
        'business_types': business_types,
        'districts': districts
    })

def delete_customer(request, id):
    customer = get_object_or_404(Customer, id=id)
    customer.delete()
    return redirect(reverse('all_customers'))





from django.shortcuts import render
from django.core.paginator import Paginator
from django.db import models
from .models import SocialMediaProject

def socialmedia_all_projects(request):
    search_query = request.GET.get('q', '').strip()

    if search_query:
        projects_list = SocialMediaProject.objects.filter(
            models.Q(project_name__icontains=search_query) |
            models.Q(customer__customer_name__icontains=search_query)
        ).select_related('customer').order_by('-id')
    else:
        projects_list = SocialMediaProject.objects.all().select_related('customer').order_by('-id')

    paginator = Paginator(projects_list, 15)  # Show 15 projects per page
    page_number = request.GET.get('page')
    projects = paginator.get_page(page_number)

    return render(request, 'socialmedia_all_projects.html', {'projects': projects})

def socialmedia_add_project(request):
    customers = Customer.objects.all()
    
    if request.method == 'POST':
        project = SocialMediaProject(
            project_name=request.POST.get('projectName'),
            customer_id=request.POST.get('customerName'),
            project_description=request.POST.get('projectDescription'),
            deadline=request.POST.get('deadline')
        )
        project.save()
        return redirect(reverse('socialmedia_all_projects'))
    
    return render(request, 'add_socialmedia_project.html', {'customers': customers})

def socialmedia_edit_project(request, id):
    project = get_object_or_404(SocialMediaProject, id=id)
    customers = Customer.objects.all()
    
    if request.method == 'POST':
        project.project_name = request.POST.get('projectName')
        project.customer_id = request.POST.get('customerName')
        project.project_description = request.POST.get('projectDescription')
        project.deadline = request.POST.get('deadline')
        project.save()
        return redirect(reverse('socialmedia_all_projects'))
    
    return render(request, 'edit_socialmedia_project.html', {'project': project, 'customers': customers})

def socialmedia_delete_project(request, id):
    project = get_object_or_404(SocialMediaProject, id=id)
    project.delete()
    return redirect(reverse('socialmedia_all_projects'))







from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from .models import Task, SocialMediaProject

def socialmedia_all_tasks(request):
    tasks = Task.objects.all().order_by('-created_at')
    return render(request, 'socialmedia_all_tasks.html', {'tasks': tasks})

def socialmedia_add_task(request):
    if request.method == 'POST':
        task = Task(
            task_name=request.POST.get('taskName')
        )
        task.save()
        return redirect(reverse('socialmedia_all_tasks'))
    
    return render(request, 'add_socialmedia_task.html')

def socialmedia_edit_task(request, id):
    task = get_object_or_404(Task, id=id)
    
    if request.method == 'POST':
        task.task_name = request.POST.get('taskName')
        task.save()
        return redirect(reverse('socialmedia_all_tasks'))
    
    return render(request, 'edit_socialmedia_task.html', {'task': task})

def socialmedia_delete_task(request, id):
    task = get_object_or_404(Task, id=id)
    task.delete()
    return redirect(reverse('socialmedia_all_tasks'))



from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.apps import apps
from .models import SocialMediaProject, Task, SocialMediaProjectAssignment

# Get User model from app1 to avoid circular import
def get_user_model():
    return apps.get_model('app1', 'User')



from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from .models import SocialMediaProjectAssignment
# NOTE: make sure get_status_duration is imported/defined somewhere
# from .utils import get_status_duration

@login_required
def socialmedia_project_assignments(request):
    # 1. Grab the filter parameter – default to 'in_progress'
    status_filter = request.GET.get('status', 'in_progress')

    # 2. Base queryset
    assignments_qs = SocialMediaProjectAssignment.objects.all() \
                      .select_related('project', 'task') \
                      .prefetch_related('assigned_to', 'status_history')

    # 3. Apply status filter
    if status_filter == 'pending':
        assignments_qs = assignments_qs.filter(status='pending')
    elif status_filter == 'in_progress':
        assignments_qs = assignments_qs.filter(status__in=['pending', 'started'])
    elif status_filter == 'completed':
        assignments_qs = assignments_qs.filter(status='completed')

    # 4. Pagination
    paginator = Paginator(assignments_qs, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # 5. Build durations
    assignment_durations = []
    for assignment in page_obj:
        history = list(assignment.status_history.all())
        duration_started_completed = get_status_duration(history, 'started', 'completed')
        assignment_durations.append({
            'assignment': assignment,
            'duration_started_completed': duration_started_completed,
        })

    # 6. Return to template
    return render(request, 'socialmedia_project_assignments.html', {
        'assignments': page_obj,
        'assignment_durations': assignment_durations,
        'status_filter': status_filter,   # so the dropdown can remember selection
    })


# Update the user_socialmedia_project_assignments view:
@login_required
def user_socialmedia_project_assignments(request):
    try:
        User = apps.get_model('app1', 'User')
        custom_user = User.objects.get(userid=request.user.username)
        assignments = SocialMediaProjectAssignment.objects.filter(
            assigned_to=custom_user
        ).select_related('project', 'task', 'project__customer').prefetch_related('status_history').order_by('-created_at')
    except User.DoesNotExist:
        assignments = SocialMediaProjectAssignment.objects.none()

    today = datetime.now().date()
    week_from_now = today + timedelta(days=7)

    processed_assignments = []
    for assignment in assignments:
        deadline_status = None
        deadline_date = None

        if assignment.deadline:
            deadline_date = assignment.deadline
        elif assignment.project.deadline:
            deadline_date = assignment.project.deadline

        if deadline_date:
            if deadline_date < today:
                deadline_status = 'passed'
            elif deadline_date <= week_from_now:
                deadline_status = 'approaching'

        # Only get started to completed duration
        history = list(assignment.status_history.all())
        duration_started_completed = get_status_duration(history, 'started', 'completed')

        processed_assignments.append({
            'assignment': assignment,
            'deadline_status': deadline_status,
            'effective_deadline': deadline_date,
            'duration_started_completed': duration_started_completed,
        })

    paginator = Paginator(processed_assignments, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'assignments': page_obj,
        'processed_assignments': page_obj,
        'today': today,
        'total_assignments': len(processed_assignments),
    }
    return render(request, 'user_socialmedia_project_assignments.html', context)
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.apps import apps
from .models import SocialMediaProject, Task, SocialMediaProjectAssignment

from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.apps import apps
from .models import SocialMediaProject, Task, SocialMediaProjectAssignment

@login_required
def add_assign_socialmedia_project(request):
    """
    Create a new SocialMediaProjectAssignment.
    Uses existing tasks from dropdown selection only.
    Only shows users with 'Social Media and Digital Marketing' job role.
    """
    projects = SocialMediaProject.objects.all()
    tasks = Task.objects.all()
    User = apps.get_model('app1', 'User')
    
    # Filter users by job role - only Social Media and Digital Marketing
    users = User.objects.filter(
        job_role__title='Social Media and Digital Marketing',
        status='active'  # Also filter for active users only
    ).select_related('job_role')

    if request.method == 'POST':
        project_id = request.POST.get('project')
        task_id = request.POST.get('task')
        assigned_to_ids = request.POST.getlist('assigned_to')
        deadline = request.POST.get('deadline') or None
        remark = request.POST.get('remark', '').strip()

        # --- basic validation ---
        try:
            project = get_object_or_404(SocialMediaProject, id=project_id)
            task = get_object_or_404(Task, id=int(task_id))
        except ValueError:
            return render(request, 'add_assign_socialmedia_project.html', {
                'projects': projects,
                'tasks': tasks,
                'users': users,
                'error': 'Invalid project or task selection.'
            })

        # --- create ---
        assignment = SocialMediaProjectAssignment.objects.create(
            project=project,
            task=task,
            deadline=deadline,
            remark=remark
        )
        assigned_users = User.objects.filter(id__in=assigned_to_ids)
        assignment.assigned_to.set(assigned_users)

        return redirect(reverse('socialmedia_project_assignments'))

    return render(request, 'add_assign_socialmedia_project.html', {
        'projects': projects,
        'tasks': tasks,
        'users': users
    })


@login_required
def edit_assign_socialmedia_project(request, id):
    """
    Edit an existing SocialMediaProjectAssignment.
    Uses existing tasks from dropdown selection only.
    Only shows users with 'Social Media and Digital Marketing' job role.
    """
    assignment = get_object_or_404(SocialMediaProjectAssignment, id=id)
    projects = SocialMediaProject.objects.all()
    tasks = Task.objects.all()
    User = apps.get_model('app1', 'User')
    
    # Filter users by job role - only Social Media and Digital Marketing
    users = User.objects.filter(
        job_role__title='Social Media and Digital Marketing',
        status='active'  # Also filter for active users only
    ).select_related('job_role')

    if request.method == 'POST':
        project_id = request.POST.get('project')
        task_id = request.POST.get('task')
        assigned_to_ids = request.POST.getlist('assigned_to')
        deadline = request.POST.get('deadline') or None
        remark = request.POST.get('remark', '').strip()

        # --- basic validation ---
        try:
            project = get_object_or_404(SocialMediaProject, id=project_id)
            task = get_object_or_404(Task, id=int(task_id))
        except ValueError:
            return render(request, 'edit_assign_socialmedia_project.html', {
                'assignment': assignment,
                'projects': projects,
                'tasks': tasks,
                'users': users,
                'error': 'Invalid project or task selection.'
            })

        # --- update ---
        assignment.project = project
        assignment.task = task
        assignment.deadline = deadline
        assignment.remark = remark
        assignment.assigned_to.set(User.objects.filter(id__in=assigned_to_ids))
        assignment.save()

        return redirect(reverse('socialmedia_project_assignments'))

    return render(request, 'edit_assign_socialmedia_project.html', {
        'assignment': assignment,
        'projects': projects,
        'tasks': tasks,
        'users': users
    })

@login_required
def delete_assign_socialmedia_project(request, id):
    assignment = get_object_or_404(SocialMediaProjectAssignment, id=id)
    assignment.delete()
    return redirect(reverse('socialmedia_project_assignments'))





from datetime import datetime, timedelta
from django.apps import apps
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from .models import SocialMediaProjectAssignment

# Add this new view to your existing views.py

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import json
from .models import AssignmentStatusHistory

@login_required
@csrf_exempt
@require_POST
def update_assignment_status(request):
    try:
        data = json.loads(request.body)
        assignment_id = data.get('assignment_id')
        new_status = data.get('status')

        if not assignment_id or not new_status:
            return JsonResponse({'success': False, 'error': 'Missing required data'})

        assignment = get_object_or_404(SocialMediaProjectAssignment, id=assignment_id)
        User = get_user_model()
        custom_user = User.objects.get(userid=request.user.username)
        if not assignment.assigned_to.filter(id=custom_user.id).exists():
            return JsonResponse({'success': False, 'error': 'You are not assigned to this project'})

        valid_statuses = ['pending', 'started', 'completed', 'hold']
        if new_status not in valid_statuses:
            return JsonResponse({'success': False, 'error': 'Invalid status'})

        # Only add to history if status is actually changing
        if assignment.status != new_status:
            AssignmentStatusHistory.objects.create(
                assignment=assignment,
                status=new_status,
                changed_by=request.user
            )
            assignment.status = new_status
            assignment.save()

        return JsonResponse({
            'success': True,
            'message': 'Status updated successfully',
            'new_status': assignment.get_status_display(),
            'status_class': assignment.get_status_display_class()
        })

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})






# Update your existing user_socialmedia_project_assignments view
from datetime import datetime, timedelta
from django.apps import apps
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import render
from django.utils.timesince import timesince
from .models import SocialMediaProjectAssignment, AssignmentStatusHistory

def get_status_duration(history, start_status, end_status):
    """Get duration between start status and end status"""
    start_time = None
    end_time = None
    
    # Find the first 'started' entry
    for entry in history:
        if entry.status == start_status and start_time is None:
            start_time = entry.changed_at
    
    # Find the last 'completed' entry after start
    for entry in reversed(history):
        if entry.status == end_status and start_time and entry.changed_at > start_time:
            end_time = entry.changed_at
            break
            
    if start_time and end_time:
        return timesince(start_time, end_time)
    elif start_time and not end_time:
        # If started but not completed yet
        return f"{timesince(start_time)}"
    return None

@login_required
def user_socialmedia_project_assignments(request):
    try:
        User = apps.get_model('app1', 'User')
        custom_user = User.objects.get(userid=request.user.username)
        assignments = SocialMediaProjectAssignment.objects.filter(
            assigned_to=custom_user
        ).select_related('project', 'task', 'project__customer').prefetch_related('status_history').order_by('-created_at')
    except User.DoesNotExist:
        assignments = SocialMediaProjectAssignment.objects.none()

    today = datetime.now().date()
    week_from_now = today + timedelta(days=7)

    processed_assignments = []
    for assignment in assignments:
        deadline_status = None
        deadline_date = None

        if assignment.deadline:
            deadline_date = assignment.deadline
        elif assignment.project.deadline:
            deadline_date = assignment.project.deadline

        if deadline_date:
            if deadline_date < today:
                deadline_status = 'passed'
            elif deadline_date <= week_from_now:
                deadline_status = 'approaching'

        # Only get started to completed duration
        history = list(assignment.status_history.all())
        duration_started_completed = get_status_duration(history, 'started', 'completed')

        processed_assignments.append({
            'assignment': assignment,
            'deadline_status': deadline_status,
            'effective_deadline': deadline_date,
            'duration_started_completed': duration_started_completed,
        })

    paginator = Paginator(processed_assignments, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'assignments': page_obj,
        'processed_assignments': page_obj,
        'today': today,
        'total_assignments': len(processed_assignments),
    }
    return render(request, 'user_socialmedia_project_assignments.html', context)



import requests
import urllib.parse
from datetime import datetime
import logging
from django.views.decorators.csrf import csrf_exempt
from django.utils.dateparse import parse_date
from datetime import date

logger = logging.getLogger(__name__)

def get_display_name(user):
    """
    Return a friendly display name for a Django user object.
    Falls back to username or 'System' if user not authenticated.
    """
    if not user or not getattr(user, 'is_authenticated', False):
        return "System"
    try:
        full = (user.get_full_name() or "").strip()
        if full:
            return full
    except Exception:
        pass
    # first + last name fallback
    first = getattr(user, 'first_name', '') or ''
    last = getattr(user, 'last_name', '') or ''
    if first.strip():
        return f"{first.strip()} {last.strip()}".strip()
    return getattr(user, 'username', 'System')


def send_whatsapp_notification(name, installation_date, software_amount, created_by=None):
    """
    Send WhatsApp notification when a new feeder is created.
    Args:
        name (str): Feeder name
        installation_date (date | None): Installation date
        software_amount (str|float|None): Software amount
        created_by (str|None): Display name of the user who created the feeder
    Returns:
        bool: True if message sent successfully, False otherwise
    """
    # WhatsApp API configuration
    WHATSAPP_API_URL = "https://app.dxing.in/api/send/whatsapp"
    SECRET = "7b8ae820ecb39f8d173d57b51e1fce4c023e359e"
    ACCOUNT = "1756959119812b4ba287f5ee0bc9d43bbf5bbe87fb68b9118fcf1af"
    RECIPIENT = "9946545535"  # keep existing recipient(s) or parameterize as needed

    try:
        # Format the installation date to DD-MM-YYYY format
        if installation_date:
            try:
                formatted_date = installation_date.strftime("%d-%m-%Y")
            except Exception:
                # fallback if installation_date is a string
                try:
                    parsed = datetime.fromisoformat(str(installation_date))
                    formatted_date = parsed.strftime("%d-%m-%Y")
                except Exception:
                    formatted_date = str(installation_date)
        else:
            formatted_date = "Not specified"

        # Format software amount safely
        try:
            amt_val = float(software_amount) if software_amount not in (None, '') else 0.0
            formatted_amount = f"₹{amt_val:,.2f}"
        except Exception:
            formatted_amount = str(software_amount or "₹0.00")

        created_by_text = f"\nCreated By: {created_by}" if created_by else "\nCreated By: -"

        # Create the message (includes created_by)
        message = (
            f"🏪 NEW FEEDER CREATED\n\n"
            f"Shop Name: {name}\n"
            f"Installation Date: {formatted_date}\n"
            f"Software Amount: {formatted_amount}\n"
            f"{created_by_text}\n\n"
            f"Created at: {datetime.now().strftime('%d-%m-%Y %H:%M')}"
        )

        # URL encode the message
        encoded_message = urllib.parse.quote(message)

        # Prepare the API URL
        api_url = f"{WHATSAPP_API_URL}?secret={SECRET}&account={ACCOUNT}&recipient={RECIPIENT}&type=text&message={encoded_message}&priority=1"

        # Send the request
        response = requests.get(api_url, timeout=10)

        if response.status_code == 200:
            logger.info(f"WhatsApp notification sent successfully for feeder: {name}")
            return True
        else:
            logger.error(f"Failed to send WhatsApp notification. Status: {response.status_code}, Response: {response.text}")
            return False

    except requests.exceptions.RequestException as e:
        logger.error(f"Network error while sending WhatsApp notification: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error while sending WhatsApp notification: {str(e)}")
        return False

# Modified feeder view with created_by included in message
@csrf_exempt
def feeder(request):
    # Ensure we resolve the correct custom user model (app1.User) even if "User" is shadowed elsewhere
    from django.apps import apps
    AppUser = apps.get_model('app1', 'User')

    business_types = BusinessType.objects.all()
    branches = Branch.objects.all()

    # Get the logged-in user's branch - ALL users now see only their branch
    try:
        custom_user = AppUser.objects.get(userid=request.user.username)
        user_branch = custom_user.branch if custom_user.branch else None
        user_branch_id = custom_user.branch.id if custom_user.branch else None
    except AppUser.DoesNotExist:
        user_branch = None
        user_branch_id = None

    # All users are now branch restricted (removed IMC/SYSMAC exception)
    is_branch_restricted = user_branch is not None

    if request.method == 'POST':
        name = request.POST.get('name')
        address = request.POST.get('address')
        location = request.POST.get('location')
        area = request.POST.get('area')
        district = request.POST.get('district')
        state = request.POST.get('state')
        contact_person = request.POST.get('contact_person')
        contact_number = request.POST.get('contact_number')
        email = request.POST.get('email')
        reputed_person_name = request.POST.get('reputed_person_name', '')
        reputed_person_number = request.POST.get('reputed_person_number', '')
        software = request.POST.get('software')
        nature = request.POST.get('nature')

        # All users now use their own branch only
        branch_id = user_branch_id  # Always use the user's branch

        no_of_system = request.POST.get('no_of_system')
        pincode = request.POST.get('pincode')
        country = request.POST.get('country')
        installation_date = request.POST.get('installation_date')
        remarks = request.POST.get('remarks', '')
        software_amount = request.POST.get('software_amount') or 0
        module_charges = request.POST.get('total_cost') or 0

        modules = request.POST.getlist('modules')
        more_modules = request.POST.getlist('more_modules')

        module_prices = {}
        for module in more_modules:
            price_key = f"price_{module}"
            price_value = request.POST.get(price_key)
            if price_value:
                try:
                    module_prices[module] = float(price_value)
                except ValueError:
                    pass

        # Parse installation date
        parsed_installation_date = None
        if installation_date:
            try:
                parsed_installation_date = parse_date(installation_date)
            except (ValueError, TypeError):
                parsed_installation_date = None

        feeder_obj = Feeder(
            name=name,
            address=address,
            location=location,
            area=area,
            district=district,
            state=state,
            contact_person=contact_person,
            contact_number=contact_number,
            email=email,
            reputed_person_name=reputed_person_name,
            reputed_person_number=reputed_person_number,
            software=software,
            nature=nature,
            branch_id=branch_id,  # Use the user's branch
            no_of_system=no_of_system,
            pincode=pincode,
            country=country,
            installation_date=parsed_installation_date,
            remarks=remarks,
            software_amount=software_amount,
            module_charges=module_charges,
            modules=', '.join(modules),
            more_modules=', '.join(more_modules),
            module_prices=module_prices
        )

        try:
            feeder_obj.save()

            # Determine creator display name
            created_by_name = get_display_name(getattr(request, 'user', None))

            # Send WhatsApp notification after successful save (includes creator)
            try:
                send_whatsapp_notification(
                    name=name,
                    installation_date=parsed_installation_date,
                    software_amount=software_amount,
                    created_by=created_by_name
                )
                logger.info(f"WhatsApp notification attempted for feeder: {name} (created by {created_by_name})")
            except Exception as e:
                # Log the error but don't fail the feeder creation
                logger.error(f"WhatsApp notification failed for feeder {name}: {str(e)}")

            return redirect('feeder_list')

        except Exception as e:
            logger.error(f"Error creating feeder: {str(e)}")
            # Handle the error appropriately
            return render(request, 'add_feeder.html', {
                'business_types': business_types,
                'branches': branches,
                'today': date.today().isoformat(),
                'user_branch': user_branch,
                'user_branch_id': user_branch_id,
                'is_branch_restricted': is_branch_restricted,
                'error': f'Error creating feeder: {str(e)}'
            })

    return render(request, 'add_feeder.html', {
        'business_types': business_types,
        'branches': branches,
        'today': date.today().isoformat(),
        'user_branch': user_branch,
        'user_branch_id': user_branch_id,
        'is_branch_restricted': is_branch_restricted,
    })




# Updated feeder_list view with proper search functionality
def feeder_list(request):
    query = request.GET.get('q', '').strip()
    selected_branch = request.GET.get('branch', '').strip()
    selected_status = request.GET.get('status', '').strip()

    # Start with all feeders
    feeders_list = Feeder.objects.select_related('branch').all().order_by('-id')

    # Apply search filter
    if query:
        feeders_list = feeders_list.filter(
            Q(name__icontains=query) |
            Q(software__icontains=query) |
            Q(branch__name__icontains=query) |
            Q(contact_person__icontains=query) |
            Q(contact_number__icontains=query) |
            Q(area__icontains=query) |
            Q(location__icontains=query) |
            Q(district__icontains=query)
        )

    # Apply branch filter
    if selected_branch:
        feeders_list = feeders_list.filter(branch__name=selected_branch)

    # Apply status filter
    if selected_status:
        feeders_list = feeders_list.filter(status=selected_status)

    # Process each feeder for modules and prices
    for feeder in feeders_list:
        # Handle more_modules list
        feeder.more_modules_list = [
            m.strip() for m in (feeder.more_modules or '').split(',') if m.strip()
        ]
        
        # Handle price dictionary
        try:
            if isinstance(feeder.module_prices, str):
                feeder.price_dict = json.loads(feeder.module_prices)
            elif isinstance(feeder.module_prices, dict):
                feeder.price_dict = feeder.module_prices
            else:
                feeder.price_dict = {}
        except (ValueError, TypeError, json.JSONDecodeError):
            feeder.price_dict = {}

    # Pagination
    paginator = Paginator(feeders_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Get list of branches for dropdown
    branches = Branch.objects.all().order_by('name')

    context = {
        'page_obj': page_obj,
        'query': query,
        'branches': branches,
        'selected_branch': selected_branch,
        'selected_status': selected_status,
        'total_count': paginator.count,
        'allowed_menus': ['feeder_status'],
    }

    return render(request, 'feeder_list.html', context)

def feeder_edit(request, feeder_id):
    from django.apps import apps
    AppUser = apps.get_model('app1', 'User')  # ensure we use app1.User (has `userid`, `branch`)

    feeder = get_object_or_404(Feeder, id=feeder_id)

    # ------------------------------------------------------------------
    # Get the logged-in user's branch (similar to clients view)
    # ------------------------------------------------------------------
    try:
        custom_user = AppUser.objects.get(userid=request.user.username)
        user_branch = custom_user.branch if custom_user.branch else None
        user_branch_id = custom_user.branch.id if custom_user.branch else None
    except AppUser.DoesNotExist:
        user_branch = None
        user_branch_id = None

    # Check if user is branch restricted (not IMC/SYSMAC)
    is_branch_restricted = user_branch and user_branch.name not in ['IMC', 'SYSMAC']

    selected_modules = [m.strip() for m in (feeder.more_modules or '').split(',') if m.strip()]
    try:
        price_dict = (
            json.loads(feeder.module_prices)
            if isinstance(feeder.module_prices, str)
            else feeder.module_prices
        )
    except (ValueError, TypeError):
        price_dict = {}

    if request.method == 'POST':
        # Update all simple fields
        feeder.name = request.POST.get('name')
        feeder.address = request.POST.get('address')
        feeder.location = request.POST.get('location')
        feeder.area = request.POST.get('area')
        feeder.district = request.POST.get('district')
        feeder.state = request.POST.get('state')
        feeder.contact_person = request.POST.get('contact_person')
        feeder.contact_number = request.POST.get('contact_number')
        feeder.email = request.POST.get('email')
        feeder.reputed_person_name = request.POST.get('reputed_person_name', '')
        feeder.reputed_person_number = request.POST.get('reputed_person_number', '')
        feeder.software = request.POST.get('software')
        
        # Handle foreign key fields properly - convert to int and handle empty values
        nature_id = request.POST.get('nature')
        if nature_id and nature_id.strip():
            try:
                feeder.nature_id = int(nature_id)
            except (ValueError, TypeError):
                feeder.nature_id = None
        else:
            feeder.nature_id = None
        
        # ------------------------------------------------------------------
        # Handle branch selection with restriction
        # ------------------------------------------------------------------
        if is_branch_restricted:
            # For restricted users, keep their original branch or use their user branch
            feeder.branch_id = user_branch_id
        else:
            # For IMC/SYSMAC users, use the selected branch
            branch_id = request.POST.get('branch')
            if branch_id and branch_id.strip():
                try:
                    feeder.branch_id = int(branch_id)
                except (ValueError, TypeError):
                    feeder.branch_id = None
            else:
                feeder.branch_id = None
        
        # Handle numeric fields
        no_of_system = request.POST.get('no_of_system')
        if no_of_system and no_of_system.strip():
            try:
                feeder.no_of_system = int(no_of_system)
            except (ValueError, TypeError):
                feeder.no_of_system = None
        else:
            feeder.no_of_system = None
            
        pincode = request.POST.get('pincode')
        if pincode and pincode.strip():
            try:
                feeder.pincode = int(pincode)
            except (ValueError, TypeError):
                feeder.pincode = None
        else:
            feeder.pincode = None
        
        feeder.country = request.POST.get('country', 'India')
        
        # Handle date field (kept as-is; string assigned directly)
        installation_date = request.POST.get('installation_date')
        if installation_date and installation_date.strip():
            feeder.installation_date = installation_date
        else:
            feeder.installation_date = None
            
        feeder.remarks = request.POST.get('remarks', '')
        feeder.software_amount = request.POST.get('software_amount', '') or 0
        
        # Handle total_cost field - FIXED: Use module_charges field
        total_cost = request.POST.get('total_cost')
        feeder.module_charges = total_cost or 0
        
        # Handle modules
        feeder.modules = ', '.join(request.POST.getlist('modules'))
        feeder.more_modules = ', '.join(request.POST.getlist('more_modules'))

        # Re-save module prices
        new_prices = {
            m: request.POST.get(f'price_{m}', '0')
            for m in request.POST.getlist('more_modules')
        }
        feeder.module_prices = json.dumps(new_prices)
        
        try:
            feeder.save()
            return redirect('feeder_list')
        except Exception as e:
            # Add error handling - you might want to show this error to the user
            print(f"Error saving feeder: {e}")
            # messages.error(request, f"Error updating feeder: {e}")

    business_types = BusinessType.objects.all()
    branches = Branch.objects.all()

    return render(request, 'feeder_edit.html', {
        'feeder': feeder,
        'selected_modules': selected_modules,
        'price_dict': price_dict,
        'business_types': business_types,
        'branches': branches,
        'user_branch': user_branch,
        'user_branch_id': user_branch_id,
        'is_branch_restricted': is_branch_restricted,
    })



# ----------  DELETE  ----------
def feeder_delete(request, feeder_id):
    feeder = get_object_or_404(Feeder, id=feeder_id)
    if request.method == 'POST':
        feeder.delete()
    return redirect('feeder_list')


# ----------  STATUS UPDATE (FIXED)  ----------
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404
from .models import Feeder
import json
import traceback

@csrf_exempt
@require_POST
def feeder_status_update(request, feeder_id):
    try:
        # Parse JSON data from request body
        data = json.loads(request.body)
        new_status = data.get('status')

        if not new_status:
            return JsonResponse({'success': False, 'error': 'Status not provided'}, status=400)

        # Get the feeder object
        feeder = get_object_or_404(Feeder, id=feeder_id)

        # Validate status
        valid_statuses = [choice[0] for choice in Feeder.STATUS_CHOICES]
        if new_status not in valid_statuses:
            return JsonResponse({
                'success': False, 
                'error': f'Invalid status. Valid options: {valid_statuses}'
            }, status=400)

        # Update status
        feeder.status = new_status
        feeder.save()

        # Return success response
        return JsonResponse({
            'success': True,
            'new_status': feeder.get_status_display(),
            'status_class': feeder.get_status_display_class()
        })

    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON data'}, status=400)
    except Feeder.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Feeder not found'}, status=404)
    except Exception as e:
        # Log the full error for debugging
        print(f"Error in feeder_status_update: {str(e)}")
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': f'Server error: {str(e)}'}, status=500)







from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.db import IntegrityError
from django.contrib import messages
from django.db.models import Q
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.contrib.auth.models import User
import json
from .models import StandbyItem, StandbyImage


def Standby_item_list(request):
    search_query = request.GET.get('search', '').strip()
    status_filter = request.GET.get('status', '').strip()
    items = StandbyItem.objects.prefetch_related('images').all().order_by('-created_at')

    if search_query:
        items = items.filter(Q(name__icontains=search_query) | Q(serial_number__icontains=search_query))
    if status_filter:
        items = items.filter(status=status_filter)

    return render(request, 'standby_table.html', {
        'items': items,
        'search_query': search_query,
        'status_filter': status_filter,
    })


def Standby_add_item(request):
    if request.method == "POST":
        name = request.POST.get("itemname", "").upper()
        serial_number = request.POST.get("serialnumber", "").upper()
        notes = request.POST.get("notes", "")
        stock = request.POST.get("stock", 0)
        status = request.POST.get("status", "in_stock")

        customer_name = request.POST.get("customer_name", "")
        customer_place = request.POST.get("customer_place", "")
        customer_phone = request.POST.get("customer_phone", "")
        issued_date = request.POST.get("issued_date", None)

        images = request.FILES.getlist("images")

        try:
            current_user = request.user if request.user.is_authenticated else User.objects.first()

            item = StandbyItem.objects.create(
                name=name,
                serial_number=serial_number,
                notes=notes,
                stock=stock,
                status=status,
                customer_name=customer_name if status == 'with_customer' else None,
                customer_place=customer_place if status == 'with_customer' else None,
                customer_phone=customer_phone if status == 'with_customer' else None,
                issued_date=issued_date if status == 'with_customer' else None,
                created_by=current_user,
            )

            for img in images:
                StandbyImage.objects.create(item=item, image=img)

            messages.success(request, "Item added successfully!")
            return redirect("item_list")

        except IntegrityError:
            messages.error(request, f"Serial Number '{serial_number}' already exists!")
        except Exception as e:
            messages.error(request, f"Error creating item: {str(e)}")

        return redirect("add")

    return render(request, "add_standby.html")


def Standby_item_edit(request, item_id):
    item = get_object_or_404(StandbyItem, id=item_id)
    if request.method == "POST":
        item.name = request.POST.get('itemname', '').upper()
        item.serial_number = request.POST.get('serialnumber', '').upper()
        item.notes = request.POST.get('notes', '')
        item.stock = request.POST.get('stock', 0)
        item.status = request.POST.get('status', item.status)

        if item.status == 'with_customer':
            item.customer_name = request.POST.get('customer_name', '')
            item.customer_place = request.POST.get('customer_place', '')
            item.customer_phone = request.POST.get('customer_phone', '')
            item.issued_date = request.POST.get('issued_date', None)
        else:
            item.customer_name = None
            item.customer_place = None
            item.customer_phone = None
            item.issued_date = None

        try:
            item.save()
            delete_ids = request.POST.get('delete_images', '')
            if delete_ids:
                ids = [id.strip() for id in delete_ids.split(',') if id.strip()]
                StandbyImage.objects.filter(id__in=ids, item=item).delete()
            for image in request.FILES.getlist('images'):
                StandbyImage.objects.create(item=item, image=image)
            messages.success(request, "Item updated successfully!")
            return redirect('item_list')
        except IntegrityError:
            messages.error(request, "Serial number already exists!")
        except Exception as e:
            messages.error(request, f"Error updating item: {str(e)}")

        return redirect("item_edit", item_id=item.id)

    return render(request, 'edit_standby.html', {'item': item})


def Standby_item_delete(request, item_id):
    if request.method == "POST":
        try:
            item = get_object_or_404(StandbyItem, id=item_id)
            item.delete()
            messages.success(request, "Item deleted successfully!")
        except Exception as e:
            messages.error(request, f"Error deleting item: {str(e)}")
    return redirect('item_list')


def Standby_check_serial(request):
    serial = request.GET.get('serial', '').upper().strip()
    item_id = request.GET.get('item_id', None)
    if item_id:
        exists = StandbyItem.objects.filter(serial_number=serial).exclude(id=item_id).exists()
    else:
        exists = StandbyItem.objects.filter(serial_number=serial).exists()
    return JsonResponse({'exists': exists})


@csrf_exempt
def Standby_get_customer_info(request, item_id):
    """
    Returns JSON with customer info for a standby item
    """
    try:
        item = get_object_or_404(StandbyItem, id=item_id)

        # Debug: Check what data we have
        print(f"Item Status: {item.status}")
        print(f"Customer Name: {item.customer_name}")
        print(f"Customer Place: {item.customer_place}")
        print(f"Customer Phone: {item.customer_phone}")
        print(f"Issued Date: {item.issued_date}")

        # Ensure the item is currently with a customer
        if item.status.lower() != 'with_customer':
            return JsonResponse({
                'success': False,
                'error': f'Item "{item.name}" is not currently with a customer. Current status: {item.status}'
            })

        # Format the issued date properly
        issued_date_formatted = 'N/A'
        if item.issued_date:
            issued_date_formatted = item.issued_date.strftime('%d %b %Y')

        data = {
            'item_name': item.name,
            'serial_number': item.serial_number,
            'customer_name': item.customer_name or 'N/A',
            'customer_place': item.customer_place or 'N/A',
            'customer_phone': item.customer_phone or 'N/A',
            'issued_date': issued_date_formatted,
        }

        return JsonResponse({'success': True, 'data': data})

    except StandbyItem.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Item not found'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Server error: {str(e)}'
        })



from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from datetime import date

@login_required
def standby_return_item(request, item_id):
    """Handle returning standby item to stock with images"""
    item = get_object_or_404(StandbyItem, id=item_id)
    
    # Check if item is actually with customer
    if item.status != 'with_customer':
        messages.error(request, f'Item "{item.name}" is not currently with a customer.')
        return redirect('item_list')
    
    if request.method == 'POST':
        # Get form data
        return_date = request.POST.get('return_date')
        return_notes = request.POST.get('return_notes', '')
        stock = request.POST.get('stock', item.stock)
        return_images = request.FILES.getlist('return_images')
        
        # Update item status and details
        item.status = 'in_stock'
        item.stock = stock
        
        # Add return notes to existing notes
        if return_notes:
            current_notes = item.notes or ''
            return_info = f"\n\n--- RETURNED ON {return_date} ---\n{return_notes}"
            item.notes = current_notes + return_info
        
        # Clear customer information
        item.customer_name = None
        item.customer_place = None
        item.customer_phone = None
        item.issued_date = None
        
        item.save()
        
        # Handle return images - REMOVE the image_type parameter
        for image in return_images:
            StandbyImage.objects.create(
                item=item, 
                image=image
                # Remove: image_type='return_condition' - this field doesn't exist
            )
        
        messages.success(request, f'Item "{item.name}" has been returned to stock successfully!')
        return redirect('item_list')
    
    # For GET request, show the return form with current customer info
    context = {
        'item': item,
        'today': date.today(),
    }
    return render(request, 'return_standby_items.html', context)

    

