# models.py (updated)
from django.db import models
from django.contrib.auth.models import User
import uuid
import os
from django.utils import timezone
from app1.models import User 
class JobCard(models.Model):
    STATUS_CHOICES = [
        ('logged', 'Logged'),
        ('sent_technician', 'Sent To Technician'),
        ('accepted', 'In Technician Hand'),  # Added from second version
        ('pending', 'Pending'),  # From first version
        ('completed', 'Completed'),
        ('returned', 'Returned'),
        ('rejected', 'Rejected'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),  # Added from second version
        ('medium', 'Medium'),
        ('high', 'High'),
    ]

    # Core job card information
    ticket_no = models.CharField(max_length=20, unique=True, blank=True)
    customer = models.CharField(max_length=200)  # Increased length from second version
    address = models.TextField()
    phone = models.CharField(max_length=50)  # Kept longer length from first version
    
    # Status and priority
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='logged'
    )
    priority = models.CharField(
        max_length=10, 
        choices=PRIORITY_CHOICES, 
        default='medium'
    )
    
    # Technician assignment
    technician = models.CharField(max_length=100, blank=True, null=True)
    assigned_date = models.DateTimeField(null=True, blank=True)
    self_assigned = models.BooleanField(
        default=False, 
        help_text="True if the job was self-assigned by the creator"
    )
    
    # Equipment tracking
    standby_issued = models.BooleanField(
        default=False, 
        help_text="Whether standby equipment was issued"
    )
    
    # JSON data storage
    items_data = models.JSONField(
        default=list, 
        blank=True,
        help_text="Stores array of items with their complaints"
    )
    completion_details = models.JSONField(default=dict, blank=True, null=True)
    
    # Audit fields
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="jobcards"  # Consistent naming
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.ticket_no} - {self.customer}"  # Consistent format

    def save(self, *args, **kwargs):
        # Generate ticket number if not exists
        if not self.ticket_no:
            # Try the sequential numbering first (from second version)
            last_job = JobCard.objects.order_by('-id').first()
            if last_job and last_job.ticket_no and last_job.ticket_no.startswith('JC'):
                try:
                    digits = ''.join(filter(str.isdigit, last_job.ticket_no))
                    if digits:
                        number = int(digits)
                        self.ticket_no = f"JC{number + 1:06d}"
                except (ValueError, TypeError):
                    # Fallback to UUID method if sequential fails
                    self.ticket_no = self._generate_uuid_ticket()
            else:
                # Use UUID method as fallback (from first version)
                self.ticket_no = self._generate_uuid_ticket()

        # Set assigned_date when technician is assigned
        if self.technician and not self.assigned_date:
            self.assigned_date = timezone.now()
            
        super().save(*args, **kwargs)

    def _generate_uuid_ticket(self):
        """Generate ticket number using UUID method"""
        while True:
            ticket_no = f"TK-{uuid.uuid4().hex[:8].upper()}"
            if not JobCard.objects.filter(ticket_no=ticket_no).exists():
                return ticket_no

    def delete(self, *args, **kwargs):
        # Delete all associated images before deleting job card
        for image in self.images.all():
            image.delete()
        super().delete(*args, **kwargs)

    # Utility methods from first version
    def get_total_items(self):
        """Return total number of items in this job card"""
        return len(self.items_data) if self.items_data else 0

    def get_total_complaints(self):
        """Return total number of complaints across all items"""
        total = 0
        if self.items_data:
            for item in self.items_data:
                total += len(item.get('complaints', []))
        return total

    def get_items_list(self):
        """Return list of item names"""
        if self.items_data:
            return [item.get('item', '') for item in self.items_data]
        return []

    def get_all_complaints_text(self):
        """Return formatted string of all complaints"""
        complaints = []
        if self.items_data:
            for item in self.items_data:
                item_name = item.get('item', 'Unknown')
                for complaint in item.get('complaints', []):
                    desc = complaint.get('description', '')
                    if desc:
                        complaints.append(f"{item_name}: {desc}")
        return '; '.join(complaints) if complaints else 'No complaints'

    @property
    def is_assigned(self):
        """Check if job card is assigned to a technician"""
        return bool(self.technician)

    @property
    def can_be_completed(self):
        """Check if job card can be marked as completed"""
        return self.status in ['sent_technician', 'accepted', 'pending']


