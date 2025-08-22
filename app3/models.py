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
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')

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

from django.db import models
from django.contrib.auth.models import User
from app1.models import Employee
from django.conf import settings  # Ensure this import is correct

# models.py
from django.db import models
from django.contrib.auth.models import User

class ExperienceCertificate(models.Model):
    employee = models.OneToOneField('app1.Employee', on_delete=models.CASCADE, related_name='experience_certificate')
    # Remove these fields since they'll be fetched from Employee model
    # address = models.CharField(max_length=255, blank=True, null=True)
    # joining_date = models.DateField(blank=True, null=True)
    # job_title = models.CharField(max_length=100, blank=True, null=True)
    
    experience_details = models.TextField(blank=True, null=True)
    certificate = models.FileField(upload_to='certificates/', blank=True, null=True)
    is_approved = models.BooleanField(default=False)
    added_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='added_experience_certificates')
    added_on = models.DateTimeField(auto_now_add=True)
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_experience_certificates')
    approved_on = models.DateTimeField(null=True, blank=True)
    start_date = models.DateField(blank=True, null=True)  # Start date field
    end_date = models.DateField(blank=True, null=True)

    def __str__(self):
        return f"Experience Certificate - {self.employee.name}"

    class Meta:
        db_table = 'experience_certificates'
        verbose_name = 'Experience Certificate'
        verbose_name_plural = 'Experience Certificates'

    # Property methods to access employee data
    @property
    def address(self):
        return self.employee.address if self.employee else None

    @property
    def joining_date(self):
        return self.employee.joining_date if self.employee else None

    @property
    def job_title(self):
        return self.employee.job_title if self.employee else None






import os
import uuid
import json
from django.db import models

class JobCard(models.Model):
    STATUS_CHOICES = [
        ('logged', 'Logged'),
        ('sent_technician', 'Sent To Technician'),
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('returned', 'Returned'),
        ('rejected', 'Rejected'),
    ]

    ticket_no = models.CharField(max_length=20, unique=True, blank=True)
    customer = models.CharField(max_length=100)
    address = models.TextField()
    phone = models.CharField(max_length=15)
    
    # Store all items and complaints as JSON data
    items_data = models.JSONField(default=list, help_text="Stores array of items with their complaints")
    # Structure: [
    #   {
    #     "item": "Laptop",
    #     "serial": "ABC123",
    #     "config": "i5, 8GB RAM",
    #     "status": "logged",
    #     "complaints": [
    #       {
    #         "description": "Screen flickering",
    #         "notes": "Happens after 30 minutes"
    #       },
    #       {
    #         "description": "Battery not charging",
    #         "notes": "Need new battery"
    #       }
    #     ]
    #   }
    # ]
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def _str_(self):
        return f"{self.customer} - {self.ticket_no}"
    
    def save(self, *args, **kwargs):
        if not self.ticket_no:
            self.ticket_no = self.generate_ticket_number()
        super().save(*args, **kwargs)

    def generate_ticket_number(self):
        while True:
            ticket_no = f"TK-{uuid.uuid4().hex[:8].upper()}"
            if not JobCard.objects.filter(ticket_no=ticket_no).exists():
                return ticket_no

    def delete(self, *args, **kwargs):
        # Delete all associated images
        for image in self.images.all():
            image.delete()
        super().delete(*args, **kwargs)

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


class JobCardImage(models.Model):
    jobcard = models.ForeignKey(JobCard, related_name='images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='jobcard_images/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    # Additional fields to identify which item and complaint this image belongs to
    item_index = models.IntegerField(default=0, help_text="Index of item in items_data array")
    complaint_index = models.IntegerField(default=0, help_text="Index of complaint within item")

    def _str_(self):
        return f"Image for {self.jobcard.customer} - {self.jobcard.ticket_no}"

    def delete(self, *args, **kwargs):
        if self.image and os.path.isfile(self.image.path):
            os.remove(self.image.path)
        super().delete(*args, **kwargs)

    class Meta:
        ordering = ['item_index', 'complaint_index', 'uploaded_at']