from django.db import models
from django.utils import timezone
from django.contrib.auth.models import AbstractBaseUser

class Branch(models.Model):
    name = models.CharField(max_length=100)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

class Requirement(models.Model):
    name = models.CharField(max_length=100)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name
    
class District(models.Model):
    name = models.CharField(max_length=100)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

class Area(models.Model):
    name = models.CharField(max_length=100)
    district = models.ForeignKey(District, on_delete=models.CASCADE, related_name='areas')

    class Meta:
        ordering = ['name']
        unique_together = ('name', 'district')  # Ensure unique area names within a district

    def __str__(self):
        return f"{self.name} ({self.district.name} District)"
    

class Location(models.Model):
    name = models.CharField(max_length=100)
    district = models.ForeignKey(District, on_delete=models.CASCADE, related_name="locations")
    area = models.ForeignKey(Area, on_delete=models.CASCADE, related_name="locations")

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} - {self.area.name} ({self.district.name})"

from django.db import models
from app2.models import JobRole


class User(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
    ]
    USER_LEVEL_CHOICES = [
        ('normal', 'Normal User'),#admin
        ('admin_level', 'Admin Level User'),#superadmin
        ('3level', '3 level'),#    USER
        ('4level', '4 level'), #  SUPER USER
        ('5level', '5 level'),  # BRANCH USER

       


    ]


    name = models.CharField(max_length=100)
    userid = models.CharField(max_length=100, unique=True)
    password = models.CharField(max_length=100)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE)
    user_level = models.CharField(
        max_length=20,
        choices=USER_LEVEL_CHOICES,
        default='normal',
    )
    image = models.ImageField(upload_to='user_images/', null=True, blank=True)  
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active') 
    allowed_menus = models.TextField(blank=True, null=True)
    job_role = models.ForeignKey(JobRole, on_delete=models.SET_NULL, null=True, blank=True, related_name='users')

    


    def __str__(self):
        return f"{self.name} ({self.get_user_level_display()})"

    @classmethod
    def authenticate(cls, userid, password):
        try:
            return cls.objects.get(userid=userid, password=password, is_active=True)
        except cls.DoesNotExist:
            return None


class Lead(models.Model):
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
        ('Opticals', 'Opticals'),
        ('Pharmacy', 'Pharmacy'),
        ('School', 'School'),
        ('Hotels/ Resorts', 'Hotels/ Resorts'),
        ('wholesale', 'Wholesale'),
        ('footware', 'Footware'),
        ('Travels', 'Travels'),
        ('Jewellery', 'Jewellery'),
        ('production', 'Production'),
        ('hardware', 'Hardware'),
        ('hospital', 'Hospital'),
        ('clinic', 'Clinic'),
        ('real estate', 'Real Estate'),
        ('another', 'Another'),
    ]

    # Keep 'Select' first and 'Another' last, sort others alphabetically
    BUSINESS_NATURE_CHOICES = [BUSINESS_NATURE_CHOICES[0]] + sorted(
        BUSINESS_NATURE_CHOICES[1:-1],  # Exclude 'Select' and 'Another'
        key=lambda x: x[1].lower()      # Sort alphabetically by display value (case-insensitive)
    ) + [BUSINESS_NATURE_CHOICES[-1]]  # Append 'Another' at the end

    firm_name = models.CharField(max_length=200)
    customer_name = models.CharField(max_length=100)
    contact_number = models.CharField(max_length=20)
    landmark = models.CharField(max_length=200)
    business_nature = models.CharField(
        max_length=100,
        choices=BUSINESS_NATURE_CHOICES,
        default=''
    )
    requirements = models.ManyToManyField('Requirement')
    user = models.ForeignKey('User', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    follow_up_required = models.BooleanField(default=False)
    quotation_required = models.BooleanField(default=False)
    image = models.ImageField(upload_to='lead_images/', null=True, blank=True)
    remarks = models.TextField(blank=True, null=True)
    planet_entry = models.BooleanField(default=False)
    voice_note = models.FileField(upload_to='voice_notes/', null=True, blank=True)
    location = models.ForeignKey(Location, on_delete=models.SET_NULL, null=True, blank=True, related_name="leads")
    district = models.ForeignKey(District, on_delete=models.SET_NULL, null=True, blank=True, related_name="leads")
    area = models.ForeignKey(Area, on_delete=models.SET_NULL, null=True, blank=True, related_name="leads")
    hardwares = models.ManyToManyField('Hardware', blank=True, related_name='leads')
    added_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    added_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    
    def get_location_url(self):
        if self.added_latitude and self.added_longitude:
            return f"https://www.google.com/maps?q={self.added_latitude},{self.added_longitude}"
        return None
    

    def __str__(self):
        return f"{self.firm_name} - {self.customer_name}"
    

class LeadRequirementAmount(models.Model):
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name='requirement_amounts')
    requirement = models.ForeignKey(Requirement, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    remarks = models.TextField(blank=True, null=True)  # Add this field

    class Meta:
        unique_together = ('lead', 'requirement')

    def __str__(self):
        return f"{self.lead} - {self.requirement}: {self.amount}"





class Hardware(models.Model):
    name = models.CharField(max_length=200)
    specification = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} (₹{self.price})"
    
