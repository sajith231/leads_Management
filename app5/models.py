# models.py (updated)
from django.db import models
import os
import uuid
import json
from app1.models import User 

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
    phone = models.CharField(max_length=50)
    technician = models.CharField(max_length=100, blank=True, null=True)
    completion_details = models.JSONField(default=dict, blank=True)
    assigned_date = models.DateTimeField(null=True, blank=True)
    self_assigned = models.BooleanField(default=False, help_text="True if the job was self-assigned by the creator")
    standby_issued = models.BooleanField(default=False, help_text="Whether standby equipment was issued")
    # Store all items and complaints as JSON data
    items_data = models.JSONField(default=list, help_text="Stores array of items with their complaints")

    # ✅ Add this field
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='logged'
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="jobcards"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
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

    def __str__(self):
        return f"Image for {self.jobcard.customer} - {self.jobcard.ticket_no}"

    def delete(self, *args, **kwargs):
        if self.image and os.path.isfile(self.image.path):
            os.remove(self.image.path)
        super().delete(*args, **kwargs)

    class Meta:
        ordering = ['item_index', 'complaint_index', 'uploaded_at']


# Model item master
class Item(models.Model):
    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.name
    


# supplier

class Supplier(models.Model):
    serial_no = models.CharField(max_length=50)  # <-- new field
    name = models.CharField(max_length=200)
    place = models.CharField(max_length=200)
    phone = models.CharField(max_length=20)
    address = models.TextField()


    def __str__(self):
        return self.name



# Add these models to your app5/models.py file

# app2/models.py  (or wherever your models live)
from django.db import models
from django.contrib.auth.models import User as AuthUser
from app1.models import User
import json
from django.utils import timezone

class JobCard(models.Model):
    STATUS_CHOICES = [
        ('logged', 'Logged'),
        ('sent_technician', 'Sent To Technician'),
        ('accepted', 'In Technician Hand'),
        ('completed', 'Completed'),
        ('returned', 'Returned'),
        ('rejected', 'Rejected'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ]

    ticket_no = models.CharField(max_length=20, unique=True, blank=True, null=True)
    customer = models.CharField(max_length=200)
    address = models.TextField()
    phone = models.CharField(max_length=15)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='logged')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    
    # Technician assignment
    technician = models.CharField(max_length=100, blank=True, null=True)
    assigned_date = models.DateTimeField(null=True, blank=True)
    self_assigned = models.BooleanField(default=False)
    
    # Standby item tracking
    standby_issued = models.BooleanField(default=False)
    
    # Items and complaints data (stored as JSON)
    items_data = models.JSONField(default=list, blank=True)
    completion_details = models.JSONField(default=dict, blank=True, null=True)
    
    # Timestamps and creator
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_jobcards')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.ticket_no:
            # Get last job card
            last_job = JobCard.objects.order_by('-id').first()
            number = 0
            if last_job and last_job.ticket_no:
                # Extract only digits from ticket_no safely
                digits = ''.join(filter(str.isdigit, last_job.ticket_no))
                if digits:
                    number = int(digits)
            self.ticket_no = f"JC{number + 1:06d}"

        # Set assigned_date when technician is assigned
        if self.technician and not self.assigned_date:
            self.assigned_date = timezone.now()
            
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.ticket_no} - {self.customer}"

    class Meta:
        ordering = ['-created_at']


class JobCardImage(models.Model):
    jobcard = models.ForeignKey(JobCard, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='jobcard_images/')
    item_index = models.IntegerField(default=0)
    complaint_index = models.IntegerField(default=0)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Image for {self.jobcard.ticket_no}"


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


class Item(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']


class Supplier(models.Model):
    name = models.CharField(max_length=200)
    place = models.CharField(max_length=100)
    phone = models.CharField(max_length=15)
    address = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']


        