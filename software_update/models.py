from django.db import models
from django.conf import settings

class SoftwareComplaint(models.Model):
    client_name = models.CharField(max_length=200)
    branch = models.CharField(max_length=200)
    software = models.CharField(max_length=100)
    description = models.TextField()
    images = models.TextField(blank=True, null=True)
    voice_note = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=50, default='Pending')

    # ✅ FIXED HERE
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='software_complaints'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.client_name} - {self.software}"
