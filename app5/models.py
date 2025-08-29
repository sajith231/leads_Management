from django.db import models

# Create your models here.


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
    technician = models.CharField(max_length=100, blank=True, null=True)

    # Store all items and complaints as JSON data
    items_data = models.JSONField(default=list, help_text="Stores array of items with their complaints")

    # ✅ Add this field
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='logged'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):  # also fixed __str__
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




#model item master
        
class Item(models.Model):
    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.name
    

    