class JobCardImage(models.Model):
    jobcard = models.ForeignKey(
        JobCard, 
        related_name='images', 
        on_delete=models.CASCADE
    )
    image = models.ImageField(upload_to='jobcard_images/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    # Additional fields to identify which item and complaint this image belongs to
    item_index = models.IntegerField(
        default=0, 
        help_text="Index of item in items_data array"
    )
    complaint_index = models.IntegerField(
        default=0, 
        help_text="Index of complaint within item"
    )

    def __str__(self):
        return f"Image for {self.jobcard.customer} - {self.jobcard.ticket_no}"

    def delete(self, *args, **kwargs):
        # Delete the actual image file from storage
        if self.image and os.path.isfile(self.image.path):
            os.remove(self.image.path)
        super().delete(*args, **kwargs)

    class Meta:
        ordering = ['item_index', 'complaint_index', 'uploaded_at']   


class StandbyIssuance(models.Model):
    STATUS_CHOICES = [
        ('issued', 'Issued'),
        ('returned', 'Returned'),
        ('lost', 'Lost'),
        ('damaged', 'Damaged'),
    ]

    standby_item = models.ForeignKey('app2.StandbyItem', on_delete=models.CASCADE, related_name='issuances')
    job_card = models.ForeignKey(JobCard, on_delete=models.CASCADE, related_name='standby_issuances')
    issued_to = models.CharField(max_length=200)  # Customer name
    issued_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='issued_standby_items')
    issued_date = models.DateTimeField(default=timezone.now)
    expected_return_date = models.DateTimeField()
    actual_return_date = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='issued')
    notes = models.TextField(blank=True)
    
    # Condition tracking
    condition_on_issue = models.TextField(blank=True, help_text="Condition notes when issued")
    condition_on_return = models.TextField(blank=True, help_text="Condition notes when returned")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.standby_item.name} issued to {self.issued_to}"

    class Meta:
        ordering = ['-issued_date']
        verbose_name = 'Standby Issuance'
        verbose_name_plural = 'Standby Issuances'

    def is_overdue(self):
        if self.status == 'issued' and self.expected_return_date:
            return timezone.now() > self.expected_return_date
        return False

    def save(self, *args, **kwargs):
        # Update job card standby_issued status based on issuance status
        if self.job_card:
            if self.status == 'issued':
                self.job_card.standby_issued = True
            elif self.status in ['returned', 'lost', 'damaged']:
                self.job_card.standby_issued = False
            self.job_card.save()
        
        super().save(*args, **kwargs)
# item

# 在 models.py 中找到 Item 类，修改为：
class Item(models.Model):
    SECTION_CHOICES = [
        ('GENERAL', 'General'),
        ('HARDWARE', 'Hardware'),
        ('SOFTWARE', 'Software'),
        ('PAPER_ROLLS', 'Paper Rolls'),
        ('OTHER', 'Other'),
    ]
    
    name = models.CharField(max_length=100, unique=True)
    section = models.CharField(
        max_length=50, 
        choices=SECTION_CHOICES, 
        default='GENERAL',
        verbose_name="Section"
    )
    unit_of_measure = models.CharField(
        max_length=50, 
        default='pcs',
        verbose_name="Unit of Measure"
    )
    mrp = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0.00,
        verbose_name="Maximum Retail Price"
    )
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.get_section_display()}"

    class Meta:
        ordering = ['section', 'name']

# Supplier
class Supplier(models.Model):
    name = models.CharField(max_length=200)
    place = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True, verbose_name="Active Status",help_text="Whether this supplier is currently active")
    phone = models.CharField(max_length=30)
    address = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']

# Update your app5/models.py WarrantyTicket model

