from django.db import models
from django.contrib.auth.models import User

class Wallet(models.Model):
    UPLOAD_TYPE_CHOICES = [
        ('bank', 'Bank/Details'),
        ('qr', 'QR Code'),
        ('document', 'Documentation Image'),
        ('pdf', 'PDF Document'),
        ('other', 'Address Book'),
        ('ofdocs_imc_dev', 'Ofdocs - IMC DEV'),
        ('ofdocs_imc_ho', 'Ofdocs - IMC HO'),
        ('ofdocs_imc_mukkam', 'Ofdocs - IMC Mukkam'),
        ('ofdocs_sysmac', 'Ofdocs - Sysmac'),
        ('ofdocs_sysmac_info', 'Ofdocs - Sysmac Info'),
        ('ofdocs_sysmac_old', 'Ofdocs - Sysmac Old'),
        ('vehicle_data', 'Vehicle Data'),
    ]
    
    VISIBILITY_CHOICES = [
        ('superadmin', 'Super Admin'),
        ('admin', 'Admin'),
        ('user', 'User'),
    ]
    
    title = models.CharField(max_length=255)
    upload_type = models.CharField(max_length=50, choices=UPLOAD_TYPE_CHOICES)
    visibility_priority = models.CharField(max_length=50, choices=VISIBILITY_CHOICES)
    description = models.TextField(blank=True, null=True)
    
    # Image field (used for bank, qr, document, pdf thumbnail, other)
    image = models.ImageField(upload_to='wallet_images/', blank=True, null=True)
    
    # PDF file field (used for pdf type)
    pdf_file = models.FileField(upload_to='wallet_pdfs/', blank=True, null=True)
    
    # Bank-specific fields
    account_holder_name = models.CharField(max_length=255, blank=True, null=True)
    account_number = models.CharField(max_length=100, blank=True, null=True)
    ifsc_code = models.CharField(max_length=20, blank=True, null=True)
    bank_address = models.TextField(blank=True, null=True)
    
    # QR-specific fields
    qr_name = models.CharField(max_length=255, blank=True, null=True)
    
    # PDF-specific fields
    pdf_name = models.CharField(max_length=255, blank=True, null=True)
    
    # Address Book-specific fields (renamed from other)
    other_name = models.CharField(max_length=255, blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    def __str__(self):
        return self.title
    
    class Meta:
        ordering = ['-created_at']