class LeadHardwarePrice(models.Model):
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name="hardware_prices")
    hardware = models.ForeignKey(Hardware, on_delete=models.CASCADE)
    custom_price = models.FloatField()

    class Meta:
        unique_together = ('lead', 'hardware')  # Enforces one price per lead-hardware combination

    def __str__(self):
        return f"Lead: {self.lead.firm_name}, Hardware: {self.hardware.name}, Price: ₹{self.custom_price}"








class Complaint(models.Model):
    COMPLAINT_TYPES = [
        ('software', 'Software'),
        ('hardware', 'Hardware'),
        ('both', 'Both'),
    ]
    description = models.TextField()
    complaint_type = models.CharField(max_length=10, choices=COMPLAINT_TYPES, default='software')
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)  # Add this field


    def __str__(self):
        return f"Complaint #{self.id}"
    




    


class ServiceEntry(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Solved', 'Solved')
    ]
    MODE_CHOICES = [
        ('Online', 'Online'),
        ('Onsite', 'Onsite')
    ]
    SERVICE_TYPE_CHOICES = [
        ('Hardware', 'Hardware'),
        ('Software', 'Software')
    ]
    
    date = models.DateTimeField(auto_now_add=True)
    customer = models.CharField(max_length=200)
    complaint = models.TextField()
    remarks = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    mode_of_service = models.CharField(max_length=20, choices=MODE_CHOICES, default='Onsite') 
    service_type = models.CharField(max_length=20, choices=SERVICE_TYPE_CHOICES, default='Software')  
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    place = models.CharField(max_length=200)
    duration = models.CharField(max_length=100, blank=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)

    class Meta:
        ordering = ['-date']


from django.db import models

class Agent(models.Model):
    name = models.CharField(max_length=100)
    firm_name = models.CharField(max_length=150, blank=True)
    business_type = models.CharField(max_length=100)
    location = models.CharField(max_length=100)
    district = models.CharField(max_length=100)
    contact_number = models.CharField(max_length=15)
    remarks = models.TextField(blank=True)

    def __str__(self):
        return self.name

class JobTitle(models.Model):
    title = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

from django.db import models
from django.contrib.auth import get_user_model
from django.utils.timezone import now

