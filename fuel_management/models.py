from django.db import models
from django.urls import reverse

class Vehicle(models.Model):
    vehicle_number = models.CharField(max_length=20, unique=True)
    owner_name     = models.CharField(max_length=100)
    rc_copy        = models.FileField(upload_to='docs/rc/', blank=True, null=True)
    insurance_copy = models.FileField(upload_to='docs/ins/', blank=True, null=True)
    pollution_copy = models.FileField(upload_to='docs/pol/', blank=True, null=True)
    avg_mileage    = models.DecimalField(max_digits=6, decimal_places=2, default=0, help_text="Average mileage in km/l")
    created_at     = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.vehicle_number} — {self.owner_name}"
    
    def get_absolute_url(self):
        return reverse('vehicle_edit', kwargs={'vehicle_id': self.id})


class FuelEntry(models.Model):
    VEHICLE_TYPE_CHOICES = [
        ('two wheeler', 'Two wheeler'),
        ('four wheeler', 'Four wheeler'),
    ]
    
    vehicle_type = models.CharField(max_length=20, choices=VEHICLE_TYPE_CHOICES)
    staff_name = models.CharField(max_length=100)
    date = models.DateField()
    odo_start = models.DecimalField(max_digits=10, decimal_places=2)
    odo_end = models.DecimalField(max_digits=10, decimal_places=2)
    trip_from = models.CharField(max_length=100)
    trip_to = models.CharField(max_length=100)
    fuel_cost = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.vehicle_type} - {self.staff_name} - {self.date}"
    
    def distance_traveled(self):
        return self.odo_end - self.odo_start

    class Meta:
        ordering = ['-date', '-created_at']