from django.db import models

# Create your models here.
from django.db import models

class Vehicle(models.Model):
    vehicle_number = models.CharField(max_length=20, unique=True)
    owner_name     = models.CharField(max_length=100)
    rc_copy        = models.FileField(upload_to='docs/rc/')
    insurance_copy = models.FileField(upload_to='docs/ins/')
    pollution_copy = models.FileField(upload_to='docs/pol/')
    created_at     = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.vehicle_number} – {self.owner_name}"