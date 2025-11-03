from django.shortcuts import render, redirect, get_object_or_404
from django.utils.dateparse import parse_date
from django.contrib import messages
from django.db.models import Q
from django.db import transaction
from django.http import JsonResponse
from decimal import Decimal
from datetime import date
from django.utils import timezone  
from .models import Supplier, PurchaseOrder, Item, PurchaseOrderItem, Department
from django.core.paginator import Paginator
from django.core.paginator import EmptyPage, PageNotAnInteger
from django.db.models import ProtectedError
import requests

def send_whatsapp_message(recipient, message):
    """Send WhatsApp message via dxing.in API."""
    try:
        base_url = "https://app.dxing.in/api/send/whatsapp"
        secret = "7b8ae820ecb39f8d173d57b51e1fce4c023e359e"
        account = "1761365422812b4ba287f5ee0bc9d43bbf5bbe87fb68fc4daea92d8"
        payload = {
            "secret": secret,
            "account": account,
            "recipient": str(recipient),
            "type": "text",
            "message": message,
            "priority": 1
        }
        response = requests.get(base_url, params=payload, timeout=10)
        print(f"📨 WhatsApp API Status: {response.status_code}")
    except Exception as e:
        print(f"❌ WhatsApp send failed: {e}")

# ==================== SUPPLIER VIEWS (UPDATED) ====================