class WarrantyTicket(models.Model):
    """Warranty claim tickets"""
    ticket_no = models.CharField(max_length=50, unique=True)
    jobcard = models.ForeignKey(JobCard, on_delete=models.CASCADE, related_name='warranty_tickets')
    
    # ✅ UPDATED: Reference purchase_order.Supplier instead of app5.Supplier
    supplier = models.ForeignKey(
        'purchase_order.Supplier',  # Changed from 'Supplier'
        on_delete=models.CASCADE, 
        related_name='warranty_tickets',
        null=True,
        blank=True
    )
    
    # Selected warranty item
    selected_item = models.CharField(max_length=200)
    item_serial = models.CharField(max_length=100, blank=True, null=True)
    
    # Status
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('submitted', 'Sent to Supplier'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('completed', 'Completed'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Dates
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    submitted_at = models.DateTimeField(blank=True, null=True)
    resolved_at = models.DateTimeField(blank=True, null=True)
    
    # Additional information
    issue_description = models.TextField(blank=True, null=True)
    supplier_response = models.TextField(blank=True, null=True)
    resolution_notes = models.TextField(blank=True, null=True)
    
    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['selected_item', 'item_serial', 'status'],
                condition=models.Q(status__in=['pending', 'submitted', 'approved']),
                name='unique_active_warranty_per_item'
            )
        ]

    def __str__(self):
        return f"WT-{self.ticket_no} - {self.selected_item}"

    @property
    def customer_name(self):
        return self.jobcard.customer if self.jobcard else ''

    @property
    def customer_phone(self):
        return self.jobcard.phone if self.jobcard else ''


class WarrantyItemLog(models.Model):
    """Log of warranty item processing history"""
    warranty_ticket = models.ForeignKey(WarrantyTicket, on_delete=models.CASCADE, related_name='logs')
    action = models.CharField(max_length=100)
    description = models.TextField()
    performed_by = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.warranty_ticket.ticket_no} - {self.action}"
    


    # ADD TO YOUR EXISTING models.py FILE

from django.db import models
from django.contrib.auth.models import User
import os

class ReturnItem(models.Model):
    """
    Model to track returned warranty items
    """
    warranty_ticket = models.OneToOneField(
        'WarrantyTicket', 
        on_delete=models.CASCADE,
        related_name='return_item'
    )
    return_date = models.DateField()
    notes = models.TextField(blank=True, null=True)
    returned_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Return for {self.warranty_ticket.ticket_no}"
    
    class Meta:
        verbose_name = "Return Item"
        verbose_name_plural = "Return Items"
        ordering = ['-return_date', '-created_at']


def return_image_upload_path(instance, filename):
    """Generate upload path for return images"""
    ticket_no = instance.return_item.warranty_ticket.ticket_no
    return f'returns/{ticket_no}/{filename}'


class ReturnImage(models.Model):
    """
    Model to store multiple images for return items
    """
    return_item = models.ForeignKey(
        ReturnItem, 
        on_delete=models.CASCADE, 
        related_name='images'
    )
    image = models.ImageField(upload_to=return_image_upload_path)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Image for {self.return_item.warranty_ticket.ticket_no}"
    
    def delete(self, *args, **kwargs):
        # Delete the image file when the model is deleted
        if self.image:
            if os.path.isfile(self.image.path):
                os.remove(self.image.path)
        super().delete(*args, **kwargs)


