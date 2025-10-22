from django.db import models
from django.core.validators import RegexValidator
from django.core.validators import MinValueValidator
from decimal import Decimal

# ========== SUPPLIER MODEL ==========
class Supplier(models.Model):
    """
    Supplier Master - Stores supplier/vendor information
    """
    name = models.CharField(max_length=120, verbose_name="Supplier Name")
    address = models.TextField(verbose_name="Address")
    places = models.CharField(max_length=120, blank=True, verbose_name="Place/Landmark")
    city = models.CharField(max_length=60, verbose_name="City")
    state = models.CharField(max_length=60, verbose_name="State")
    
    # Phone number validator
    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
    )
    mobile_no = models.CharField(
        validators=[phone_regex], 
        max_length=15, 
        verbose_name="Mobile Number"
    )
    alternate_number = models.CharField(
        validators=[phone_regex],
        max_length=15,
        blank=True,
        verbose_name="Alternate Number"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True, verbose_name="Active Status")

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Supplier"
        verbose_name_plural = "Suppliers"

    def __str__(self):
        return self.name


# ========== PURCHASE ORDER MODEL ==========
class PurchaseOrder(models.Model):
    """
    Purchase Order - Stores PO information with supplier reference
    """
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('DELIVERED', 'Delivered'),
        ('CANCELLED', 'Cancelled'),
    ]
    
    PAYMENT_TERMS_CHOICES = [
        ('NET_30', 'Net 30 Days'),
        ('NET_60', 'Net 60 Days'),
        ('COD', 'Cash on Delivery'),
        ('ADVANCE', 'Advance Payment'),
        ('CREDIT', 'Credit'),
    ]

    # ✅ NEW: Admin Approval Status
    ADMIN_STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    ]
    
    # PO Basic Info
    po_number = models.CharField(
        max_length=50, 
        unique=True, 
        verbose_name="PO Number",
        help_text="Unique Purchase Order Number"
    )
    po_date = models.DateField(verbose_name="PO Date")
    
    # Supplier Reference (Foreign Key)
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.PROTECT,
        related_name='purchase_orders',
        verbose_name="Supplier"
    )

    # Department Reference (Foreign Key)
    department = models.ForeignKey(
        'Department',
        on_delete=models.PROTECT,
        related_name='purchase_orders',
        verbose_name="Buyer Department",
        help_text="Department making the purchase",
        null=True, blank=True
    )
    
    # Additional Info
    reference_number = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Reference Number",
        help_text="Quotation or Reference Number"
    )
    delivery_date = models.DateField(verbose_name="Expected Delivery Date")
    client_details = models.TextField(verbose_name="Client Details", default='')
    
    # Financial Details
    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Total Amount",
        default=0.00
    )
    tax_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Tax Amount",
        default=0.00
    )
    grand_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Grand Total",
        default=0.00
    )
    
    # Terms and Status
    payment_terms = models.CharField(
        max_length=20,
        choices=PAYMENT_TERMS_CHOICES,
        default='NET_30',
        verbose_name="Payment Terms"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='DRAFT',
        verbose_name="PO Status"
    )

    admin_status = models.CharField(
        max_length=20,
        choices=ADMIN_STATUS_CHOICES,
        default='PENDING',
        verbose_name="Admin Approval Status",
        help_text="Administrative approval status for this purchase order"
    )
    
    # ✅ ADD OPTIONAL FIELDS for rejection/approval details
    admin_approved_by = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Approved By"
    )
    admin_approved_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Approval Date"
    )
    admin_rejection_reason = models.TextField(
        blank=True,
        verbose_name="Rejection Reason"
    )
    
    # Notes/Comments
    notes = models.TextField(blank=True, verbose_name="Additional Notes")
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ['-po_date', '-created_at']
        verbose_name = "Purchase Order"
        verbose_name_plural = "Purchase Orders"

    def __str__(self):
        return f"{self.po_number} - {self.supplier.name}"
    
    @staticmethod
    def generate_po_number():
        """
        Auto-generate PO number in format: PO-YYYYMMDD-001
        """
        from datetime import date
        today = date.today()
        prefix = f"PO-{today.strftime('%Y%m%d')}"
        
        # Get last PO number for today
        last_po = PurchaseOrder.objects.filter(
            po_number__startswith=prefix
        ).order_by('-po_number').first()
        
        if last_po:
            # Extract the sequence number and increment
            last_sequence = int(last_po.po_number.split('-')[-1])
            new_sequence = last_sequence + 1
        else:
            new_sequence = 1
        
        return f"{prefix}-{new_sequence:03d}"
    
    def save(self, *args, **kwargs):
        """
        Auto-calculate grand total before saving
        """
        self.grand_total = self.total_amount + self.tax_amount
        super().save(*args, **kwargs)

    def can_change_admin_status(self, user):
        """
        Check if user has permission to change admin status
        Only superadmin can change admin status
        """
        return user.is_authenticated and user.is_superuser
    
    def get_admin_status_display_with_icon(self):
        """Return admin status with appropriate icon"""
        icons = {
            'PENDING': '⏳',
            'APPROVED': '✅',
            'REJECTED': '❌'
        }
        return f"{icons.get(self.admin_status, '')} {self.get_admin_status_display()}"    

