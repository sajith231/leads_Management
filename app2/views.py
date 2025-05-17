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
        
        # Filter by priority based on user status
        if not self.request.user.is_superuser:
            queryset = queryset.filter(priority='priority2')
        
        if product_type:
            queryset = queryset.filter(product_type_id=product_type)
        if product_category:
            queryset = queryset.filter(product_category_id=product_category)
            
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

@login_required
def edit_product_category(request, id):
    product_category = get_object_or_404(ProductCategory, id=id)
    product_types = ProductType.objects.all()
    if request.method == 'POST':
        name = request.POST.get('name')
        product_type_id = request.POST.get('product_type')
        if name and product_type_id:
            product_type = ProductType.objects.get(id=product_type_id)
            product_category.name = name
            product_category.product_type = product_type
            product_category.save()
            return redirect('product_category_list')
    return render(request, 'edit_product_category.html', {
        'product_category': product_category,
        'product_types': product_types
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