# Alternative normalized approach
class ServiceBilling(models.Model):
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('partial', 'Partial Payment'),
    ]
    
    # Basic information
    ticket_no = models.CharField(max_length=20)
    date = models.DateField(default=timezone.now)
    customer_name = models.CharField(max_length=100)
    customer_contact = models.CharField(max_length=25)
    customer_address = models.TextField()
    technician = models.CharField(max_length=100)
    
    # Financial information
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Additional information
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    notes = models.TextField(blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Service Billing"
        verbose_name_plural = "Service Billings"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"INV-{self.ticket_no} - {self.customer_name} - ₹{self.total}"
    
    def calculate_totals(self):
        """Calculate subtotal, tax, and total based on service items"""
        items = self.service_items.all()
        self.subtotal = sum(item.charge for item in items)
        self.tax = self.subtotal * 0.1  # 10% tax
        self.total = self.subtotal + self.tax
        self.save()

class ServiceItem(models.Model):
    SERVICE_STATUS_CHOICES = [
        ('Payment', 'Payment'),
        ('Free', 'Free'),
    ]
    
    billing = models.ForeignKey(ServiceBilling, on_delete=models.CASCADE, related_name='service_items')
    item_name = models.CharField(max_length=100)
    serial_no = models.CharField(max_length=50, blank=True, null=True)
    service_description = models.TextField()
    charge = models.DecimalField(max_digits=10, decimal_places=2)
    service_status = models.CharField(
        max_length=20, 
        choices=SERVICE_STATUS_CHOICES, 
        default='Payment',
        help_text="Whether this service is paid or free"
    )
    def __str__(self):
        return f"{self.item_name} - ₹{self.charge}"   


# lead

# Add this to your models.py
from django.db import models


# models.py
import uuid
from django.db import models, IntegrityError, transaction
from django.utils import timezone
from app1.models import User 

class Lead(models.Model):

    ASSIGNMENT_CHOICES = [
        ('self_assigned', 'Self Assigned'),
        ('unassigned', 'Unassigned'),
    ]

    PRIORITY_CHOICES = [
        ('High', 'High'),
        ('Medium', 'Medium'),
        ('Low', 'Low'),
    ]

    # ----------------------------
    # CUSTOMER TYPE (TOGGLE)
    # ----------------------------
    customerType = models.CharField(
        max_length=20,
        default='Business',   # Business or Individual
        help_text="Determines which input group to show"
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="leads"
    )

    # ----------------------------
    # COMMON FIELDS
    # ----------------------------
    ticket_number = models.CharField(max_length=30, unique=True, blank=True)
    ownerName = models.CharField(max_length=100)
    phoneNo = models.CharField(max_length=30)
    email = models.EmailField(blank=True, null=True)

    # =====================================================
    # BUSINESS FIELDS
    # =====================================================
    name = models.CharField(max_length=100, blank=True, null=True)  # Business Name
    address = models.TextField(blank=True, null=True)
    place = models.CharField(max_length=100, blank=True, null=True)
    District = models.CharField(max_length=100, blank=True, null=True)
    State = models.CharField(max_length=100, blank=True, null=True)
    pinCode = models.CharField(max_length=10, blank=True, null=True)

    # =====================================================
    # INDIVIDUAL FIELDS
    # =====================================================
    firstName = models.CharField(max_length=100, blank=True, null=True)
    lastName = models.CharField(max_length=100, blank=True, null=True)
    individualAddress = models.TextField(blank=True, null=True)
    individualPlace = models.CharField(max_length=100, blank=True, null=True)
    individualDistrict = models.CharField(max_length=100, blank=True, null=True)
    individualState = models.CharField(max_length=100, blank=True, null=True)
    individualPinCode = models.CharField(max_length=10, blank=True, null=True)

    # =====================================================
    # GENERAL LEAD INFO
    # =====================================================
    status = models.CharField(max_length=20, default='Active')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='High')

    refFrom = models.CharField(max_length=100, blank=True, null=True)
    business = models.CharField(max_length=100, blank=True, null=True)
    campaign = models.CharField(max_length=255, blank=True, null=True)
    marketedBy = models.CharField(max_length=100, blank=True, null=True)
    Consultant = models.CharField(max_length=100, blank=True, null=True)
    requirement = models.CharField(max_length=100, blank=True, null=True)
    details = models.TextField(blank=True, null=True)
    date = models.DateField(default=timezone.now)

    # =====================================================
    # ASSIGNMENT INFO
    # =====================================================
    assignment_type = models.CharField(
        max_length=20,
        choices=ASSIGNMENT_CHOICES,
        default='unassigned'
    )

    assigned_to_name = models.CharField(max_length=150, blank=True, null=True)
    assigned_by_name = models.CharField(max_length=150, blank=True, null=True)
    assigned_date = models.DateField(null=True, blank=True)
    assigned_time = models.TimeField(null=True, blank=True)

    # =====================================================
    # META FIELDS
    # =====================================================
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # =====================================================
    # AUTO TICKET NUMBER GENERATION
    # =====================================================
    def save(self, *args, **kwargs):
        if not self.ticket_number:
            date_part = timezone.now().strftime('%Y%m%d')

            for attempt in range(5):
                today_count = Lead.objects.filter(
                    created_at__date=timezone.now().date()
                ).count()
                seq = str(today_count + 1).zfill(4)
                trial = f"TKT-{date_part}-{seq}"

                self.ticket_number = trial

                try:
                    with transaction.atomic():
                        super().save(*args, **kwargs)
                    return
                except IntegrityError:
                    continue

            # FINAL FALLBACK
            fallback = uuid.uuid4().hex[:6].upper()
            self.ticket_number = f"TKT-{date_part}-{fallback}"
            with transaction.atomic():
                super().save(*args, **kwargs)

        else:
            super().save(*args, **kwargs)


