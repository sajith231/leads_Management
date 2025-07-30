
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
    








from django.db import models
from django.contrib.auth.models import User


class DailyTask(models.Model):
    STATUS_CHOICES = [
        ('complete', 'Complete'),
        ('started', 'Started'),
        ('finish', 'Finish'),
        ('in_progress', 'In Progress'),
    ]
    project = models.CharField(max_length=255)
    task = models.CharField(max_length=255)
    duration = models.CharField(max_length=50)  # Changed to CharField
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='in_progress')#CHANGED AS NEW
    added_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    remark = models.TextField(blank=True, null=True) 

    def __str__(self):
        return f"{self.task} in {self.project}"
    



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
        ('rejected', 'Rejected'),
        ('under_process', 'Under Process'),
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
    nature = models.ForeignKey(
        'app1.BusinessType',     # points to app1.BusinessType
        on_delete=models.SET_NULL,
        null=True,
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


    modules = models.TextField(blank=True)  # store module list as comma separated values
    module_prices = models.JSONField(default=dict, blank=True)
    
    # New status field with default as 'pending'
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    def _str_(self):
        return self.name

    def get_status_display_class(self):
        """Return CSS class for status display"""
        status_classes = {
            'pending': 'status-pending',
            'accepted': 'status-accepted',
            'rejected': 'status-rejected',
            'under_process': 'status-under-process',
        }
        return status_classes.get(self.status, 'status-pending')








from django.db import models
from django.contrib.auth.models import User

class StandbyItem(models.Model):
    serial_number = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    notes = models.TextField(blank=True, null=True)
    stock = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, default=1)  # Add default user ID
    
    def save(self, *args, **kwargs):
        self.serial_number = self.serial_number.upper()
        self.name = self.name.upper()  # Also uppercase the name
        super().save(*args, **kwargs)

    def __str__(self):  # Fixed: double underscore
        return self.name
    
    class Meta:
        ordering = ['-created_at']  # Default ordering by creation date


class StandbyItemImage(models.Model):
    item = models.ForeignKey(StandbyItem, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="item_images/")

    def __str__(self):  # Fixed: double underscore
        return f"Image for {self.item.name}"