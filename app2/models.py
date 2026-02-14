
# models.py
from django.db import models

class Field(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name


class Credentials(models.Model):
    name = models.CharField(max_length=255)
    category = models.CharField(max_length=255, blank=True, null=True)
    remark = models.CharField(max_length=255, blank=True, null=True)
    credential_type = models.CharField(max_length=50, choices=[('priority 1', 'Priority 1'), ('priority 2', 'Priority 2')], default='priority 1')

    
    def __str__(self):
        return self.name
    


class CredentialDetail(models.Model):
    credential = models.ForeignKey(Credentials, on_delete=models.CASCADE, related_name='details')
    field = models.ForeignKey(Field, on_delete=models.CASCADE)
    value = models.TextField()


    def __str__(self):
        return f"{self.credential.name} - {self.field.name}"
    




class Category(models.Model):
    name = models.CharField(max_length=255, unique=True)
    
    def __str__(self):
        return self.name
    


#CREATED AS NEW
#CREATED AS NEW
#CREATED AS NEW
#CREATED AS NEW
#CREATED AS NEW


from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class ProductType(models.Model):
    name = models.CharField(max_length=100)
    
    def __str__(self):
        return self.name

class ProductCategory(models.Model):
    name = models.CharField(max_length=100)
    
    
    def __str__(self):
        return self.name

PRIORITY_CHOICES = [
    ('priority1', 'Priority 1'),
    ('priority2', 'Priority 2'),
]

class InformationCenter(models.Model):
    title = models.CharField(max_length=200)
    remark = models.TextField(blank=True)
    url = models.URLField()
    added_date = models.DateField(default=timezone.now)
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE)
    product_type = models.ForeignKey(ProductType, on_delete=models.CASCADE)
    product_category = models.ForeignKey(ProductCategory, on_delete=models.CASCADE)
    thumbnail = models.ImageField(upload_to='information_thumbnails/')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES)
    language = models.CharField(max_length=50, blank=True) 
    duration = models.CharField(max_length=50, blank=True)  
    host = models.CharField(max_length=255, blank=True)  
    position = models.PositiveIntegerField(default=1)  # CREATED AS NEW
    
    def __str__(self):
        return self.title
    







# =============================================================================
# UPDATED DAILYTASK MODEL WITH DURATION TRACKING
# Add these fields and methods to your existing DailyTask model in models.py
# =============================================================================

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class DailyTask(models.Model):
    STATUS_CHOICES = [
        ('backlog', 'Backlog'),
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('review', 'Review/Testing'),
        ('completed', 'Completed'),
        ('hold', 'Hold'),
    ]
    
    PRIORITY_CHOICES = [
        ('high', 'High'),
        ('medium', 'Medium'),
        ('low', 'Low'),
    ]
    
    # Existing fields
    task_key = models.CharField(max_length=20, blank=True, null=True, editable=False)
    project = models.CharField(max_length=255)
    task = models.CharField(max_length=255)
    duration = models.CharField(max_length=50)  # Display duration like "2h 30m 15s"
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='in_progress')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    due_date = models.DateField(blank=True, null=True)
    added_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    remark = models.TextField(blank=True, null=True)
    
    # ✅ NEW FIELDS FOR DURATION TRACKING
    # Add these three fields to your existing model:
    elapsed_seconds = models.IntegerField(
        default=0, 
        help_text="Total elapsed time in seconds"
    )
    last_started_at = models.DateTimeField(
        null=True, 
        blank=True, 
        help_text="When task was last started/resumed"
    )
    is_timer_running = models.BooleanField(
        default=False, 
        help_text="Is the timer currently running"
    )

    def __str__(self):
        return f"{self.task} in {self.project}"
    
    # ✅ NEW METHODS - Add these to your model:
    
    def get_current_duration(self):
        """
        Calculate current duration including active time
        Returns formatted string like "2h 30m 15s"
        """
        total_seconds = self.elapsed_seconds
        
        # If timer is running, add the current active time
        if self.is_timer_running and self.last_started_at:
            current_time = timezone.now()
            active_duration = (current_time - self.last_started_at).total_seconds()
            total_seconds += active_duration
        
        # Format as "Xh Ym Zs"
        hours, remainder = divmod(int(total_seconds), 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours}h {minutes}m {seconds}s"
    
    def start_timer(self):
        """
        Start or resume the timer
        Called when status changes to 'in_progress'
        """
        if not self.is_timer_running:
            self.last_started_at = timezone.now()
            self.is_timer_running = True
            self.status = 'in_progress'
            self.save()
    
    def pause_timer(self):
        """
        Pause the timer and save elapsed time
        Called when status changes from 'in_progress' to 'hold' or other statuses
        """
        if self.is_timer_running and self.last_started_at:
            current_time = timezone.now()
            active_duration = (current_time - self.last_started_at).total_seconds()
            self.elapsed_seconds += int(active_duration)
            self.is_timer_running = False
            self.last_started_at = None
            self.status = 'hold'
            self.duration = self.get_current_duration()
            self.save()
    
    def stop_timer(self):
        """
        Stop the timer completely
        Called when task is marked as 'completed'
        """
        if self.is_timer_running:
            self.pause_timer()
        # Final duration update
        self.duration = self.get_current_duration()
        self.save()
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Daily Task'
        verbose_name_plural = 'Daily Tasks'