@property
@property
def requirements_json(self):
    """Return requirements as JSON string"""
    import json
    
    requirements = []
    try:
        # Get all requirements linked to this lead
        for req in self.requirements.all():
            req_dict = {
                'id': req.id,
                'item_id': req.item.id if req.item else None,
                'item_name': req.item_name,
                'section': req.section or '',
                'unit': req.unit or '',
                'price': float(req.price) if req.price else 0.0,
                'quantity': req.quantity if req.quantity else 1,
                'total': float(req.total) if req.total else 0.0,
            }
            requirements.append(req_dict)
            
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error building requirements JSON for lead {self.id}: {e}")
        return '[]'
    
    return json.dumps(requirements)

@property
def requirements_count(self):
    """Return count of requirements"""
    try:
        return self.requirements.count()
    except:
        return 0

    # =====================================================
    # SMART DISPLAY NAME FOR DIRECTORY
    # =====================================================
    @property
    def display_name(self):
        if self.customerType == "Business":
            return self.name or self.ownerName
        else:
            fullname = f"{self.firstName or ''} {self.lastName or ''}".strip()
            return fullname or self.ownerName

    def __str__(self):
        return f"{self.ticket_number} - {self.display_name}"




from django.db import models

class RequirementItem(models.Model):
    # ForeignKey relationships
    lead = models.ForeignKey(
        Lead, 
        on_delete=models.CASCADE, 
        related_name='requirements',
        null=True,  # Allow null for backward compatibility
        blank=True
    )
    item = models.ForeignKey(
        'purchase_order.Item',  # Add this ForeignKey!
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Item"
    )
    
    # Basic item information
    item_name = models.CharField(max_length=200, verbose_name="Item Name")
    
    # Customer/owner information
    ticket_number = models.CharField(max_length=50, blank=True, null=True, verbose_name="Ticket Number")
    owner_name = models.CharField(max_length=255, blank=True, null=True, verbose_name="Owner Name")
    phone_no = models.CharField(max_length=20, blank=True, null=True, verbose_name="Phone Number")
    email = models.EmailField(blank=True, null=True, verbose_name="Email Address")
    
    # Item details
    section = models.CharField(max_length=255, null=True, blank=True)
    unit = models.CharField(max_length=50, blank=True, null=True, verbose_name="Unit")
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Price")
    quantity = models.IntegerField(default=1, verbose_name="Quantity")
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name="Total")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.item_name} - {self.lead.ticket_number if self.lead else 'No Lead'}"
    
    def save(self, *args, **kwargs):
        # Auto-calculate total
        self.total = self.price * self.quantity
        super().save(*args, **kwargs)
# bussiness nature

