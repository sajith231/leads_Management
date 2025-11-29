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

class Item(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
    

    class Meta:
        ordering = ['name']

# Supplier
class Supplier(models.Model):
    name = models.CharField(max_length=200)
    place = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True, verbose_name="Active Status",help_text="Whether this supplier is currently active")
    phone = models.CharField(max_length=15)
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
from django.db import models
from django.utils import timezone

# app5/models.py
from django.db import models
from django.utils import timezone
from django.conf import settings

from django.db import models, IntegrityError, transaction
from django.conf import settings
from django.utils import timezone
import uuid

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

    assignment_type = models.CharField(
        max_length=20, choices=ASSIGNMENT_CHOICES, default='unassigned'
    )
    ticket_number = models.CharField(max_length=30, unique=True, blank=True)
    ownerName = models.CharField(max_length=100)
    phoneNo = models.CharField(max_length=15)
    email = models.EmailField(blank=True, null=True)
    customerType = models.CharField(max_length=20, default='Business')

    # Business fields
    name = models.CharField(max_length=100, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    place = models.CharField(max_length=100, blank=True, null=True)
    District = models.CharField(max_length=100, blank=True, null=True)
    State = models.CharField(max_length=100, blank=True, null=True)
    pinCode = models.CharField(max_length=10, blank=True, null=True)

    # Individual fields
    firstName = models.CharField(max_length=100, blank=True, null=True)
    lastName = models.CharField(max_length=100, blank=True, null=True)
    individualAddress = models.TextField(blank=True, null=True)
    individualPlace = models.CharField(max_length=100, blank=True, null=True)
    individualDistrict = models.CharField(max_length=100, blank=True, null=True)
    individualState = models.CharField(max_length=100, blank=True, null=True)
    individualPinCode = models.CharField(max_length=10, blank=True, null=True)

    # Business information
    status = models.CharField(max_length=20, default='Active')
    priority = models.CharField( max_length=20,choices=PRIORITY_CHOICES,default='High',help_text="Lead priority level")
    refFrom = models.CharField(max_length=100, blank=True, null=True)
    business = models.CharField(max_length=100, blank=True, null=True)
    campaign = models.CharField(max_length=255, blank=True, null=True)
    marketedBy = models.CharField(max_length=100, blank=True, null=True)
    Consultant = models.CharField(max_length=100, blank=True, null=True)
    requirement = models.CharField(max_length=100, blank=True, null=True)
    details = models.TextField(blank=True, null=True)
    date = models.DateField(default=timezone.now)

    # Assignment fields
    
    assigned_to_name = models.CharField(max_length=150, blank=True, null=True)
    assigned_by_name = models.CharField(max_length=150, blank=True, null=True)
    assigned_date = models.DateField(null=True, blank=True)
    assigned_time = models.TimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        """
        Generate ticket if missing: TKT-YYYYMMDD-XXXX
        Use retry loop to avoid unique constraint errors under concurrency.
        Fall back to UUID suffix if retries exhausted.
        """
        if not self.ticket_number:
            date_part = timezone.now().strftime('%Y%m%d')
            max_attempts = 5

            for attempt in range(max_attempts):
                # compute sequential part based on how many leads exist today
                today_count = Lead.objects.filter(created_at__date=timezone.now().date()).count()
                seq = str(today_count + 1).zfill(4)
                candidate = f"TKT-{date_part}-{seq}"
                self.ticket_number = candidate

                try:
                    # Try to save within a transaction; IntegrityError means collision
                    with transaction.atomic():
                        super().save(*args, **kwargs)
                    return  # saved successfully
                except IntegrityError:
                    # collision — try again (recompute count)
                    if attempt == max_attempts - 1:
                        # last attempt failed — fall back to UUID-style ticket and save once
                        fallback_suffix = uuid.uuid4().hex[:6].upper()
                        self.ticket_number = f"TKT-{date_part}-{fallback_suffix}"
                        with transaction.atomic():
                            super().save(*args, **kwargs)
                        return
                    # otherwise loop and retry

        else:
            # ticket already present (manual or editing) — normal save
            super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.ticket_number} - {self.ownerName}"

    @property
    def display_name(self):
        if self.customerType == 'Business':
            return self.name or self.ownerName
        return f"{self.firstName or ''} {self.lastName or ''}".strip() or self.ownerName


from django.db import models

class RequirementItem(models.Model):
    # Basic item information
    item_name = models.CharField(max_length=200, verbose_name="Item Name")
    
    # Customer/owner information (ADDED THESE FIELDS)
    owner_name = models.CharField(max_length=255, blank=True, null=True, verbose_name="Owner Name")
    phone_no = models.CharField(max_length=20, blank=True, null=True, verbose_name="Phone Number")
    email = models.EmailField(blank=True, null=True, verbose_name="Email Address")
    
    # Item details
    unit = models.CharField(max_length=50, blank=True, null=True, verbose_name="Unit")
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Price")
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name="Total")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Requirement Item"
        verbose_name_plural = "Requirement Items"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.item_name} - {self.owner_name or 'No Owner'}"
    
    def save(self, *args, **kwargs):
        # Auto-calculate total if needed, or you can remove this
        if not self.total:
            self.total = self.price
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

    
         


        



