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

class InformationCenterListView(ListView):
    model = InformationCenter
    template_name = 'information_center.html'
    context_object_name = 'information_items'
    ordering = ['-added_date']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        product_type = self.request.GET.get('product_type')
        product_category = self.request.GET.get('product_category')
        search_query = self.request.GET.get('search', '').strip()  # Get the search query
        
        # Filter by priority based on user status
        if not self.request.user.is_superuser:
            queryset = queryset.filter(priority='priority2')
        
        if product_type:
            queryset = queryset.filter(product_type_id=product_type)
        if product_category:
            queryset = queryset.filter(product_category_id=product_category)
        if search_query:
            queryset = queryset.filter(title__icontains=search_query)  # Filter by title
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['product_types'] = ProductType.objects.all()
        context['product_categories'] = ProductCategory.objects.all()
        return context

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
        
        product_type = ProductType.objects.get(id=product_type_id)
        product_category = ProductCategory.objects.get(id=product_category_id)
        
        InformationCenter.objects.create(
            title=title,
            remark=remark,
            url=url,
            added_date=added_date,
            uploaded_by=request.user,
            product_type=product_type,
            product_category=product_category,
            thumbnail=thumbnail,
            priority=priority
        )
        return redirect('information_center')
    
    product_types = ProductType.objects.all()
    product_categories = ProductCategory.objects.all()
    
    return render(request, 'add_information_center.html', {
        'product_types': product_types,
        'product_categories': product_categories,
    })


# views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView
from .models import InformationCenter, ProductType, ProductCategory
from django.contrib.auth.decorators import login_required

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
        daily_tasks = daily_tasks.filter(added_by_id=user_filter)  # Filter by user ID
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

@login_required
def daily_task_user(request):
    daily_tasks = DailyTask.objects.filter(added_by=request.user).order_by('-created_at')


    paginator = Paginator(daily_tasks, 15)
    page = request.GET.get('page', 1)
    try:
        page_obj = paginator.page(page)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    return render(request, 'daily_task_user.html', {'page_obj': page_obj})

@login_required
def add_daily_task(request):
    if request.method == 'POST':
        project = request.POST.get('project', '').strip()
        project_assigned = request.POST.get('project_assigned', '').strip()
        task = request.POST.get('task', '').strip()
        duration = request.POST.get('duration', '').strip()
        status = request.POST.get('status', '').strip()
        remark = request.POST.get('remark', '')  # Get the remark field

        # Validate that either project or project_assigned is provided (but not both)
        if not project and not project_assigned:
            messages.error(request, 'Either "Project (Assigned)" or "Project (Manual Entry)" must be filled.')
            return redirect('add_daily_task')
        
        if project and project_assigned:
            messages.error(request, 'Please use only one project field - either assigned or manual entry.')
            return redirect('add_daily_task')

        # Validate other required fields
        if not task or not duration or not status:
            messages.error(request, 'All fields are required.')
            return redirect('add_daily_task')

        DailyTask.objects.create(
            project=project or project_assigned,
            task=task,
            duration=duration,
            status=status,
            added_by=request.user,
            remark=remark  # Add the remark field
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
        task.duration = request.POST['duration']
        task.status = request.POST['status']
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