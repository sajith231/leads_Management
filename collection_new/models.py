from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_delete, pre_delete
from django.dispatch import receiver
import logging

logger = logging.getLogger(__name__)


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
    cloudflare_r2_url = models.URLField(blank=True, null=True, help_text='Cloudflare R2 public URL for the payment proof')
    cloudflare_r2_key = models.CharField(max_length=500, blank=True, null=True, help_text='Cloudflare R2 S3 object key for deletion')
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


@receiver(pre_delete, sender=Collection)
def delete_cloudflare_file(sender, instance, **kwargs):
    """
    Signal handler to delete file from Cloudflare R2 when a Collection is deleted.
    """
    if instance.cloudflare_r2_key:
        try:
            from common.cloudflare_storage import delete_from_cloudflare
            result = delete_from_cloudflare(instance.cloudflare_r2_key)
            if result['success']:
                logger.info(f"Deleted R2 file: {instance.cloudflare_r2_key}")
            else:
                logger.warning(f"Failed to delete R2 file {instance.cloudflare_r2_key}: {result['message']}")
        except Exception as e:
            logger.error(f"Error deleting R2 file for Collection {instance.id}: {str(e)}")