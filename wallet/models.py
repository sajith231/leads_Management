from django.db import models
from django.contrib.auth.models import User

class Wallet(models.Model):
    UPLOAD_TYPE_CHOICES = [
        ('bank', 'Bank/Details'),
        ('qr', 'QR Code'),
        ('document', 'Documentation Image'),
        ('other', 'Other Wallet'),
    ]
    
    VISIBILITY_CHOICES = [
        ('superadmin', 'Super Admin'),
        ('admin', 'Admin'),
        ('user', 'User'),
    ]
    
    # Common fields
    title = models.CharField(max_length=200)
    upload_type = models.CharField(max_length=20, choices=UPLOAD_TYPE_CHOICES)
    visibility_priority = models.CharField(max_length=20, choices=VISIBILITY_CHOICES)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='wallet_images/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    
    # Bank/Details specific fields
    account_holder_name = models.CharField(max_length=200, blank=True)
    account_number = models.CharField(max_length=50, blank=True)
    ifsc_code = models.CharField(max_length=20, blank=True)
    bank_address = models.TextField(blank=True)
    
    # QR Code specific fields
    qr_name = models.CharField(max_length=200, blank=True)
    
    # Other Wallet specific fields
    other_name = models.CharField(max_length=200, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} - {self.upload_type}"