class BusinessNature(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name
    

   
# state model
class StateMaster(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="State Name")
    description = models.TextField(blank=True, null=True, verbose_name="Description")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'state_master'
        verbose_name = 'State Master'
        verbose_name_plural = 'State Masters'
        ordering = ['name']
    
    def __str__(self):
        return self.name
    

from django.db import models

class Reference(models.Model):
    ref_name = models.CharField(max_length=255, verbose_name="Reference Name")
    description = models.TextField(blank=True, null=True, verbose_name="Description")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'reference_master'
        verbose_name = 'Reference'
        verbose_name_plural = 'References'

    def __str__(self):
        return self.ref_name
    


    # Add these models to your app5/quotation models.py file

from django.db import models
from django.utils import timezone
from purchase_order.models import Item

class Quotation(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('expired', 'Expired'),
    ]
    
    # Quotation identification
    quotation_number = models.CharField(max_length=50, unique=True)
    
    # Lead reference
    lead = models.ForeignKey(
        'Lead', 
        on_delete=models.CASCADE, 
        related_name='quotations',
        null=True,
        blank=True
    )
    
    # Client information
    client_name = models.CharField(max_length=200)
    client_phone = models.CharField(max_length=20)
    client_email = models.EmailField(blank=True, null=True)
    company_name = models.CharField(max_length=200, blank=True, null=True)
    
    # Quotation details
    quotation_date = models.DateField(default=timezone.now)
    valid_until = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    
    # Financial details
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_discount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_tax = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    grand_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Additional information
    notes = models.TextField(blank=True, null=True)
    terms_conditions = models.TextField(blank=True, null=True)

    # Proposal document attachment
    # FIX: Added missing FileField — the view calls quotation.proposal_attachment.save(...)
    # but the field didn't exist, causing an AttributeError on every file upload.
    proposal_attachment = models.FileField(
        upload_to='quotation_proposals/',
        blank=True,
        null=True,
        help_text="Optional proposal document (PDF, Word, etc.) attached to this quotation"
    )
    
    # Metadata
    created_by = models.ForeignKey(
        'app1.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_quotations'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Quotation'
        verbose_name_plural = 'Quotations'
    
    def __str__(self):
        return f"{self.quotation_number} - {self.client_name}"
    
    @property
    def is_expired(self):
        """Check if quotation has expired"""
        return timezone.now().date() > self.valid_until
    
    def save(self, *args, **kwargs):
        # Auto-generate quotation number if not provided
        if not self.quotation_number:
            from django.db.models import Max
            last_quote = Quotation.objects.aggregate(Max('id'))['id__max'] or 0
            self.quotation_number = f"QT-{timezone.now().strftime('%Y%m%d')}-{(last_quote + 1):04d}"
        super().save(*args, **kwargs)


class QuotationItem(models.Model):
    quotation = models.ForeignKey(
        Quotation,
        on_delete=models.CASCADE,
        related_name='items'
    )
    
    # Item reference
    item = models.ForeignKey(
        'purchase_order.Item',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    item_name = models.CharField(max_length=200)  # Snapshot of item name
    
    # Item details
    description = models.TextField(blank=True, null=True)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    unit = models.CharField(max_length=50, default='pcs')
    
    # Pricing
    entry_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    sales_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Discounts and taxes
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Total
    line_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Additional info
    hsn_code = models.CharField(max_length=20, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    
    # Order
    order = models.PositiveIntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['order', 'id']
        verbose_name = 'Quotation Item'
        verbose_name_plural = 'Quotation Items'
    
    def __str__(self):
        return f"{self.item_name} - Qty: {self.quantity}"
    
    def calculate_totals(self):
        """Calculate all totals for this item"""
        # Use sales_price as base, fallback to unit_price
        base_price = self.sales_price if self.sales_price > 0 else self.unit_price
        
        # Calculate discount
        self.discount_amount = (base_price * self.quantity) * (self.discount_percentage / 100)
        
        # Calculate amount after discount
        amount_after_discount = (base_price * self.quantity) - self.discount_amount
        
        # Calculate tax
        self.tax_amount = amount_after_discount * (self.tax_percentage / 100)
        
        # Calculate line total
        self.line_total = amount_after_discount + self.tax_amount
        
        return self.line_total
    
    def save(self, *args, **kwargs):
        # FIX: The original code called calculate_totals() unconditionally, which
        # overwrote the precise figures already computed by quotation_submit view
        # before calling QuotationItem.objects.create(...).
        #
        # New behaviour:
        #   - New record with line_total still at default 0  → auto-calculate
        #     (covers direct admin / shell creation where no totals are supplied).
        #   - New record where caller already set line_total  → trust the caller.
        #   - Existing record being updated                   → recalculate so
        #     edits to price/qty/discount/tax stay consistent.
        if self.pk:
            # Existing record: always recalculate to stay in sync with any
            # field edits (e.g. via admin or an update view).
            self.calculate_totals()
        elif self.line_total == 0:
            # New record with no externally provided total: auto-calculate.
            self.calculate_totals()
        # else: new record with a caller-supplied line_total — leave it alone.

        super().save(*args, **kwargs)



from django.db import models
from django.conf import settings

class FollowUp(models.Model):
   
    
    STATUS_CHOICES = [
        ('Accepted', 'Accepted'),
        ('Follow-up Required', 'Follow-up Required'),
        ('Not Attanted', 'Not Attanted'),
        ('Proposal Sent', 'Proposal Sent'),
        ('On Hold', 'On Hold'),
        ('Rejected', 'Rejected'),
    ]
    
    CONTACT_METHOD_CHOICES = [
        ('Phone Call', 'Phone Call'),
        ('WhatsApp', 'WhatsApp'),
        ('Email', 'Email'),
        ('SMS', 'SMS'),
        ('In-Person Meeting', 'In-Person Meeting'),
        ('Other', 'Other'),
    ]
    
    # Core fields
    lead = models.ForeignKey('Lead', on_delete=models.CASCADE, related_name='followups')
    follow_up_date = models.DateField()
    contact_method = models.CharField(max_length=50, choices=CONTACT_METHOD_CHOICES)
    reply = models.TextField(help_text="Remarks or notes from the conversation")
    status = models.CharField(max_length=50, choices=STATUS_CHOICES)
    notes = models.TextField(blank=True, null=True, help_text="Additional notes")
    
    # Track which requirement items this follow-up is for
    selected_requirement_items = models.TextField(
        blank=True, 
        null=True,
        help_text="Comma-separated list of requirement items that need follow-up"
    )
    
    # Conditional fields (required for certain statuses)
    assigned_to = models.CharField(max_length=100, blank=True, null=True)
    next_follow_up_date = models.DateField(blank=True, null=True)
    next_action = models.CharField(max_length=255, blank=True, null=True)
    
    # Metadata
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='created_followups'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-follow_up_date', '-created_at']
        verbose_name = 'Follow Up'
        verbose_name_plural = 'Follow Ups'
    
    def __str__(self):
        ticket = self.lead.ticket_number if hasattr(self.lead, 'ticket_number') else f"LD-{self.lead.id}"
        return f"Follow-up for {ticket} on {self.follow_up_date}"
    
    def save(self, *args, **kwargs):
        # Follow-up status is independent — lead status is NOT updated here
        super().save(*args, **kwargs)

    

    
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class Customer(models.Model):
    name = models.CharField(max_length=200)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    pincode = models.CharField(max_length=10, blank=True)
    gst_number = models.CharField(max_length=15, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ['name']


class SalesOrder(models.Model):
    # Add PAYMENT_TERMS choices
    PAYMENT_TERMS = [
        ('DUE_ON_RECEIPT', 'Due on Receipt'),
        ('NET_15', 'Net 15 Days'),
        ('NET_30', 'Net 30 Days'),
        ('NET_45', 'Net 45 Days'),
        ('NET_60', 'Net 60 Days'),
    ]
    
    # Add CALCULATION_METHODS choices
    CALCULATION_METHODS = [
        ('STANDARD', 'Standard Calculation'),
        ('TAX_INCLUSIVE', 'Tax Inclusive'),
        ('TAX_EXCLUSIVE', 'Tax Exclusive'),
        ('DISCOUNT_FIRST', 'Discount First'),
        ('DISCOUNT_LAST', 'Discount Last'),
        ('CUSTOM', 'Custom Calculation'),
    ]
    
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('PENDING', 'Pending'),
        ('CONFIRMED', 'Confirmed'),
        ('PROCESSING', 'Processing'),
        ('SHIPPED', 'Shipped'),
        ('DELIVERED', 'Delivered'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    ]
    
    PAYMENT_STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PARTIAL', 'Partial'),
        ('PAID', 'Paid'),
    ]

    # ── NEW ───────────────────────────────────────────────────────────────────
    APPROVAL_STATUS_CHOICES = [
        ('pending',  'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    # ─────────────────────────────────────────────────────────────────────────
    
    so_number = models.CharField(max_length=50, unique=True)
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name='sales_orders')
    so_date = models.DateField(default=timezone.now)
    delivery_date = models.DateField(null=True, blank=True)
    reference_number = models.CharField(max_length=100, blank=True)
    
    payment_terms = models.CharField(
        max_length=20, 
        choices=PAYMENT_TERMS, 
        default='NET_30',
        blank=True,
        null=True
    )
    
    calculation_method = models.CharField(
        max_length=20, 
        choices=CALCULATION_METHODS, 
        default='STANDARD',
        blank=True,
        null=True
    )
    
    from_department = models.ForeignKey(
        'purchase_order.Department', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='sales_orders_from'
    )
    
    to_department = models.ForeignKey(
        'purchase_order.Department', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='sales_orders_to'
    )
    
    # Financial fields
    subtotal = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    grand_total = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    # Status fields
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='PENDING')

    # ── NEW ───────────────────────────────────────────────────────────────────
    approval_status = models.CharField(
        max_length=20,
        choices=APPROVAL_STATUS_CHOICES,
        default='pending',
    )
    # ─────────────────────────────────────────────────────────────────────────
    
    # Additional fields
    notes = models.TextField(blank=True)
    terms_conditions = models.TextField(blank=True)
    
    # Tracking fields
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_sales_orders')
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='updated_sales_orders')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.so_number
    
    class Meta:
        ordering = ['-so_date', '-so_number']
        indexes = [
            models.Index(fields=['so_number']),
            models.Index(fields=['status']),
            models.Index(fields=['so_date']),
        ]
    
    def save(self, *args, **kwargs):
        if not self.so_number:
            year = timezone.now().year
            last_order = SalesOrder.objects.filter(
                so_number__startswith=f'SO-{year}'
            ).order_by('so_number').last()
            
            if last_order:
                last_number = int(last_order.so_number.split('-')[-1])
                new_number = last_number + 1
            else:
                new_number = 1
            
            self.so_number = f'SO-{year}-{new_number:05d}'
        
        super().save(*args, **kwargs)


# In your models.py file, add or update the OrderItem model

class OrderItem(models.Model):
    # Foreign Keys
    sales_order = models.ForeignKey(SalesOrder, on_delete=models.CASCADE, related_name='items')
    item = models.ForeignKey(Item, on_delete=models.SET_NULL, null=True, blank=True, related_name='order_items')
    
    # Item details
    product_name = models.CharField(max_length=255, blank=True)
    
    # Quantity and pricing fields
    quantity = models.DecimalField(max_digits=15, decimal_places=2, default=1)
    entry_rate = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    sales_price = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    unit_price = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    item_cost = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    margin = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    tax = models.DecimalField(max_digits=5, decimal_places=2, default=0)  # Tax percentage
    total = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    # Optional fields
    description = models.TextField(blank=True)
    
    # Tracking
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.product_name} - {self.quantity} x {self.unit_price}"
    
    class Meta:
        ordering = ['id']         


        

from django.db import models

class TaxMaster(models.Model):
    name = models.CharField(max_length=100, unique=True)
    percentage = models.DecimalField(max_digits=5, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.percentage}%)"

    class Meta:
        ordering = ['name']
        verbose_name = 'Tax Master'
        verbose_name_plural = 'Tax Masters'

