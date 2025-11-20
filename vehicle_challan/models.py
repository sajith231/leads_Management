from django.db import models
from app1.models import User

class VehicleDetail(models.Model):
    vehicle = models.ForeignKey(
        'fuel_management.Vehicle',
        on_delete=models.CASCADE,
        related_name='vehicle_details',
        db_column='vehicle_id'
    )
    detail_date = models.DateField()
    description = models.TextField()
    remarks = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-detail_date']
        db_table = 'vehicle_challan_vehicledetail'

    def __str__(self):
        return f"{self.vehicle.vehicle_number} - {self.detail_date}"


class Challan(models.Model):
    vehicle = models.ForeignKey(
        'fuel_management.Vehicle',
        on_delete=models.CASCADE,
        related_name='challans'
    )
    fuel_entry = models.ForeignKey(
        'fuel_management.FuelEntry',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='challans',
        help_text='Related fuel entry that this challan is associated with'
    )
    challan_number = models.CharField(max_length=100, unique=True)
    challan_date = models.DateField()
    offense_type = models.CharField(max_length=200)
    offense_location = models.CharField(max_length=300, blank=True, null=True)
    fine_amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('paid', 'Paid'),
            ('disputed', 'Disputed'),
        ],
        default='pending'
    )
    payment_date = models.DateField(null=True, blank=True)
    remarks = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-challan_date']

    def __str__(self):
        return f"{self.challan_number} - {self.vehicle.vehicle_number}"
    
    def get_user(self):
        """Get the user associated with this challan through fuel entry"""
        if self.fuel_entry and self.fuel_entry.user:
            return self.fuel_entry.user
        return None