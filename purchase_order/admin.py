from django.contrib import admin
from django.utils import timezone 
from .models import Supplier, PurchaseOrder, Item, PurchaseOrderItem, Department

# ========== SUPPLIER ADMIN ==========
@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    """
    Admin interface for Supplier Master
    """
    list_display = (
        'id',
        'name',
        'city',
        'state',
        'mobile_no',
        'is_active',
        'created_at'
    )
    list_filter = ('is_active', 'state', 'city', 'created_at')
    search_fields = ('name', 'city', 'mobile_no', 'places')
    list_editable = ('is_active',)
    list_per_page = 25

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'is_active')
        }),
        ('Address Details', {
            'fields': ('address', 'places', 'city', 'state')
        }),
        ('Contact Information', {
            'fields': ('mobile_no', 'alternate_number')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'created_at'


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
class PurchaseOrderItemInline(admin.TabularInline):
    """
    Inline admin for Purchase Order Items
    Allows adding/editing items directly within PO admin
    """
    model = PurchaseOrderItem
    extra = 1
    fields = ('item', 'department', 'quantity', 'unit_price', 'discount', 'tax_percent', 'line_total')
    readonly_fields = ('line_total',)


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    """Admin interface for Purchase Orders with inline items"""
    list_display = (
        'po_number',
        'po_date',
        'supplier',
        'department',
        'grand_total',
        'status',
        'admin_status',
        'delivery_date',
        'created_at'
    )
    list_filter = (
        'status', 
        'admin_status',
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
            'fields': ('total_amount', 'tax_amount', 'grand_total')
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
    
    # ✅ ADD THIS METHOD - Override get_readonly_fields
    def get_readonly_fields(self, request, obj=None):
        """
        Make admin status fields readonly for non-superadmin
        """
        readonly = list(self.readonly_fields)
        
        # If not superadmin, make admin approval fields readonly
        if not request.user.is_superuser:
            readonly.extend([
                'admin_status',
                'admin_approved_by',
                'admin_rejection_reason'
            ])
        
        return readonly
    
    # ✅ ADD THIS METHOD - Custom save behavior
    def save_model(self, request, obj, form, change):
        """
        Auto-populate approval fields when admin status changes
        """
        if change and 'admin_status' in form.changed_data:
            if obj.admin_status in ['APPROVED', 'REJECTED']:
                obj.admin_approved_by = request.user.username
                obj.admin_approved_at = timezone.now()
        
        super().save_model(request, obj, form, change)

    