def supplier_list(request):
    """Display all suppliers with search functionality"""
    search_query = request.GET.get('search', '')
    department_filter = request.GET.get('department', '')
    
    suppliers = Supplier.objects.select_related('department').filter(is_active=True)
    
    if search_query:
        suppliers = suppliers.filter(
            Q(name__icontains=search_query) |
            Q(city__icontains=search_query) |
            Q(state__icontains=search_query) |
            Q(mobile_no__icontains=search_query) |
            Q(gst_number__icontains=search_query) |
            Q(contact_person_name__icontains=search_query)
        )
    
    if department_filter:
        suppliers = suppliers.filter(department_id=department_filter)

    # 🧾 Apply pagination (30 per page)
    paginator = Paginator(suppliers.order_by('-id'), 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    
    departments = Department.objects.filter(is_active=True).order_by('name')
    
    context = {
         'suppliers': page_obj, 
        'page_obj': page_obj,   
        'search_query': search_query,
        'department_filter': department_filter,
        'departments': departments,
    }
    return render(request, 'purchase_order/supplier_list.html', context)


def supplier_create(request):
    """Create a new supplier"""
    if request.method == 'POST':
        try:
            # Get department if provided
            department_id = request.POST.get('department')
            department = None
            if department_id:
                department = get_object_or_404(Department, pk=department_id)
            
            # Create supplier with new fields
            supplier = Supplier.objects.create(
                name=request.POST.get('name'),
                address=request.POST.get('address'),
                places=request.POST.get('places', ''),
                city=request.POST.get('city'),
                state=request.POST.get('state'),
                mobile_no=request.POST.get('mobile_no'),
                alternate_number=request.POST.get('alternate_number', ''),
                department=department,
                gst_number=request.POST.get('gst_number', ''),
                contact_person_name=request.POST.get('contact_person_name', ''),
                created_by=request.user.username if request.user.is_authenticated else 'Admin',
                updated_by=request.user.username if request.user.is_authenticated else 'Admin',
                is_active=True
            )
            messages.success(request, 'Supplier created successfully!')
            return redirect('purchase_order:supplier_list')
        except Exception as e:
            messages.error(request, f'Error creating supplier: {str(e)}')
    
    departments = Department.objects.filter(is_active=True).order_by('name')
    
    context = {
        'action': 'Create',
        'departments': departments,
    }
    return render(request, 'purchase_order/supplier_form.html', context)


def supplier_update(request, pk):
    """Update existing supplier"""
    supplier = get_object_or_404(Supplier, pk=pk)
    
    if request.method == 'POST':
        try:
            # Get department if provided
            department_id = request.POST.get('department')
            department = None
            if department_id:
                department = get_object_or_404(Department, pk=department_id)
            
            supplier.name = request.POST.get('name')
            supplier.address = request.POST.get('address')
            supplier.places = request.POST.get('places', '')
            supplier.city = request.POST.get('city')
            supplier.state = request.POST.get('state')
            supplier.mobile_no = request.POST.get('mobile_no')
            supplier.alternate_number = request.POST.get('alternate_number', '')
            supplier.department = department
            supplier.gst_number = request.POST.get('gst_number', '')
            supplier.contact_person_name = request.POST.get('contact_person_name', '')
            supplier.is_active = request.POST.get('is_active') == 'True'
            supplier.updated_by = request.user.username if request.user.is_authenticated else 'Admin'
            supplier.save()
            
            messages.success(request, 'Supplier updated successfully!')
            return redirect('purchase_order:supplier_list')
        except Exception as e:
            messages.error(request, f'Error updating supplier: {str(e)}')
    
    departments = Department.objects.filter(is_active=True).order_by('name')
    
    context = {
        'supplier': supplier,
        'action': 'Update',
        'departments': departments,
    }
    return render(request, 'purchase_order/supplier_form.html', context)


def supplier_delete(request, pk):
    """Soft delete supplier"""
    supplier = get_object_or_404(Supplier, pk=pk)
    
    if request.method == 'POST':
        if supplier.purchase_orders.exists():
            messages.warning(
                request,
                'Cannot delete supplier with existing purchase orders. Deactivating instead.'
            )
            supplier.is_active = False
            supplier.updated_by = request.user.username if request.user.is_authenticated else 'Admin'
            supplier.save()
        else:
            supplier.delete()
            messages.success(request, 'Supplier deleted successfully!')
        
        return redirect('purchase_order:supplier_list')
    
    return render(request, 'purchase_order/supplier_confirm_delete.html', {'supplier': supplier})


# ==================== ITEM MASTER VIEWS ====================

def item_list(request):
    """Display all items with pagination"""
    search_query = request.GET.get('search', '')
    department_filter = request.GET.get('department', '')

    # Base queryset
    items = Item.objects.all().order_by('name')

    # 🔍 Search filter
    if search_query:
        items = items.filter(
            Q(name__icontains=search_query) |
            Q(hsn_code__icontains=search_query)
        )

    # 🏢 Department filter
    if department_filter:
        items = items.filter(department_id=department_filter)

    # ✅ Pagination (25 per page)
    from django.core.paginator import Paginator
    paginator = Paginator(items, 10)
    page_number = request.GET.get('page')
    items = paginator.get_page(page_number)

    # 🧭 Department dropdown list
    departments = Department.objects.filter(is_active=True).order_by('name')

    # ✅ Context for template
    context = {
        'items': items,
        'search_query': search_query,
        'departments': departments,
        'selected_department': department_filter,  # match your template variable
    }

    return render(request, 'purchase_order/item_list.html', context)


def item_add(request):
    """Create new item"""
    if request.method == 'POST':
        try:

             # ✅ NEW: Get department if provided
            department_id = request.POST.get('department')
            department = None
            if department_id:
                department = get_object_or_404(Department, pk=department_id)

            Item.objects.create(
                name=request.POST.get('name'),
                description=request.POST.get('description', ''),
                department=department,
                unit_of_measure=request.POST.get('unit_of_measure', 'pcs'),
                tax_percentage=Decimal(request.POST.get('tax_percentage', '18.00')),
                mrp=Decimal(request.POST.get('mrp', '0.00')),
                purchase_price=Decimal(request.POST.get('purchase_price', '0.00')),
                cost=Decimal(request.POST.get('cost', '0.00')),
                hsn_code=request.POST.get('hsn_code', ''),
                is_active=True,  # Default to active
                created_by=request.user.username if request.user.is_authenticated else 'Admin',
                updated_by=request.user.username if request.user.is_authenticated else 'Admin',
            )
            messages.success(request, "Item added successfully.")
            return redirect('purchase_order:item_list')
        except Exception as e:
            messages.error(request, f"Error adding item: {str(e)}")

    # ✅ NEW: Get departments for dropdown
    departments = Department.objects.filter(is_active=True).order_by('name')
    
    return render(request, 'purchase_order/item_add.html', {
        'action': 'Add',
        'departments': departments  # ✅ ADDED
    })


def item_edit(request, pk):
    """Update existing item"""
    item = get_object_or_404(Item, pk=pk)
    
    if request.method == 'POST':
        try:
             # ✅ NEW: Get department if provided
            department_id = request.POST.get('department')
            department = None
            if department_id:
                department = get_object_or_404(Department, pk=department_id)

            item.name = request.POST.get('name')
            item.description = request.POST.get('description', '')
            item.department = department
            item.unit_of_measure = request.POST.get('unit_of_measure', 'pcs')
            item.tax_percentage = Decimal(request.POST.get('tax_percentage', '18.00'))
            item.mrp = Decimal(request.POST.get('mrp', '0.00'))
            item.purchase_price = Decimal(request.POST.get('purchase_price', '0.00'))
            item.cost = Decimal(request.POST.get('cost', '0.00'))
            item.hsn_code = request.POST.get('hsn_code', '')
            item.is_active = request.POST.get('status') == "True"  # ✅ Add status control
            item.updated_by = request.user.username if request.user.is_authenticated else 'Admin'
            item.save()

            
            messages.success(request, "Item updated successfully.")
            return redirect('purchase_order:item_list')
        except Exception as e:
            messages.error(request, f"Error updating item: {str(e)}")
    
     # ✅ NEW: Get departments for dropdown
    departments = Department.objects.filter(is_active=True).order_by('name')
    
    return render(request, 'purchase_order/item_edit.html', {
        'item': item,
        'action': 'Edit',
        'departments': departments  # ✅ ADDED
    })


def item_delete(request, pk):
    """Delete item"""
    item = get_object_or_404(Item, pk=pk)
    
    if request.method == 'POST':
        # Check if item is used in any PO
        if PurchaseOrderItem.objects.filter(item=item).exists():
            messages.error(request, 'Cannot delete item that exists in purchase orders.')
        else:
            item.delete()
            messages.success(request, 'Item deleted successfully!')
        return redirect('purchase_order:item_list')
    
    return render(request, 'purchase_order/item_confirm_delete.html', {'item': item})


# ==================== PURCHASE ORDER VIEWS ====================

def purchase_order_list(request):
    """Display all purchase orders with search and filters"""
    # Get filter parameters
    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    admin_status_filter = request.GET.get('admin_status', '')
    department_filter = request.GET.get('department', '')
    supplier_filter = request.GET.get('supplier', '')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    # Start with all purchase orders
    purchase_orders = PurchaseOrder.objects.select_related(
        'supplier', 
        'supplier__department'
    ).prefetch_related('po_items').all().order_by('-po_date', '-created_at')
    
    # Apply search filter
    if search_query:
        purchase_orders = purchase_orders.filter(
            Q(po_number__icontains=search_query) |
            Q(supplier__name__icontains=search_query) |
            Q(reference_number__icontains=search_query) |
            Q(supplier__city__icontains=search_query) |
            Q(supplier__state__icontains=search_query)
        )
    
    # Apply status filter
    if status_filter:
        purchase_orders = purchase_orders.filter(status=status_filter)
    
    # Apply admin status filter
    if admin_status_filter:
        purchase_orders = purchase_orders.filter(admin_status=admin_status_filter)
    
    # Apply department filter (filter by supplier's department)
    if department_filter:
        purchase_orders = purchase_orders.filter(supplier__department_id=department_filter)
    
    # Apply supplier filter
    if supplier_filter:
        purchase_orders = purchase_orders.filter(supplier_id=supplier_filter)

    if start_date:
        purchase_orders = purchase_orders.filter(po_date__gte=parse_date(start_date))
    if end_date:
        purchase_orders = purchase_orders.filter(po_date__lte=parse_date(end_date))    
    
    # Pagination - 25 items per page
    paginator = Paginator(purchase_orders, 10)
    page = request.GET.get('page')
    
    try:
        purchase_orders = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page
        purchase_orders = paginator.page(1)
    except EmptyPage:
        # If page is out of range, deliver last page
        purchase_orders = paginator.page(paginator.num_pages)
    
    # Get all active departments and suppliers for filter dropdowns
    departments = Department.objects.filter(is_active=True).order_by('name')
    suppliers = Supplier.objects.filter(is_active=True).order_by('name')
    
    context = {
        'purchase_orders': purchase_orders,
        'search_query': search_query,
        'status_filter': status_filter,
        'admin_status_filter': admin_status_filter,
        'department_filter': department_filter,
        'supplier_filter': supplier_filter,
        'start_date': start_date,
        'end_date': end_date,
        'status_choices': PurchaseOrder.STATUS_CHOICES,
        'admin_status_choices': PurchaseOrder.ADMIN_STATUS_CHOICES,
        'departments': departments,
        'suppliers': suppliers,
    }
    
    return render(request, 'purchase_order/po_list.html', context)


# ==================== CREATE PURCHASE ORDER ====================
@transaction.atomic
def purchase_order_create(request):
    """Create new purchase order with line items including entry rate"""
    if request.method == 'POST':
        # ✅ ADD THIS: Debug logging
        print("=" * 50)
        print("POST REQUEST RECEIVED")
        print("=" * 50)
        print(f"POST Data: {request.POST}")
        print(f"User: {request.user}")
        
        try:
            supplier = get_object_or_404(Supplier, pk=request.POST.get('supplier'))
            department = get_object_or_404(Department, pk=request.POST.get('department'))
            po_number = request.POST.get('po_number') or PurchaseOrder.generate_po_number()
            client_details = request.POST.get('client_details', '').strip()

            # ✅ ADD THIS: Validate client details
            if not client_details:
                print("❌ ERROR: Client details missing!")
                messages.error(request, 'Please select a client from the dropdown')
                return redirect('purchase_order:po_create')
            
            print(f"✅ Creating PO: {po_number}")
            print(f"✅ Supplier: {supplier.name}")
            print(f"✅ Client: {client_details}")
            
            if request.user.is_superuser:
                admin_status = request.POST.get('admin_status', 'PENDING')
            else:
                admin_status = 'PENDING'

            # Get calculation method
            calculation_method = request.POST.get('calculation_method', 'PLUS_TAX')

            # Create Purchase Order
            po = PurchaseOrder.objects.create(
                po_number=po_number,
                po_date=request.POST.get('po_date'),
                supplier=supplier,
                department=department,
                reference_number=request.POST.get('reference_number', ''),
                delivery_date=request.POST.get('delivery_date'),
                client_details=client_details,
                payment_terms=request.POST.get('payment_terms', 'NET_30'),
                status=request.POST.get('status', 'DRAFT'),
                admin_status=admin_status,
                calculation_method=calculation_method,
                notes=request.POST.get('notes', ''),
                created_by=request.user.username if request.user.is_authenticated else 'Admin'
            )

            print(f"✅ PO Created: {po.po_number} (ID: {po.id})")

            # Get line items
            item_ids = request.POST.getlist('item_id[]')
            quantities = request.POST.getlist('quantity[]')
            unit_prices = request.POST.getlist('unit_price[]')
            entry_rates = request.POST.getlist('entry_rate[]')
            sales_prices = request.POST.getlist('sales_price[]')
            discounts = request.POST.getlist('discount[]')
            tax_percents = request.POST.getlist('tax_percent[]')

            print(f"✅ Processing {len(item_ids)} line items")

            total_amount = Decimal('0.00')
            total_tax = Decimal('0.00')

            for i in range(len(item_ids)):
                if not item_ids[i]:
                    continue

                item = get_object_or_404(Item, pk=item_ids[i])
                
                qty = Decimal(quantities[i] or '0')
                unit_price = Decimal(unit_prices[i] or '0')
                discount = Decimal(discounts[i] or '0')
                tax_percent = Decimal(tax_percents[i] or '0')

                if calculation_method == 'PLUS_TAX':
                    entry_rate = unit_price
                    subtotal = (qty * unit_price) - discount
                    tax_amount = subtotal * (tax_percent / 100)
                    line_total = subtotal + tax_amount
                else:  # REVERSE_TAX
                    entry_rate = unit_price / (Decimal('1') + (tax_percent / Decimal('100')))
                    gross_amount = (qty * unit_price) - discount
                    subtotal = (qty * entry_rate) - (discount / (Decimal('1') + (tax_percent / Decimal('100'))))
                    tax_amount = gross_amount - subtotal
                    line_total = gross_amount

                PurchaseOrderItem.objects.create(
                    purchase_order=po,
                    item=item,
                    department=department,
                    quantity=qty,
                    unit_price=unit_price,
                    entry_rate=entry_rate,
                    sales_price=Decimal(sales_prices[i] or '0'), 
                    discount=discount,
                    tax_percent=tax_percent,
                    line_total=line_total
                )

                total_amount += subtotal
                total_tax += tax_amount

            # Update totals
            po.total_amount = total_amount
            po.tax_amount = total_tax
            po.grand_total = total_amount + total_tax
            po.save()

            print(f"✅ PO SAVED: Total = ₹{po.grand_total}")
            print("=" * 50)

            messages.success(request, f'Purchase Order {po.po_number} created successfully!')
            # ✅ WhatsApp notification to Super Admin when PO is created
            msg = (
                f"🧾 *New Purchase Order Created*\n"
                f"📄 *PO Number:* {po.po_number}\n"
                f"🏢 *Supplier:* {po.supplier.name}\n"
                f"🏬 *Department:* {po.department.name if po.department else 'N/A'}\n"
                f"💰 *Total:* ₹{po.grand_total}\n"
                f"📦 *Status:* {po.status}\n"
                f"📅 *Date:* {po.po_date}\n"
                f"👤 *Created By:* {po.created_by or request.user.username or 'System'}"
            )
            send_whatsapp_message("9946545535", msg)
            return redirect('purchase_order:po_list')

        except Exception as e:
            print(f"❌ ERROR: {str(e)}")
            print("=" * 50)
            import traceback
            traceback.print_exc()
            messages.error(request, f'Error creating purchase order: {str(e)}')
            return redirect('purchase_order:po_create')

    # ✅✅✅ GET REQUEST - FILTER ONLY ACTIVE ITEMS & SUPPLIERS ✅✅✅
    suppliers = Supplier.objects.filter(is_active=True).order_by('name')  # ✅ CHANGED
    items = Item.objects.filter(is_active=True).order_by('name')  # ✅ CHANGED
    departments = Department.objects.filter(is_active=True).order_by('name')

    context = {
        'suppliers': suppliers,
        'items': items,
        'departments': departments,
        'payment_terms': PurchaseOrder.PAYMENT_TERMS_CHOICES,
        'status_choices': PurchaseOrder.STATUS_CHOICES,
        'calculation_methods': PurchaseOrder.CALCULATION_METHOD_CHOICES,
        'today': date.today().isoformat(),
        'action': 'Create',
        'auto_po_number': PurchaseOrder.generate_po_number()
    }
    return render(request, 'purchase_order/po_form.html', context)


# ==================== UPDATE PURCHASE ORDER ====================
@transaction.atomic
def purchase_order_update(request, pk):
    """Update existing purchase order with entry rate support"""
    po = get_object_or_404(PurchaseOrder, pk=pk)

    if request.method == 'POST':
        try:
            supplier = get_object_or_404(Supplier, pk=request.POST.get('supplier'))
            department = get_object_or_404(Department, pk=request.POST.get('department'))

            # Update PO header
            po.po_number = request.POST.get('po_number')
            po.po_date = request.POST.get('po_date')
            po.supplier = supplier
            po.department = department
            po.reference_number = request.POST.get('reference_number', '')
            po.delivery_date = request.POST.get('delivery_date')
            po.client_details = request.POST.get('client_details')
            po.payment_terms = request.POST.get('payment_terms')
            po.status = request.POST.get('status')
            po.calculation_method = request.POST.get('calculation_method', 'PLUS_TAX')
            
            # Admin status handling
            if request.user.is_superuser:
                new_admin_status = request.POST.get('admin_status', po.admin_status)

                if new_admin_status != po.admin_status:
                    po.admin_status = new_admin_status
                    po.admin_approved_by = request.user.username
                    po.admin_approved_at = timezone.now()

                    # ✅ APPROVED
                    if new_admin_status == 'APPROVED':
                        po.admin_rejection_reason = ''
                        messages.success(request, f'✅ Purchase Order {po.po_number} has been approved!')

                        msg = (
                            f"✅ *Purchase Order Approved*\n"
                            f"📄 *PO Number:* {po.po_number}\n"
                            f"🏢 *Supplier:* {po.supplier.name}\n"
                            f"🏬 *Department:* {po.department.name if po.department else 'N/A'}\n"
                            f"💰 *Total:* ₹{po.grand_total}\n"
                            f"📅 *Approved On:* {timezone.now().strftime('%Y-%m-%d %H:%M')}\n"
                            f"👤 *Approved By:* {request.user.username}"
                        )
                        send_whatsapp_message("8606360089", msg)

                    # ❌ REJECTED
                    elif new_admin_status == 'REJECTED':
                        rejection_reason = request.POST.get('rejection_reason', 'No reason provided')
                        po.admin_rejection_reason = rejection_reason
                        messages.warning(request, f'❌ Purchase Order {po.po_number} has been rejected!')

                        msg = (
                            f"❌ *Purchase Order Rejected*\n"
                            f"📄 *PO Number:* {po.po_number}\n"
                            f"🏢 *Supplier:* {po.supplier.name}\n"
                            f"🏬 *Department:* {po.department.name if po.department else 'N/A'}\n"
                            f"💰 *Total:* ₹{po.grand_total}\n"
                            f"📅 *Rejected On:* {timezone.now().strftime('%Y-%m-%d %H:%M')}\n"
                            f"📝 *Reason:* {rejection_reason}\n"
                            f"👤 *Rejected By:* {request.user.username}"
                        )
                        send_whatsapp_message("8606360089", msg)
            
            po.notes = request.POST.get('notes', '')
            po.save()

            # Remove existing line items
            po.po_items.all().delete()

            # Recalculate with entry rate
            item_ids = request.POST.getlist('item_id[]')
            quantities = request.POST.getlist('quantity[]')
            unit_prices = request.POST.getlist('unit_price[]')
            entry_rates = request.POST.getlist('entry_rate[]')
            sales_prices = request.POST.getlist('sales_price[]')  # ✅ Already getting this
            discounts = request.POST.getlist('discount[]')
            tax_percents = request.POST.getlist('tax_percent[]')

            total_amount = Decimal('0.00')
            total_tax = Decimal('0.00')

            for i in range(len(item_ids)):
                if not item_ids[i]:
                    continue

                item = get_object_or_404(Item, pk=item_ids[i])
                qty = Decimal(quantities[i] or '0')
                unit_price = Decimal(unit_prices[i] or '0')
                sales_price = Decimal(sales_prices[i] or '0')  # ✅ Extract sales_price
                discount = Decimal(discounts[i] or '0')
                tax_percent = Decimal(tax_percents[i] or '0')

                # Calculate based on method
                if po.calculation_method == 'PLUS_TAX':
                    entry_rate = unit_price
                    subtotal = (qty * unit_price) - discount
                    tax_amount = subtotal * (tax_percent / 100)
                    line_total = subtotal + tax_amount
                else:  # REVERSE_TAX
                    entry_rate = unit_price / (Decimal('1') + (tax_percent / Decimal('100')))
                    gross_amount = (qty * unit_price) - discount
                    subtotal = (qty * entry_rate) - (discount / (Decimal('1') + (tax_percent / Decimal('100'))))
                    tax_amount = gross_amount - subtotal
                    line_total = gross_amount

                # ✅ FIX: Include sales_price when creating the item
                PurchaseOrderItem.objects.create(
                    purchase_order=po,
                    item=item,
                    department=department,
                    quantity=qty,
                    unit_price=unit_price,
                    entry_rate=entry_rate,
                    sales_price=sales_price,  # ✅ ADD THIS LINE
                    discount=discount,
                    tax_percent=tax_percent,
                    line_total=line_total
                )

                total_amount += subtotal
                total_tax += tax_amount

            po.total_amount = total_amount
            po.tax_amount = total_tax
            po.grand_total = total_amount + total_tax
            po.save()

            messages.success(request, f'Purchase Order {po.po_number} updated successfully!')
            # ✅ Notify Super Admin when PO is updated
            if not request.user.is_superuser:
                msg = (
                    f"✏️ *Purchase Order Updated*\n"
                    f"📄 *PO Number:* {po.po_number}\n"
                    f"🏢 *Supplier:* {po.supplier.name}\n"
                    f"🏬 *Department:* {po.department.name if po.department else 'N/A'}\n"
                    f"💰 *Total:* ₹{po.grand_total}\n"
                    f"📅 *Updated On:* {timezone.now().strftime('%Y-%m-%d %H:%M')}\n"
                    f"👤 *Updated By:* {request.user.username}"
                )
                send_whatsapp_message("9946545535", msg)
            return redirect('purchase_order:po_list')

        except Exception as e:
            messages.error(request, f'Error updating purchase order: {str(e)}')

    # ✅✅✅ GET REQUEST - SHOW ACTIVE + CURRENTLY USED INACTIVE RECORDS ✅✅✅
    
    # Get all active suppliers
    suppliers = Supplier.objects.filter(is_active=True).order_by('name')
    
    # ✅ IMPORTANT: Include currently selected supplier even if inactive
    if po.supplier and not po.supplier.is_active:
        suppliers = suppliers | Supplier.objects.filter(id=po.supplier.id)
    
    # Get all active items
    items = Item.objects.filter(is_active=True).order_by('name')
    
    # ✅ IMPORTANT: Include currently used items even if inactive
    used_item_ids = po.po_items.values_list('item_id', flat=True)
    inactive_used_items = Item.objects.filter(
        id__in=used_item_ids,
        is_active=False
    )
    if inactive_used_items.exists():
        items = items | inactive_used_items
    
    # Get active departments
    departments = Department.objects.filter(is_active=True).order_by('name')

    context = {
        'po': po,
        'suppliers': suppliers,
        'items': items,
        'departments': departments,
        'payment_terms': PurchaseOrder.PAYMENT_TERMS_CHOICES,
        'status_choices': PurchaseOrder.STATUS_CHOICES,
        'admin_status_choices': PurchaseOrder.ADMIN_STATUS_CHOICES,
        'calculation_methods': PurchaseOrder.CALCULATION_METHOD_CHOICES,
        'is_superuser': request.user.is_superuser,
        'action': 'Update',
        'today': date.today().isoformat(), 
        'auto_po_number': po.po_number
    }
    return render(request, 'purchase_order/po_form.html', context)

def purchase_order_view(request, pk):
    """View purchase order details"""
    po = get_object_or_404(
        PurchaseOrder.objects.select_related('supplier').prefetch_related('po_items__item'),
        pk=pk
    )
    context = {'po': po}
    return render(request, 'purchase_order/po_detail.html', context)


def purchase_order_delete(request, pk):
    """Delete purchase order"""
    po = get_object_or_404(PurchaseOrder, pk=pk)
    
    if request.method == 'POST':
        po_number = po.po_number
        po.delete()
        messages.success(request, f'Purchase Order {po_number} deleted successfully!')
        return redirect('purchase_order:po_list')
    
    return render(request, 'purchase_order/po_confirm_delete.html', {'po': po})


# ==================== AJAX API ENDPOINTS ====================

def get_item_details(request, item_id):
    """API endpoint to get item details for AJAX calls"""
    try:
        item = Item.objects.get(pk=item_id)
        data = {
            'id': item.id,
            'name': item.name,
            'purchase_price': str(item.purchase_price),
            'tax_percentage': str(item.tax_percentage),
            'unit_of_measure': item.unit_of_measure,
            'hsn_code': item.hsn_code or ''
        }
        return JsonResponse(data)
    except Item.DoesNotExist:
        return JsonResponse({'error': 'Item not found'}, status=404)


def get_supplier_details(request, supplier_id):
    """API endpoint to get supplier details for AJAX calls"""
    try:
        supplier = Supplier.objects.get(pk=supplier_id)
        data = {
            'id': supplier.id,
            'name': supplier.name,
            'address': supplier.address,
            'city': supplier.city,
            'state': supplier.state,
            'mobile_no': supplier.mobile_no
        }
        return JsonResponse(data)
    except Supplier.DoesNotExist:
        return JsonResponse({'error': 'Supplier not found'}, status=404)
    
# ==================== DEPARTMENT MASTER VIEWS (ADD THESE) ====================

def department_list(request):
    search_query = request.GET.get('search', '')

    departments = Department.objects.all().order_by('name')

    if search_query:
        departments = departments.filter(
            Q(name__icontains=search_query) |
            Q(city__icontains=search_query) |
            Q(gst_number__icontains=search_query) |
            Q(contact_number__icontains=search_query)
        )

    # ✅ PAGINATION
    paginator = Paginator(departments, 10)  # 25 entries per page
    page_number = request.GET.get('page')
    departments = paginator.get_page(page_number)

    return render(request, 'purchase_order/department_list.html', {
        'departments': departments,
        'search_query': search_query,
    })

def department_create(request):
    """Create a new department"""
    if request.method == 'POST':
        try:
            Department.objects.create(
                name=request.POST.get('name'),
                address=request.POST.get('address'),
                city=request.POST.get('city'),
                state=request.POST.get('state'),
                pincode=request.POST.get('pincode'),
                contact_number=request.POST.get('contact_number'),
                alternate_number=request.POST.get('alternate_number', ''),
                email=request.POST.get('email', ''),
                gst_number=request.POST.get('gst_number', ''),
                is_active=True
            )
            messages.success(request, 'Department created successfully!')
            return redirect('purchase_order:department_list')
        except Exception as e:
            messages.error(request, f'Error creating department: {str(e)}')
    
    return render(request, 'purchase_order/department_form.html', {'action': 'Create'})


def department_update(request, pk):
    """Update existing department"""
    department = get_object_or_404(Department, pk=pk)
    
    if request.method == 'POST':
        try:
            department.name = request.POST.get('name')
            department.address = request.POST.get('address')
            department.city = request.POST.get('city')
            department.state = request.POST.get('state')
            department.pincode = request.POST.get('pincode')
            department.contact_number = request.POST.get('contact_number')
            department.alternate_number = request.POST.get('alternate_number', '')
            department.email = request.POST.get('email', '')
            department.gst_number = request.POST.get('gst_number', '')
            department.save()
            
            messages.success(request, 'Department updated successfully!')
            return redirect('purchase_order:department_list')
        except Exception as e:
            messages.error(request, f'Error updating department: {str(e)}')
    
    context = {
        'department': department,
        'action': 'Update'
    }
    return render(request, 'purchase_order/department_form.html', context)

def department_delete(request, pk):
    """Soft delete department (handles linked suppliers, items, and purchase orders)"""
    department = get_object_or_404(Department, pk=pk)
    
    if request.method == 'POST':
        try:
            # Check if department has linked records
            has_po = department.purchase_orders.exists()
            has_supplier = department.suppliers.exists()
            has_item = department.items.exists()

            if has_po or has_supplier or has_item:
                messages.warning(
                    request,
                    'Cannot delete department with linked suppliers, items, or purchase orders. Deactivating instead.'
                )
                department.is_active = False
                department.save()
            else:
                department.delete()
                messages.success(request, 'Department deleted successfully!')
        except ProtectedError:
            messages.error(
                request,
                'Cannot delete department — it is referenced by other records (Suppliers/Items).'
            )

        return redirect('purchase_order:department_list')
    
    return render(request, 'purchase_order/department_confirm_delete.html', {'department': department})

# ==================== AJAX API ENDPOINT FOR DEPARTMENT (ADD THIS) ====================

def get_department_details(request, department_id):
    """API endpoint to get department details for AJAX calls"""
    try:
        department = Department.objects.get(pk=department_id)
        data = {
            'id': department.id,
            'name': department.name,
            'address': department.address,
            'city': department.city,
            'state': department.state,
            'pincode': department.pincode,
            'contact_number': department.contact_number,
            'email': department.email,
            'gst_number': department.gst_number,
            'full_address': department.get_full_address()
        }
        return JsonResponse(data)
    except Department.DoesNotExist:
        return JsonResponse({'error': 'Department not found'}, status=404) 

# ==================== CLIENT API PROXY ====================

def get_clients_from_api(request):
    """
    Proxy endpoint to fetch clients from external API.
    Returns clients with name, place, city, and enhanced display name.
    """
    import requests
    
    try:
        # Fetch from external API
        response = requests.get(
            'https://accmaster.imcbs.com/api/sync/rrc-clients/',
            timeout=10
        )
        response.raise_for_status()
        
        data = response.json()
        
        # Handle different API response formats
        clients = []
        if isinstance(data, list):
            clients = data
        elif isinstance(data, dict):
            clients = data.get('results', data.get('data', []))
        
        if not clients:
            return JsonResponse([], safe=False)
        
        # Enhance clients with display names including location
        enhanced_clients = []
        
        for client in clients:
            # Get client name
            client_name = (
                client.get('name') or 
                client.get('client_name') or 
                client.get('title') or 
                'Unnamed Client'
            ).strip()
            
            # Get location details from API fields
            place = (
                client.get('address3') or
                client.get('address') or
                client.get('rout') or
                ''
            ).strip()
            
            city = (
                client.get('district') or
                ''
            ).strip()
            
            state = (
                client.get('state') or
                ''
            ).strip()
            
            # Build location string
            location_parts = []
            
            if place and place.upper() not in ['', 'NULL', 'NONE', '--']:
                location_parts.append(place)
            
            if city and city.upper() != place.upper():
                location_parts.append(city)
            
            if state and len(location_parts) < 2:
                location_parts.append(state)
            
            location_str = ', '.join(location_parts) if location_parts else ''
            
            # Create display name with location
            if location_str:
                display_name = f"{client_name} - {location_str}"
            else:
                display_name = client_name
            
            enhanced_clients.append({
                'id': client.get('code', client.get('id', '')),
                'name': client_name,
                'display_name': display_name,
                'place': place,
                'city': city,
                'state': state,
            })
        
        # Sort alphabetically by display name
        enhanced_clients.sort(key=lambda x: x['display_name'].upper())
        
        return JsonResponse(enhanced_clients, safe=False)
        
    except requests.exceptions.Timeout:
        return JsonResponse(
            {'error': 'API request timed out. Please try again.'},
            status=504
        )
    except requests.exceptions.ConnectionError:
        return JsonResponse(
            {'error': 'Unable to connect to API. Please check your internet connection.'},
            status=503
        )
    except requests.exceptions.RequestException as e:
        return JsonResponse(
            {'error': f'Error fetching clients: {str(e)}'},
            status=500
        )
    except Exception as e:
        return JsonResponse(
            {'error': f'Unexpected error: {str(e)}'},
            status=500
        )


# Optional: Add caching to reduce API calls
def get_clients_cached(request):
    """
    Same as above but with caching (cache for 5 minutes).
    Uncomment this section if you want to reduce API calls.
    """
    from django.views.decorators.cache import cache_page
    from django.utils.decorators import decorator_from_middleware_with_args
    
    # This would need @cache_page(300) decorator
    # Or implement Redis caching for better performance
    pass       

from django.contrib.auth.decorators import login_required
from django.utils import timezone

@login_required
def approve_purchase_order(request, pk):
    """Update admin approval status (superadmin only)"""
    po = get_object_or_404(PurchaseOrder, pk=pk)
    
    # Check if user is superadmin
    if not request.user.is_superuser:
        messages.error(request, '⚠️ Only superadmin can change approval status.')
        return redirect('purchase_order:po_detail', pk=po.pk)
    
    if request.method == 'POST':
        new_status = request.POST.get('admin_status')
        
        if new_status in ['PENDING', 'APPROVED', 'REJECTED']:
            old_status = po.admin_status
            po.admin_status = new_status
            po.admin_approved_by = request.user.username
            po.admin_approved_at = timezone.now()
            
            if new_status == 'REJECTED':
                po.admin_rejection_reason = request.POST.get('rejection_reason', 'No reason provided')
            else:
                po.admin_rejection_reason = ''
            
            po.save()
            
            # Success messages
            if new_status == 'APPROVED':
                messages.success(request, f'✅ Purchase Order {po.po_number} has been APPROVED!')
            elif new_status == 'REJECTED':
                messages.warning(request, f'❌ Purchase Order {po.po_number} has been REJECTED!')
            else:
                messages.info(request, f'⏳ Purchase Order {po.po_number} status set to PENDING.')
        else:
            messages.error(request, 'Invalid approval status.')
    
    return redirect('purchase_order:po_detail', pk=po.pk)

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

@login_required
def generate_po_pdf(request, pk):
    """Generate and return PO PDF as bytes for printing or WhatsApp sharing."""
    from io import BytesIO
    po = get_object_or_404(PurchaseOrder, pk=pk)

    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    y = height - 50

    p.setFont("Helvetica-Bold", 16)
    p.drawString(200, y, f"PURCHASE ORDER - {po.po_number}")

    y -= 40
    p.setFont("Helvetica", 12)
    p.drawString(50, y, f"Supplier: {po.supplier.name}")
    y -= 20
    p.drawString(50, y, f"Department: {po.department.name if po.department else 'N/A'}")
    y -= 20
    p.drawString(50, y, f"PO Date: {po.po_date}")
    y -= 20
    p.drawString(50, y, f"Total Amount: ₹{po.grand_total}")
    y -= 30

    p.setFont("Helvetica-Bold", 13)
    p.drawString(50, y, "Items:")
    y -= 20
    p.setFont("Helvetica", 11)

    for item in po.po_items.all():
        line = f"{item.item.name} - Qty: {item.quantity} | Rate: ₹{item.unit_price} | Total: ₹{item.line_total}"
        p.drawString(50, y, line)
        y -= 15
        if y < 100:
            p.showPage()
            y = height - 50
            p.setFont("Helvetica", 11)

    p.showPage()
    p.save()
    buffer.seek(0)

    # Return raw PDF bytes for reuse
    return buffer

import os
import requests
from io import BytesIO
from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from .models import PurchaseOrder

@csrf_exempt
@login_required
def send_whatsapp_po(request, pk):
    """Generate PO PDF and send it via WhatsApp to the supplier."""
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request method"}, status=405)

    po = get_object_or_404(PurchaseOrder, pk=pk)
    supplier = po.supplier

    if not supplier.mobile_no:
        return JsonResponse({"error": "Supplier mobile number not found"}, status=400)

    # ✅ Normalize the phone number
    raw_number = str(supplier.mobile_no).strip().replace("+", "")
    if len(raw_number) == 10:  # assume local Indian number
        recipient_number = "91" + raw_number
    else:
        recipient_number = raw_number

    print(f"📱 Sending WhatsApp to: {recipient_number}")

    # ✅ 1. Generate PDF
    try:
        pdf_buffer = BytesIO()
        c = canvas.Canvas(pdf_buffer, pagesize=A4)
        c.drawString(100, 800, f"Purchase Order: {po.po_number}")
        c.drawString(100, 780, f"Supplier: {supplier.name}")
        c.drawString(100, 760, f"Total: ₹{po.grand_total}")
        c.showPage()
        c.save()
        pdf_buffer.seek(0)

        folder_path = os.path.join(settings.MEDIA_ROOT, "po_pdfs")
        os.makedirs(folder_path, exist_ok=True)
        file_name = f"PO_{po.po_number}.pdf"
        file_path = os.path.join(folder_path, file_name)

        with open(file_path, "wb") as f:
            f.write(pdf_buffer.getbuffer())

        # ✅ Use your live domain for file link
        file_url = f"https://myimc.in/media/po_pdfs/{file_name}"

        print(f"📎 PDF URL: {file_url}")

    except Exception as e:
        return JsonResponse({"error": f"PDF generation failed: {str(e)}"}, status=500)

    # ✅ 2. Send to WhatsApp API
    try:
        base_url = "https://app.dxing.in/api/send/whatsapp"
        secret = "7b8ae820ecb39f8d173d57b51e1fce4c023e359e"
        account = "1761365422812b4ba287f5ee0bc9d43bbf5bbe87fb68fc4daea92d8"

        payload = {
            "secret": secret,
            "account": account,
            "recipient": recipient_number,
            "type": "document",
            "document_url": file_url,
            "document_name": file_name,
            "document_type": "pdf",
            "priority": 1,
        }

        response = requests.get(base_url, params=payload, timeout=10)
        print("📤 WhatsApp API Response:", response.status_code, response.text)

        if response.status_code == 200:
            return JsonResponse({
                "status": "success",
                "message": "WhatsApp message sent successfully!",
                "api_response": response.text,
            })
        else:
            return JsonResponse({
                "status": "failed",
                "message": f"WhatsApp API returned {response.status_code}",
                "api_response": response.text,
            }, status=400)

    except Exception as e:
        return JsonResponse({"error": f"WhatsApp send failed: {str(e)}"}, status=500)