# =============================================================================

    



from django.db import models

class Department(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name



class JobRole(models.Model):
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    title = models.CharField(max_length=100)
    description = models.TextField(help_text="Separate each point with a new line")

    def get_description_points(self):
        return self.description.strip().split('\n')

    def __str__(self):
        return f"{self.title} ({self.department.name})"
    

class JobRoleDescription(models.Model):
    job_role = models.ForeignKey(JobRole, on_delete=models.CASCADE, related_name='descriptions')
    heading = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.heading} - {self.description}"
    




from django.db import models


class Customer(models.Model):
    customer_name   = models.CharField(max_length=100)
    firm_name       = models.CharField(max_length=100)
    place           = models.CharField(max_length=100)
    district        = models.CharField(max_length=100)
    state           = models.CharField(max_length=100)
    country         = models.CharField(max_length=100)
    phone           = models.CharField(max_length=15)

    # avoid circular import by using a string reference
    business_type   = models.ForeignKey(
        'app1.BusinessType',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    contact_person  = models.CharField(max_length=100)
    phone1          = models.CharField(max_length=15)
    phone2          = models.CharField(max_length=15, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)  

    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.customer_name





from django.db import models
from .models import Customer

class SocialMediaProject(models.Model):
    project_name = models.CharField(max_length=100)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    project_description = models.TextField()
    deadline = models.DateField()

    def __str__(self):
        return self.project_name
    



class Task(models.Model):
    task_name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.task_name
    



# app2/models.py
# models.py

from django.db import models
from django.conf import settings

class SocialMediaProjectAssignment(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('started', 'Started'),
        ('completed', 'Completed'),
        ('hold', 'On Hold'),
    ]
    project = models.ForeignKey('SocialMediaProject', on_delete=models.CASCADE)
    task = models.ForeignKey('Task', on_delete=models.CASCADE)
    assigned_to = models.ManyToManyField('app1.User', related_name='project_assignments')
    deadline = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    remark = models.TextField(blank=True, null=True)  


    def __str__(self):
        return f"{self.project.project_name} - {self.task.task_name}"

    def get_status_display_class(self):
        status_classes = {
            'pending': 'status-pending',
            'started': 'status-in-progress',
            'completed': 'status-completed',
            'hold': 'status-hold'
        }
        return status_classes.get(self.status, 'status-pending')

class AssignmentStatusHistory(models.Model):
    assignment = models.ForeignKey(SocialMediaProjectAssignment, on_delete=models.CASCADE, related_name='status_history')
    status = models.CharField(max_length=20, choices=SocialMediaProjectAssignment.STATUS_CHOICES)
    changed_at = models.DateTimeField(auto_now_add=True)
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ['changed_at']






from django.db import models

class Feeder(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('key_uploaded', 'Key Uploaded'),
        ('rejected', 'Rejected'),
        ('under_process', 'Under Process'),
    ]

    BUSINESS_NATURE_CHOICES = [
        ('', 'Select'),
        ('supermarket', 'Supermarket'),
        ('textile', 'Textile'),
        ('restaurant', 'Restaurant'),
        ('Agency/Distribution', 'Agency/Distribution'),
        ('retail', 'Retail'),
        ('Auto Mobiles', 'Auto Mobiles'),
        ('Bakery', 'Bakery'),
        ('Boutique', 'Boutique'),
        ('Hyper Market', 'Hyper Market'),
        ('Lab', 'Lab'),
    ]

    name = models.CharField(max_length=200)
    address = models.TextField()
    location = models.CharField(max_length=200)
    area = models.CharField(max_length=200)
    district = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    contact_person = models.CharField(max_length=100)
    contact_number = models.CharField(max_length=15)
    email = models.EmailField()
    reputed_person_name = models.CharField(max_length=100, blank=True)
    reputed_person_number = models.CharField(max_length=15, blank=True)

    software = models.CharField(max_length=100)

    # ✅ Changed from ForeignKey to CharField with your custom dropdown
    nature = models.CharField(
        max_length=50,
        choices=BUSINESS_NATURE_CHOICES,
        blank=True
    )

    branch = models.ForeignKey(
        'app1.Branch',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    no_of_system = models.IntegerField()
    pincode = models.CharField(max_length=10)
    country = models.CharField(max_length=100, default='India')
    installation_date = models.DateField()
    remarks = models.TextField(blank=True)
    software_amount = models.DecimalField(max_digits=10, decimal_places=2)
    module_charges = models.DecimalField(max_digits=10, decimal_places=2)
    more_modules = models.TextField(blank=True, null=True)
    modules = models.TextField(blank=True)
    module_prices = models.JSONField(default=dict, blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    def _str_(self):
        return self.name

    def get_status_display_class(self):
        status_classes = {
            'pending': 'status-pending',
            'accepted': 'status-accepted',
            'key_uploaded': 'status-key-uploaded',
            'rejected': 'status-rejected',
            'under_process': 'status-under-process',
        }
        return status_classes.get(self.status, 'status-pending')







from django.db import models
from django.contrib.auth.models import User


class StandbyItem(models.Model):
    STATUS_CHOICES = [
        ('in_stock', 'In Stock'),
        ('with_customer', 'With Customer'),
    ]

    name = models.CharField(max_length=200)
    serial_number = models.CharField(max_length=100, unique=True)
    notes = models.TextField(blank=True, null=True)
    stock = models.IntegerField(default=0)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='in_stock',
        help_text="Current status of the item"
    )

    customer_name = models.CharField(max_length=200, blank=True, null=True)
    customer_place = models.CharField(max_length=200, blank=True, null=True)
    customer_phone = models.CharField(max_length=15, blank=True, null=True)
    issued_date = models.DateField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return f"{self.name} - {self.serial_number}"

    def get_status_display_class(self):
        if self.status == 'in_stock':
            return 'badge-success'
        elif self.status == 'with_customer':
            return 'badge-warning'
        return 'badge-secondary'

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Standby Item"
        verbose_name_plural = "Standby Items"


class StandbyReturn(models.Model):
    """Model to track standby item returns"""
    item = models.ForeignKey(StandbyItem, on_delete=models.CASCADE, related_name='returns')
    return_date = models.DateField()
    return_notes = models.TextField(blank=True, null=True)
    returned_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    stock_on_return = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Store original customer info at time of return
    customer_name_at_return = models.CharField(max_length=200, blank=True, null=True)
    customer_place_at_return = models.CharField(max_length=200, blank=True, null=True)
    customer_phone_at_return = models.CharField(max_length=15, blank=True, null=True)
    issued_date_at_return = models.DateField(blank=True, null=True)

    def __str__(self):
        return f"Return of {self.item.name} on {self.return_date}"

# Update the StandbyImage model to link to returns
class StandbyImage(models.Model):
    IMAGE_TYPE_CHOICES = [
        ('original', 'Original'),
        ('return_condition', 'Return Condition'),
        ('other', 'Other'),
    ]
    
    item = models.ForeignKey(StandbyItem, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='standby_images/')
    image_type = models.CharField(max_length=20, choices=IMAGE_TYPE_CHOICES, default='original')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    # Link return images to specific return records
    standby_return = models.ForeignKey(
        StandbyReturn, 
        on_delete=models.CASCADE, 
        related_name='return_images',
        null=True, 
        blank=True
    )

    def __str__(self):
        return f"Image for {self.item.name} ({self.image_type})"