class CV(models.Model):
    GENDER_CHOICES = [
        ('', ''),  
        ('M', 'Male'),
        ('F', 'Female'),
    ]
    KERALA_DISTRICTS = [
        ('Alappuzha', 'Alappuzha'),
        ('Ernakulam', 'Ernakulam'),
        ('Idukki', 'Idukki'),
        ('Kannur', 'Kannur'),
        ('Kasaragod', 'Kasaragod'),
        ('Kollam', 'Kollam'),
        ('Kottayam', 'Kottayam'),
        ('Kozhikode', 'Kozhikode'),
        ('Malappuram', 'Malappuram'),
        ('Palakkad', 'Palakkad'),
        ('Pathanamthitta', 'Pathanamthitta'),
        ('Thiruvananthapuram', 'Thiruvananthapuram'),
        ('Thrissur', 'Thrissur'),
        ('Wayanad', 'Wayanad'),
        ('Other', 'Other'),
    ]
    created_date = models.DateTimeField(default=now)
    name = models.CharField(max_length=255)
    address = models.TextField(blank=True, null=True) 
    phone_number = models.CharField(max_length=15, blank=True, null=True)  
    place = models.CharField(max_length=255)
    district = models.CharField(max_length=255, choices=KERALA_DISTRICTS)
    education = models.CharField(max_length=255)
    experience = models.TextField()
    job_title = models.ForeignKey(JobTitle, on_delete=models.CASCADE)
    dob = models.DateField(blank=True, null=True)  
    remarks = models.TextField(blank=True, null=True)
    cv_attachment = models.FileField(upload_to='cv_attachments/')
    interview_status = models.BooleanField(default=False)
    interview_date = models.DateTimeField(null=True, blank=True)  
    selected = models.BooleanField(default=False)  
    created_by = models.ForeignKey(get_user_model(), on_delete=models.SET_NULL, null=True, blank=True, related_name="created_cvs")
    agent = models.ForeignKey('Agent', on_delete=models.SET_NULL, null=True, blank=True) 
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True)

    
    


     

    def __str__(self):
        return self.name
    
    
from django.contrib.postgres.fields import ArrayField
from django.db import models

class Credential(models.Model): 
    name = models.CharField(max_length=255)
    visibility = ArrayField(
        models.CharField(max_length=20, choices=[
            ('all', 'All Users'),
            ('normal', 'Normal User'),
            ('admin_level', 'Admin Level User'),
            ('3level', '3 Level User'),
            ('4level', '4 Level User')
        ]),
        default=list, 
        blank=True
    )

    def clean(self):
        """ Ensure visibility is always stored as a list format """
        if isinstance(self.visibility, str):  
            self.visibility = [self.visibility]  # Convert single string to list
        elif self.visibility is None:
            self.visibility = []
        elif isinstance(self.visibility, list):
            self.visibility = [str(v) for v in self.visibility]  # Ensure all items are strings

    def save(self, *args, **kwargs):
        """ Apply the cleaning function before saving to enforce correct format """
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


    


from django.db import models

