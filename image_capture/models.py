from django.db import models
import uuid

class ImageCapture(models.Model):
    unique_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    customer_name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=15)
    image = models.ImageField(upload_to='customer_images/', blank=True, null=True)
    latitude = models.CharField(max_length=50, blank=True, null=True)
    longitude = models.CharField(max_length=50, blank=True, null=True)
    location_name = models.CharField(max_length=500, blank=True, null=True)
    verified = models.BooleanField(default=False)

    # ✅ NEW FIELD
    status = models.CharField(
        max_length=20,
        choices=[('Pending', 'Pending'), ('Verified', 'Verified')],
        default='Pending'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['verified', '-created_at']),
        ]

    def __str__(self):
        return f"{self.customer_name} - {self.phone_number}"
