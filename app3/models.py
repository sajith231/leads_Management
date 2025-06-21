from django.db import models
from django.contrib.auth.models import User
from app1.models import Employee
 # Adjust import based on app structure

class SalaryCertificate(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    address = models.CharField(max_length=255, blank=True, null=True)
    joining_date = models.DateField(blank=True, null=True)
    job_title = models.CharField(max_length=100, blank=True, null=True)
    salary = models.DecimalField(max_digits=10, decimal_places=2)
    is_approved = models.BooleanField(default=False)
    
    # New fields
    added_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='added_certificates')
    added_on = models.DateTimeField(auto_now_add=True)
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_certificates')
    approved_on = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Salary Certificate - {self.employee.name}"

    def save(self, *args, **kwargs):
        # Populate fields from the associated Employee instance
        self.address = self.employee.address
        self.joining_date = self.employee.joining_date
        self.job_title = self.employee.job_title
        super().save(*args, **kwargs)


from django.db import models
from django.contrib.auth.models import User
from app1.models import CV

class Interview(models.Model):
    name = models.CharField(max_length=255)
    job_title = models.CharField(max_length=255)
    cv_attachment = models.FileField(upload_to='cv_attachments/', blank=True, null=True)
    place = models.CharField(max_length=255)
    created_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    gender = models.CharField(max_length=1, choices=[('M', 'Male'), ('F', 'Female')], blank=True)
    address = models.TextField(blank=True, null=True)
    district = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    education = models.CharField(max_length=255)
    experience = models.TextField()
    dob = models.DateField(blank=True, null=True)
    remarks = models.TextField(blank=True, null=True)
    cv_source = models.CharField(max_length=255, blank=True, null=True)
    created_date = models.DateTimeField(auto_now_add=True)
    

    def __str__(self):
        return self.name

class Rating(models.Model):
    interview = models.ForeignKey(Interview, on_delete=models.CASCADE)
    appearance = models.IntegerField(null=True, blank=True, default=0)
    knowledge = models.IntegerField(null=True, blank=True, default=0)
    confidence = models.IntegerField(null=True, blank=True, default=0)
    attitude = models.IntegerField(null=True, blank=True, default=0)
    communication = models.IntegerField(null=True, blank=True, default=0)
    languages = models.CharField(max_length=255, blank=True, default='')
    expected_salary = models.CharField(max_length=50, blank=True, default='')
    experience = models.CharField(max_length=50, blank=True, default='')
    remark = models.TextField(blank=True, default='')
    voice_note = models.FileField(upload_to='voice_notes/', blank=True, null=True)
    STATUS_CHOICES = [
        ('selected', 'Selected'),
        ('rejected', 'Rejected'),
    ]
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='selected')

from django.db import models
from app3.models import Interview  # adjust if Interview is from another app

# models.py
from django.db import models
from django.contrib.auth.models import User
from app1.models import Employee

# Add these fields to your OfferLetter model in models.py

class OfferLetter(models.Model):
    interview = models.OneToOneField(
        Interview,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='offer_letter'
    )
    position = models.CharField(max_length=100)
    department = models.CharField(max_length=100)
    start_date = models.DateField()
    salary = models.DecimalField(max_digits=10, decimal_places=2)
    notice_period = models.IntegerField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_generated = models.BooleanField(default=False)
    generated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='generated_offer_letters')
    generated_date = models.DateTimeField(null=True, blank=True)
    
    # Add these new fields for candidate status
    CANDIDATE_STATUS_CHOICES = [
        ('willing', 'Willing'),
        ('not_willing', 'Not Willing'),
    ]
    candidate_status = models.CharField(
        max_length=15, 
        choices=CANDIDATE_STATUS_CHOICES, 
        blank=True, 
        null=True,
        default=None
    )
    status_remarks = models.TextField(blank=True, null=True)
    status_updated_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='status_updated_offer_letters'
    )
    status_updated_date = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        if self.interview:
            return f"Offer Letter - {self.position} for {self.interview.name}"
        return f"Offer Letter - {self.position}"