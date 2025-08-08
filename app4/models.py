from django.db import models


# app2/models.py

from django.db import models
from app1.models import Branch

class License(models.Model):
    name = models.CharField(max_length=255)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE)
    license_key = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return f"{self.name} ({self.branch.name})"


class Printer(models.Model):
    name = models.CharField(max_length=100)