# ----------------- ITEM (PRODUCT) MASTER -----------------
class Item(models.Model):
    TAX_CHOICES = [
        (Decimal('5.00'), '5%'),
        (Decimal('18.00'), '18%'),
        (Decimal('28.00'), '28%'),
    ]
    
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    unit_of_measure = models.CharField(max_length=50, default='pcs')

    department = models.ForeignKey(
        'Department',
        on_delete=models.PROTECT,
        related_name='items',
        verbose_name="Department",
        help_text="Department this item belongs to",
        null=True,
        blank=True  # Make it optional initially
    )
    
    # New fields with defaults
    tax_percentage = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        choices=TAX_CHOICES,
        default=Decimal('18.00'),
        verbose_name="Tax Percentage"
    )
    mrp = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        validators=[MinValueValidator(Decimal('0.00'))],
        default=Decimal('0.00'),  # ADD THIS
        verbose_name="Maximum Retail Price"
    )
    purchase_price = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        validators=[MinValueValidator(Decimal('0.00'))],
        default=Decimal('0.00'),  # ADD THIS
        verbose_name="Purchase Price"
    )
    cost = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        validators=[MinValueValidator(Decimal('0.00'))],
        default=Decimal('0.00'),  # ADD THIS
        verbose_name="Cost Price"
    )
    hsn_code = models.CharField(max_length=50, blank=True, null=True, verbose_name="HSN Code")
    
    # Keep old unit_price if you want backward compatibility
    unit_price = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        validators=[MinValueValidator(Decimal('0.00'))],
        default=Decimal('0.00')
    )

    def __str__(self):
        return self.name
    
# ----------------- DEPARTMENT MASTER -----------------    
    
class Department(models.Model):
    """
    Department Master - Stores buyer department information
    This represents the buying department/organization details
    """
    # Basic Information
    name = models.CharField(max_length=100, unique=True, verbose_name="Department Name")
    
    # Address Details
    address = models.TextField(verbose_name="Department Address", default="Not Provided")
    city = models.CharField(max_length=60, verbose_name="City", default="Not Provided")
    state = models.CharField(max_length=60, verbose_name="State", default="Not Provided")
    pincode = models.CharField(max_length=20, verbose_name="Pincode", default="Not Provided")
    
    # Contact Information
    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
    )
    contact_number = models.CharField(
        validators=[phone_regex],
        max_length=15,
        verbose_name="Contact Number", default="Not Provided"
    )
    alternate_number = models.CharField(
        validators=[phone_regex],
        max_length=15,
        blank=True,
        verbose_name="Alternate Number", default="Not Provided"
    )
    email = models.EmailField(max_length=100, blank=True, verbose_name="Email ID", default="Not Provided")
    
    # Business Details
    gst_number = models.CharField(
        max_length=15,
        blank=True,
        verbose_name="GST Number",
        help_text="15-character GST Number", default="Not Provided"
    )
    
    # Metadata
    is_active = models.BooleanField(default=True, verbose_name="Active Status")
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        ordering = ['name']
        verbose_name = "Department"
        verbose_name_plural = "Departments"

    def __str__(self):
        return self.name
    
    def get_full_address(self):
        """Returns formatted full address for delivery"""
        return f"{self.address}\n{self.city}, {self.state} - {self.pincode}"


# ----------------- PURCHASE ORDER LINE ITEMS -----------------
class PurchaseOrderItem(models.Model):
    purchase_order = models.ForeignKey('PurchaseOrder', on_delete=models.CASCADE, related_name='po_items')
    item = models.ForeignKey(Item, on_delete=models.PROTECT)
    department = models.ForeignKey(Department, on_delete=models.PROTECT, null=True,blank=True)  # NEW
    quantity = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    line_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    def save(self, *args, **kwargs):
        subtotal = (self.quantity * self.unit_price) - self.discount
        tax_amt = subtotal * (self.tax_percent / 100)
        self.line_total = subtotal + tax_amt
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.item.name} ({self.quantity})"      

    @staticmethod
    def generate_po_number():
        """
        Auto-generate PO number in format: PO-YYYYMMDD-001
        """
        from datetime import date
        today = date.today()
        prefix = f"PO-{today.strftime('%Y%m%d')}"
        
        # Get last PO number for today
        last_po = PurchaseOrder.objects.filter(
            po_number__startswith=prefix
        ).order_by('-po_number').first()
        
        if last_po:
            # Extract the sequence number and increment
            last_sequence = int(last_po.po_number.split('-')[-1])
            new_sequence = last_sequence + 1
        else:
            new_sequence = 1
        
        return f"{prefix}-{new_sequence:03d}"  
    
    