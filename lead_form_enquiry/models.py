from django.db import models
from django.db.models.signals import pre_delete
from django.dispatch import receiver
import logging

logger = logging.getLogger(__name__)


class Enquiry(models.Model):
    date         = models.DateTimeField(auto_now_add=True)
    creator      = models.CharField(max_length=150)
    owner_name   = models.CharField(max_length=200, blank=True)
    shop_name    = models.CharField(max_length=200)
    location     = models.CharField(max_length=200)
    phone_number = models.CharField(max_length=20, blank=True)
    purpose      = models.CharField(max_length=100)
    notes        = models.TextField(blank=True)
    latitude     = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude    = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    image        = models.ImageField(upload_to='enquiry/images/', null=True, blank=True)
    audio        = models.FileField(upload_to='enquiry/audio/',  null=True, blank=True)
    
    # Cloudflare R2 storage fields
    cloudflare_image_url = models.URLField(blank=True, null=True, help_text='Cloudflare R2 public URL for image')
    cloudflare_image_key = models.CharField(max_length=500, blank=True, null=True, help_text='Cloudflare R2 S3 object key for image')
    cloudflare_audio_url = models.URLField(blank=True, null=True, help_text='Cloudflare R2 public URL for audio')
    cloudflare_audio_key = models.CharField(max_length=500, blank=True, null=True, help_text='Cloudflare R2 S3 object key for audio')

    def __str__(self):
        return f"{self.shop_name} – {self.purpose}"


@receiver(pre_delete, sender=Enquiry)
def delete_cloudflare_files(sender, instance, **kwargs):
    """
    Signal handler to delete files from Cloudflare R2 when an Enquiry is deleted.
    """
    files_to_delete = [
        (instance.cloudflare_image_key, 'image'),
        (instance.cloudflare_audio_key, 'audio'),
    ]
    
    try:
        from common.cloudflare_storage import delete_from_cloudflare
        
        for file_key, file_type in files_to_delete:
            if file_key:
                result = delete_from_cloudflare(file_key)
                if result['success']:
                    logger.info(f"Deleted R2 {file_type} file: {file_key}")
                else:
                    logger.warning(f"Failed to delete R2 {file_type} file {file_key}: {result['message']}")
    except Exception as e:
        logger.error(f"Error deleting R2 files for Enquiry {instance.id}: {str(e)}")