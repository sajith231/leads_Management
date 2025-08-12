from django.db import models


# app2/models.py

from django.db import models
from app1.models import Branch

class License(models.Model):
    name = models.CharField(max_length=255)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE)
    # New fields
    service_pack = models.CharField(max_length=255, blank=True, null=True)
    place = models.CharField(max_length=255, blank=True, null=True)
    type = models.CharField(max_length=255, blank=True, null=True)
    number_of_system = models.CharField(max_length=50, blank=True, null=True)
    # store base64-encoded file bytes here
    license_key = models.TextField()
    # store original uploaded filename (optional, useful for download)
    file_name = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        # show file_name if present, else name
        display = self.file_name if self.file_name else self.name
        return f"{display} ({self.branch.name})"



class Printer(models.Model):
    name = models.CharField(max_length=100)
