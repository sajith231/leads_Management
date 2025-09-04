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




class KeyRequest(models.Model):
    KEY_TYPES = [
        ("Seat Upgradation Request", "Seat Upgradation Request"),
        ("More Module Request", "More Module Request"),
        ("Trade Name And Address Change Request", "Trade Name And Address Change Request"),
        ("Key type Change Request", "Key type Change Request"),
        ("Key Extension Request", "Key Extension Request"),
        ("Hosted Key Request", "Hosted Key Request"),
        ("Feeder Cancellation Request", "Feeder Cancellation Request"),
        ("Demo Key Request", "Demo Key Request"),
        ("Software Amount Change Request", "Software Amount Change Request"),
        ("Maturity Upgradation Request", "Maturity Upgradation Request"),
        ("Enterprises Key Request", "Enterprises Key Request"),
        ("Image Request", "Image Request"),
    ]

    STATUS_CHOICES = [
        ("Pending", "Pending"),
        ("On Process", "On Process"),
        ("Completed", "Completed"),
        ("Rejected", "Rejected"),
    ]

    REQUESTED_STATUS_CHOICES = [
        ("Requested", "Requested"),
        ("Pending", "Pending"),
        ("Rejected", "Rejected"),
        ("Working on it", "Working on it"),
        ("Work completed/Payment pending", "Work completed/Payment pending"),
        ("Work done & Payment collected", "Work done & Payment collected"),
    ]

    clientName = models.CharField(max_length=255)
    location = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    keyType = models.CharField(max_length=255, choices=KEY_TYPES)
    requestDate = models.DateField(null=True, blank=True)
    gps_location = models.CharField(max_length=100, blank=True, null=True)
    gps_address = models.CharField(max_length=255, blank=True, null=True)

    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="Pending"
    )
    requested_status = models.CharField(
        max_length=50,
        choices=REQUESTED_STATUS_CHOICES,
        default="Requested"
    )

    requestImage = models.ImageField(
        upload_to="key_request_images/", blank=True, null=True
    )
    
    # Changed from foreign key to simple text field
    branch_name = models.CharField(max_length=200, blank=True, null=True)
    
    amount = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        ordering = ["-id"]

    def __str__(self):
        return f"{self.clientName} - {self.keyType} ({self.requestDate})"