class OfficialDocument(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField()

    def __str__(self):
        return self.name

class DocumentCredential(models.Model):
    document = models.ForeignKey(OfficialDocument, on_delete=models.CASCADE)
    credential = models.ForeignKey(Credential, on_delete=models.CASCADE)
    url = models.URLField(blank=True, null=True)
    attachment = models.FileField(upload_to='attachments/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    additional_fields = models.JSONField(default=list, blank=True)

    class Meta:
        unique_together = ('document', 'credential')  # Enforce uniqueness

    def __str__(self):
        return f"{self.document.name} - {self.credential.name}"



from django.db import models
from .models import CV  # Import the CV model if it's not already imported

class Rating(models.Model):
    cv = models.ForeignKey('CV', on_delete=models.CASCADE)
    knowledge = models.IntegerField(null=True, blank=True)  
    confidence = models.IntegerField(null=True, blank=True)
    attitude = models.IntegerField(null=True, blank=True)
    communication = models.IntegerField(null=True, blank=True)
    appearance = models.IntegerField(null=True, blank=True)
    languages = models.JSONField(default=list, blank=True)
    expected_salary = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    experience = models.CharField(max_length=255, blank=True, null=True)
    remark = models.TextField(blank=True, null=True)
    voice_note = models.FileField(upload_to='voice_notes/', null=True, blank=True)

    def __str__(self):
        return f"Ratings for CV: {self.cv.name}"
    
from django.db import models
from django.contrib.auth import get_user_model
from .models import CV



class BusinessType(models.Model):
    name = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
    



from django.db import models
from .models import CV

class OfferLetterDetails(models.Model):
    cv = models.OneToOneField(CV, on_delete=models.CASCADE, related_name='offer_letter_details')
    position = models.CharField(max_length=255, blank=True, null=True)
    department = models.CharField(max_length=255, blank=True, null=True)
    start_date = models.DateField(blank=True, null=True)
    salary = models.CharField(max_length=255, blank=True, null=True)
    notice_period = models.PositiveIntegerField(default=0)  # Add this line

    def __str__(self):
        return f"Offer Letter Details for {self.cv.name}"
    



from django.core.exceptions import ValidationError


class Employee(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('on_leave', 'On Leave'),
    ]
    ORGANIZATION_CHOICES = [
        ('', 'Select Organization'),  # Optional blank choice
        ('IMC', 'IMC'),
        ('SYSMAC', 'SYSMAC'),
    ]
    name = models.CharField(max_length=100)
    user = models.ForeignKey("User", on_delete=models.SET_NULL, null=True, blank=True) 
    photo = models.ImageField(upload_to='employees/')
    address = models.CharField(max_length=255, blank=True, null=True) 
    phone_personal = models.CharField(max_length=15)
    phone_residential = models.CharField(max_length=15, blank=True, null=True)
    place = models.CharField(max_length=100)
    district = models.CharField(max_length=100)
    education = models.CharField(max_length=100)
    experience = models.CharField(max_length=100, blank=True, null=True)
    job_title = models.CharField(max_length=100)
    organization = models.CharField(max_length=10, choices=ORGANIZATION_CHOICES, blank=True, null=True)  # Optional field
    joining_date = models.DateField()
    dob = models.DateField()
    experience_start_date = models.DateField(blank=True, null=True)
    experience_end_date = models.DateField(blank=True, null=True)
    bank_account_number = models.CharField(max_length=20, blank=True, null=True)  
    ifsc_code = models.CharField(max_length=20, blank=True, null=True)  
    bank_name = models.CharField(max_length=100, blank=True, null=True)
    branch = models.CharField(max_length=100, blank=True, null=True)  
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')  
    duty_time_start = models.TimeField(null=True, blank=True)
    duty_time_end = models.TimeField(null=True, blank=True)

    def clean(self):
        """ Ensure the selected User ID is unique. """
        if self.user and Employee.objects.exclude(id=self.id).filter(user=self.user).exists():
            raise ValidationError(f"User ID {self.user.userid} is already assigned to another employee.")
    
    def save(self, *args, **kwargs):
        self.clean()  # Run validation before saving
        super().save(*args, **kwargs)


class Attachment(models.Model):
    employee = models.ForeignKey(Employee, related_name='attachments', on_delete=models.CASCADE)
    file = models.FileField(upload_to='employee_attachments/')


    

from django.db import models

class Document(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

class DocumentSetting(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='settings')
    name = models.CharField(max_length=100)
    url = models.URLField(blank=True, null=True)
    attachment = models.FileField(upload_to='document_settings/', blank=True, null=True)
    position = models.IntegerField(default=0) 

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if self.position == 0:  # If position is not set
            # Get the highest position number for this document
            max_position = DocumentSetting.objects.filter(
                document=self.document
            ).aggregate(models.Max('position'))['position__max']
            # Set the new position to be one more than the highest
            self.position = (max_position or 0) + 1
        super().save(*args, **kwargs)

    class Meta:
        ordering = ['position']

class DocumentSettingField(models.Model):
    setting = models.ForeignKey(DocumentSetting, on_delete=models.CASCADE, related_name="fields")
    field_name = models.CharField(max_length=255)
    field_value = models.TextField()
    purpose = models.TextField()
    attachment = models.FileField(upload_to='field_attachments/', blank=True, null=True)
    position = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.setting.name} - {self.field_name}"

    def save(self, *args, **kwargs):
        if self.position == 0:  # If position is not set
            # Get the highest position number for this setting
            max_position = DocumentSettingField.objects.filter(
                setting=self.setting
            ).aggregate(models.Max('position'))['position__max']
            # Set the new position to be one more than the highest
            self.position = (max_position or 0) + 1
        super().save(*args, **kwargs)

    class Meta:
        ordering = ['position']

    

from django.db import models

class ReminderType(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name




from django.conf import settings


class Reminder(models.Model):
    no = models.IntegerField(primary_key=True, editable=False)  # Changed from AutoField
    reminder_type = models.ForeignKey(ReminderType, on_delete=models.CASCADE)
    remark = models.TextField(blank=True, null=True)
    responsible_persons = models.ManyToManyField('Employee', related_name='reminders', blank=True)
    remind_date = models.DateField()
    entry_date = models.DateTimeField(auto_now_add=True)
    
    added_by = models.ForeignKey(     
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='added_reminders',
        editable=False  
    )
    event_date = models.DateField(null=True, blank=True)   

    def save(self, *args, **kwargs):
        if not self.no:  
            max_no = Reminder.objects.aggregate(models.Max('no')).get('no__max') or 0
            self.no = max_no + 1
        super().save(*args, **kwargs)

    def _str_(self):
        return f"Reminder {self.no}: {self.reminder_type}"


   



from django.db import models
from .models import Employee

# models.py

from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

class Attendance(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    date = models.DateField()
    day = models.IntegerField()
    status = models.CharField(
        max_length=20, 
        choices=[
            ('initial', 'Not Marked'),
            ('full', 'Full Day'),
            ('half', 'Half Day'),
            ('leave', 'Leave')
        ], 
        default='initial'
    )
    
    punch_in = models.DateTimeField(null=True, blank=True)
    punch_out = models.DateTimeField(null=True, blank=True)
    punch_in_location = models.CharField(max_length=255, null=True, blank=True)
    punch_out_location = models.CharField(max_length=255, null=True, blank=True)
    punch_in_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    punch_in_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    punch_out_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    punch_out_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    verified = models.BooleanField(default=False)  
    note = models.TextField(blank=True, null=True)

    class Meta:
        unique_together = ('employee', 'day', 'date')  # Ensure no duplicate entries for the same day

    def __str__(self):
        return f"{self.employee.name} - Day {self.day} - {self.get_status_display()}"
 # Add to models.py


class Holiday(models.Model):
    date = models.DateField(unique=True)
    description = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"Holiday - {self.date}"   

    


from django.contrib.auth.models import User as DjangoUser


class LeaveRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    LEAVE_TYPE_CHOICES = [
        ('full_day', 'Full Day'),
        ('half_day', 'Half Day'),
    ]
    
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    leave_type = models.CharField(max_length=20, choices=LEAVE_TYPE_CHOICES, default='full_day')
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    processed_by = models.ForeignKey(DjangoUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='processed_leave_requests')
    processed_at = models.DateTimeField(null=True, blank=True)
    

    def __str__(self):
        return f"{self.employee.name} - {self.start_date} to {self.end_date} ({self.status})"

    def save(self, *args, **kwargs):
        if self.status in ['approved', 'rejected'] and not self.processed_at:
            self.processed_at = timezone.now()
        super().save(*args, **kwargs)
    
class LateRequest(models.Model):
    employee = models.ForeignKey('Employee', on_delete=models.CASCADE)
    date = models.DateField()
    delay_time = models.CharField(max_length=50, default='0 minutes')  # New field
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=(
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')
    ), default='pending')
    processed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    processed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.employee.name} - {self.date} ({self.status})"

    class Meta:
        ordering = ['-created_at']    
    
    
    
    






#Project Management
#Project Management
from ckeditor.fields import RichTextField  # Import CKEditor's RichTextField

class Project(models.Model):
    PROJECT_TYPES = [
        ('Website', 'Website'),
        ('Web Application', 'Web Application'),
        ('Mobile Application', 'Mobile Application'),
    ]

    STATUS_CHOICES = [
        ('Active', 'Active'),
        ('On Hold', 'On Hold'),
        ('Cancel', 'Cancel'),
        ('In Progress', 'In Progress'),
        ('Finish', 'Finish'),
        ('Inactive', 'Inactive'),
        
    ]

    project_name = models.CharField(max_length=200)
    languages = models.CharField(max_length=200)
    technologies = models.CharField(max_length=200)
    notes = RichTextField()  # Changed from description to notes and using RichTextField
    database_name = models.CharField(max_length=100)
    domain_name = models.CharField(max_length=100)
    domain_platform = models.CharField(max_length=100)
    github_link = models.URLField()
    assigned_person = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True)
    client = models.CharField(max_length=200, default='')  # Added client field
    project_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Active')  # Added project status field
    project_type = models.CharField(max_length=50, choices=PROJECT_TYPES)
    project_duration = models.CharField(max_length=50)
    deadline = models.DateField(null=True, blank=True) 


    def _str_(self):
        assigned_to = f" - Assigned to: {self.assigned_person.name}" if self.assigned_person else ""
        return f"{self.project_name}{assigned_to}"


        
class ProjectWork(models.Model):
    STATUS_CHOICES = [
        ('not_started', 'Not Started'),
        ('started', 'Started'),
        ('in_progress', 'In Progress'),
        ('on_hold', 'On Hold'),
        ('canceled', 'Canceled'),
        ('finished', 'Finished')
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='project_works')
    members = models.ManyToManyField(Employee, related_name='project_works')  # Changed to ManyToManyField
    start_date = models.DateField(default=timezone.now)
    deadline = models.DateField()
    client = models.CharField(max_length=200)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='not_started')
    
    @property
    def countdown(self):
        if self.deadline:
            today = timezone.now().date()
            total_days = (self.deadline - self.start_date).days
            remaining_days = (self.deadline - today).days
        
            if remaining_days <= 0:
                return {'total': total_days, 'remaining': 0, 'percentage': 100}
        
            completed_percentage = ((total_days - remaining_days) / total_days) * 100 if total_days > 0 else 0
        
            return {
                'total': total_days,
                'remaining': remaining_days,
                'percentage': min(round(completed_percentage, 1), 100)
            }
        return {'total': 0, 'remaining': 0, 'percentage': 0}

    def _str_(self):
        return f"{self.project.project_name}"

    class Meta:
        ordering = ['deadline']



