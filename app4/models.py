from django.db import models


# app2/models.py

from django.db import models
from app1.models import Branch

class License(models.Model):
    name             = models.CharField(max_length=255)
    branch           = models.ForeignKey(Branch, on_delete=models.CASCADE)
    service_pack     = models.CharField(max_length=255, blank=True, null=True)
    place            = models.CharField(max_length=255, blank=True, null=True)
    type             = models.CharField(max_length=255, blank=True, null=True)
    number_of_system = models.CharField(max_length=50, blank=True, null=True)
    module           = models.CharField(max_length=255, blank=True, null=True)
    notes            = models.TextField(blank=True, null=True)

    license_key = models.TextField()
    file_name   = models.CharField(max_length=255, blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        display = self.file_name or self.name
        return f"{display} ({self.branch.name})"



class Printer(models.Model):
    name = models.CharField(max_length=100)



from django.db import models

class KeyRequest(models.Model):
    client_id = models.IntegerField()
    client_name = models.CharField(max_length=255)
    request_title = models.CharField(max_length=255)
    image_file = models.ImageField(upload_to='key_requests/', blank=True, null=True)
    additional_requests = models.TextField(blank=True)  # store comma-separated values
    comments = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.client_name} - {self.request_title}"
