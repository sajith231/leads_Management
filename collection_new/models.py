from django.db import models
from django.contrib.auth.models import User


class Collection(models.Model):
    COLLECTION_TYPE_CHOICES = [
        ('cash',          'Cash'),
        ('cheque',        'Cheque'),
        ('bank_transfer', 'Bank Transfer'),
        ('upi',           'UPI'),
        ('other',         'Other'),
    ]

    COMPANY_CHOICES = [
        ('Sysmac Computers', 'Sysmac Computers'),
        ('Sysmac Info',      'Sysmac Info'),
        ('IMCB LLP',         'IMCB LLP'),
    ]

    company         = models.CharField(max_length=100, choices=COMPANY_CHOICES)
    department      = models.CharField(max_length=255)
    client_name     = models.CharField(max_length=255)
    collection_type = models.CharField(max_length=20, choices=COLLECTION_TYPE_CHOICES)
    amount          = models.DecimalField(max_digits=12, decimal_places=2)
    paid_for        = models.CharField(max_length=255)
    STATUS_CHOICES = [
        ('pending',  'Pending'),
        ('verified', 'Verified'),
    ]

    payment_proof   = models.FileField(upload_to='collection_proofs/', blank=True, null=True)
    notes           = models.TextField(blank=True, null=True)
    status          = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_by      = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='collections')
    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Collection'
        verbose_name_plural = 'Collections'

    def __str__(self):
        return f"{self.client_name} - ₹{self.amount} ({self.get_collection_type_display()})"

    @property
    def proof_required(self):
        return self.collection_type in ('cheque', 'upi', 'bank_transfer')