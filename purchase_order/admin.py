from django.contrib import admin
from django.utils import timezone 
from .models import Supplier, PurchaseOrder, Item, PurchaseOrderItem, Department

# ========== SUPPLIER ADMIN (UPDATED) ==========
@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    """
    Admin interface for Supplier Master
    """
    list_display = (
        'id',
        'name',
        'department',
        'contact_person_name',
        'city',
        'state',
        'mobile_no',
        'gst_number',
        'created_by',
        'created_at',
        'is_active'
    )
    list_filter = ('is_active', 'department', 'state', 'city', 'created_at')
    search_fields = (
        'name', 
        'city', 
        'mobile_no', 
        'places', 
        'gst_number',
        'contact_person_name',
        'department__name'
    )
    list_editable = ('is_active',)
    list_per_page = 25
    autocomplete_fields = ['department']

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'department', 'is_active')
        }),
        ('Address Details', {
            'fields': ('address', 'places', 'city', 'state')
        }),
        ('Contact Information', {
            'fields': (
                'contact_person_name',
                'mobile_no', 
                'alternate_number'
            )
        }),
        ('Business Details', {
            'fields': ('gst_number',)
        }),
        ('Record Information', {
            'fields': (
                'created_by',
                'updated_by',
                'created_at', 
                'updated_at'
            ),
            'classes': ('collapse',)
        }),
    )

    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'created_at'
    
    def save_model(self, request, obj, form, change):
        """
        Auto-populate created_by and updated_by fields
        """
        if not change:  # Creating new object
            obj.created_by = request.user.username
            obj.updated_by = request.user.username
        else:  # Updating existing object
            obj.updated_by = request.user.username
        
        super().save_model(request, obj, form, change)


# ========== DEPARTMENT ADMIN ==========
@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    """
    Admin interface for Department Master (Buyer Departments)
    """
    list_display = (
        'id',
        'name',
        'city',
        'state',
        'contact_number',
        'email',
        'gst_number',
        'is_active',
        'created_at'
    )
    list_filter = ('is_active', 'state', 'city', 'created_at')
    search_fields = ('name', 'city', 'state', 'gst_number', 'email', 'contact_number')
    list_editable = ('is_active',)
    list_per_page = 25

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'is_active')
        }),
        ('Address Details', {
            'fields': ('address', 'city', 'state', 'pincode')
        }),
        ('Contact Information', {
            'fields': ('contact_number', 'alternate_number', 'email')
        }),
        ('Business Details', {
            'fields': ('gst_number',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'created_at'


# ========== ITEM ADMIN ==========
@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    """
    Admin interface for Item Master with Department support
    """
    list_display = (
        'id', 
        'name', 
        'department',  # ✅ ADDED
        'unit_of_measure', 
        'purchase_price', 
        'tax_percentage', 
        'hsn_code'
    )
    search_fields = ('name', 'hsn_code', 'department__name')  # ✅ UPDATED
    list_filter = ('tax_percentage', 'unit_of_measure', 'department')  # ✅ UPDATED
    list_per_page = 25
    autocomplete_fields = ['department']  # ✅ ADDED - enables searchable dropdown
    
    # Optional: Add fieldsets for better organization
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'department')  # ✅ ADDED department
        }),
        ('Measurement', {
            'fields': ('unit_of_measure', 'hsn_code')
        }),
        ('Pricing', {
            'fields': ('mrp', 'purchase_price', 'cost', 'tax_percentage')
        }),
    )


# ========== PURCHASE ORDER ITEM INLINE ==========
# ========== PURCHASE ORDER ITEM INLINE ==========
class PurchaseOrderItemInline(admin.TabularInline):
    """
    Inline admin for Purchase Order Items
    Now includes entry_rate for Reverse Tax calculations
    """
    model = PurchaseOrderItem
    extra = 1
    fields = (
        'item', 
        'department', 
        'quantity', 
        'unit_price', 
        'entry_rate',
        'item_cost', 
        'sales_price',  # ✅ Added for visibility
        'margin',       # ✅ NEW field                      # ✅ NEW - Shows base price after tax extraction
        'discount', 
        'tax_percent', 
        'line_total'
    )
    readonly_fields = ('line_total','item_cost','entry_rate', 'margin')  # ✅ UPDATED


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    """Admin interface for Purchase Orders with inline items"""
    list_display = (
        'po_number',
        'po_date',
        'supplier',
        'department',
        'calculation_method',  # ✅ NEW
        'grand_total',
        'status',
        'admin_status',
        'delivery_date',
        'created_at'
    )
    list_filter = (
        'status', 
        'admin_status',
        'calculation_method',  # ✅ NEW
        'department', 
        'payment_terms', 
        'po_date', 
        'delivery_date'
    )
    search_fields = (
        'po_number',
        'reference_number',
        'supplier__name',
        'department__name',
        'client_details'
    )
    list_editable = ('status', 'admin_status')
    list_per_page = 25

    inlines = [PurchaseOrderItemInline]

    fieldsets = (
        ('Purchase Order Details', {
            'fields': ('po_number', 'po_date', 'supplier', 'department', 'reference_number')
        }),
        ('Client & Delivery Information', {
            'fields': ('delivery_date', 'client_details')
        }),
        ('Financial Details', {
            'fields': (
                'calculation_method',  # ✅ NEW - Added here
                'total_amount', 
                'tax_amount', 
                'grand_total'
            ),
            'description': '💡 Plus Tax: Adds tax on base | Reverse Tax: Extracts tax from total'
        }),
        ('Terms & Status', {
            'fields': ('payment_terms', 'status', 'notes')
        }),
        ('Admin Approval', {
            'fields': (
                'admin_status', 
                'admin_approved_by', 
                'admin_approved_at',
                'admin_rejection_reason'
            ),
            'classes': ('collapse',),
            'description': '⚠️ Only superadmin should modify these fields'
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    readonly_fields = (
        'grand_total', 
        'created_at', 
        'updated_at',
        'admin_approved_at'
    )
    date_hierarchy = 'po_date'
    autocomplete_fields = ['supplier']
    
    def get_readonly_fields(self, request, obj=None):
        """Make admin status fields readonly for non-superadmin"""
        readonly = list(self.readonly_fields)
        
        if not request.user.is_superuser:
            readonly.extend([
                'admin_status',
                'admin_approved_by',
                'admin_rejection_reason'
            ])
        
        return readonly
    
    def save_model(self, request, obj, form, change):
        """Auto-populate approval fields when admin status changes"""
        if change and 'admin_status' in form.changed_data:
            if obj.admin_status in ['APPROVED', 'REJECTED']:
                obj.admin_approved_by = request.user.username
                obj.admin_approved_at = timezone.now()
        
        super().save_model(request, obj, form, change)

    