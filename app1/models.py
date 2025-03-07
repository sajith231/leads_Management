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


class User(models.Model):
    USER_LEVEL_CHOICES = [
        ('normal', 'Normal User'),#admin
        ('admin_level', 'Admin Level User'),#superadmin
        ('3level', '3 level'),#    USER
        ('4level', '4 level'), #  SUPER USER

       


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
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Complaint #{self.id}"
    




from django.db import models

class ServiceLog(models.Model):
    customer_name = models.CharField(max_length=255)
    type = models.CharField(max_length=255)
    complaint = models.ForeignKey(Complaint, on_delete=models.CASCADE)
    remark = models.TextField()
    voice_note = models.FileField(upload_to='voice_notes/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    added_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
    assigned_person = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_service_logs')
    assigned_date = models.DateField(null=True, blank=True)  #
    status = models.CharField(max_length=20, default='Not Completed', 
                            choices=[('Not Completed', 'Not Completed'), 
                                   ('Completed', 'Completed')])
    
    def assign_user(self, user):
        self.assigned_person = user
        self.assigned_date = timezone.now()
        self.save()

    def __str__(self):
        return f"Service Log for {self.customer_name} ({self.created_at})"
    


class ServiceEntry(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Solved', 'Solved')
    ]
    
    date = models.DateTimeField(auto_now_add=True)
    customer = models.CharField(max_length=200)
    complaint = models.TextField()
    remarks = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    place = models.CharField(max_length=200)

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

class InterviewTakenBy(models.Model):     
    cv = models.ForeignKey(CV, on_delete=models.CASCADE, related_name='interview_taken_by')
    created_by = models.ForeignKey(get_user_model(), on_delete=models.CASCADE, related_name='interview_taken_by')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Interview taken by {self.created_by.username} for CV {self.cv.id}"

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

    def __str__(self):
        return f"Offer Letter Details for {self.cv.name}"
    





class Employee(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('on_leave', 'On Leave'),
    ]
    name = models.CharField(max_length=100)
    photo = models.ImageField(upload_to='employees/')
    address = models.CharField(max_length=255, blank=True, null=True) 
    phone_personal = models.CharField(max_length=15)
    phone_residential = models.CharField(max_length=15, blank=True, null=True)
    place = models.CharField(max_length=100)
    district = models.CharField(max_length=100)
    education = models.CharField(max_length=100)
    experience = models.CharField(max_length=100, blank=True, null=True)
    job_title = models.CharField(max_length=100)
    joining_date = models.DateField()
    dob = models.DateField()
    experience_start_date = models.DateField(blank=True, null=True)
    experience_end_date = models.DateField(blank=True, null=True)
    bank_account_number = models.CharField(max_length=20, blank=True, null=True)  
    ifsc_code = models.CharField(max_length=20, blank=True, null=True)  
    bank_name = models.CharField(max_length=100, blank=True, null=True)
    branch = models.CharField(max_length=100, blank=True, null=True)  
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')  

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
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="settings")
    name = models.CharField(max_length=255)
    attachment = models.FileField(upload_to='document_attachments/', blank=True, null=True)
    url = models.URLField(blank=True, null=True)

    def __str__(self):
        return f"{self.document.name} - {self.name}"

class DocumentSettingField(models.Model):
    setting = models.ForeignKey(DocumentSetting, on_delete=models.CASCADE, related_name="fields")
    field_name = models.CharField(max_length=255)
    field_value = models.TextField()
    purpose = models.TextField()
    attachment = models.FileField(upload_to='field_attachments/', blank=True, null=True)

    def __str__(self):
        return f"{self.setting.name} - {self.field_name}"
    


    #CREATED AS NEW

    #CREATED AS NEW

    #CREATED AS NEW

from django.db import models
from .models import Employee

class EmployeeSalary(models.Model):
    employee = models.OneToOneField(Employee, on_delete=models.CASCADE, related_name='salary_details')
    joining_date = models.DateField(null=True, blank=True)
    salary = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    def __str__(self):
        return f"{self.employee.name} - {self.salary}"