from django.db import models
from django.utils import timezone

class Task(models.Model):
    STATUS_CHOICES = [
        ('Not Started', 'Not Started'),
        ('Started', 'Started'),
        ('On Hold', 'On Hold'),
        ('In Progress', 'In Progress'),
        ('Cancel', 'Cancel'),
    ]

    title = models.CharField(max_length=255)
    project = models.ForeignKey('Project', on_delete=models.CASCADE)
    start_date = models.DateField(default=timezone.now)
    deadline_date = models.DateField()
    assigned_to = models.ForeignKey('Employee', on_delete=models.SET_NULL, null=True)
    assigned_by = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_tasks')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Not Started')

    def _str_(self):
        return self.title





    


class DefaultSettings(models.Model):
    default_menus = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Default Setting'
        verbose_name_plural = 'Default Settings'






   




class BreakTime(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    date = models.DateField()
    break_punch_in = models.DateTimeField(null=True, blank=True)
    break_punch_out = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)  # To track current active break


    def __str__(self):
        return f"{self.employee.name} - Break Time on {self.date}"


    #CREATED AS NEW

    #CREATED AS NEW

    #CREATED AS NEWF


    # models.py
REQUEST_STATUS_CHOICES = [
    ('pending', 'Pending'),
    ('approved', 'Approved'),
    ('rejected', 'Rejected'),
]

class EarlyRequest(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    date = models.DateField()
    early_time = models.TimeField()
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=REQUEST_STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    processed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    processed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.employee.name} - {self.date}"
