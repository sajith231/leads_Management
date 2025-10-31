from decimal import Decimal
from django.core.validators import MinValueValidator
from django.db import models
from django.urls import reverse
from django.core.exceptions import ValidationError
from django.conf import settings
from django.utils import timezone

class Vehicle(models.Model):
    FUEL_TYPES = [
        ('petrol', 'Petrol'),
        ('diesel', 'Diesel'),
    ]
    
    vehicle_number = models.CharField(max_length=20, unique=True)
    vehicle_name = models.CharField(max_length=100, help_text="Name of the vehicle")
    model_number = models.CharField(max_length=50, help_text="Model number of the vehicle")
    manufacture_year = models.PositiveIntegerField(
        help_text="Year of manufacture",
        validators=[MinValueValidator(1900)],
        default=2030  # Default value for existing records
    )
    owner_name = models.CharField(max_length=100)
    fuel_type = models.CharField(
        max_length=10, 
        choices=FUEL_TYPES, 
        default='petrol',
        help_text="Type of fuel used by the vehicle"
    )
    fuel_rate = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Current fuel rate in rupees per liter"
    )
    rc_copy = models.FileField(upload_to='docs/rc/', blank=True, null=True)
    insurance_copy = models.FileField(upload_to='docs/ins/', blank=True, null=True)
    pollution_copy = models.FileField(upload_to='docs/pol/', blank=True, null=True)
    avg_mileage = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Average mileage in km/l"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.vehicle_number} — {self.vehicle_name} — {self.owner_name}"

    def get_absolute_url(self):
        return reverse('vehicle_edit', kwargs={'vehicle_id': self.id})

    def save(self, *args, **kwargs):
        # Auto-set fuel rate based on fuel type if not explicitly set
        if not self.fuel_rate or self.fuel_rate == Decimal('0.00'):
            if self.fuel_type == 'diesel':
                self.fuel_rate = Decimal('95.86')
            else:  # petrol
                self.fuel_rate = Decimal('106.93')
        super().save(*args, **kwargs)


class FuelEntry(models.Model):
    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.CASCADE,
        related_name='fuel_entries',
        null=True,
        blank=True,
        help_text="Link this fuel entry to a vehicle"
    )

    # ✅ Add user tracking for logged-in user
    travelled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,  # <-- fixed reference
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='fuel_trips',
        help_text="User who performed the trip"
    )

    date = models.DateField(help_text="Date of the trip")

    start_time = models.TimeField(null=True, blank=True, help_text="Trip start time")
    end_time = models.TimeField(null=True, blank=True, help_text="Trip end time")

    trip_from = models.CharField(
        max_length=100,
        default='',
        blank=True,
        help_text="Starting point of the trip"
    )
    trip_to = models.CharField(
        max_length=100,
        default='',
        blank=True,
        help_text="Destination point of the trip"
    )

    fuel_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Total cost of the fuel"
    )

    odo_start_reading = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Odometer reading before the trip"
    )
    odo_end_reading = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Odometer reading after the trip"
    )

    odo_start_image = models.ImageField(upload_to='odo_images/start/', blank=True, null=True)
    odo_end_image = models.ImageField(upload_to='odo_images/end/', blank=True, null=True)

    fuel_quantity = models.DecimalField(
        max_digits=8,
        decimal_places=3,
        default=Decimal('0.000'),
        validators=[MinValueValidator(Decimal('0.000'))],
        help_text="Fuel quantity filled in liters"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', '-created_at']
        verbose_name_plural = "Fuel Entries"

    def __str__(self):
        date_str = self.date.strftime("%Y-%m-%d") if self.date else "—"
        return f"{self.trip_from or '—'} → {self.trip_to or '—'} ({date_str})"

    def clean(self):
        """Ensure end odometer >= start odometer."""
        if self.odo_end_reading < self.odo_start_reading:
            raise ValidationError({
                'odo_end_reading': "End reading cannot be less than start reading."
            })

    def distance_traveled(self):
        """Return total kilometers traveled."""
        return self.odo_end_reading - self.odo_start_reading

    def fuel_efficiency(self):
        """Return km/l value if fuel quantity is known."""
        if self.fuel_quantity and self.fuel_quantity > 0:
            return self.distance_traveled() / self.fuel_quantity
        return None

    @classmethod
    def get_last_odometer_reading(cls):
        """Get the last odometer reading from the most recent trip"""
        last_entry = cls.objects.all().order_by('-date', '-created_at').first()
        if last_entry:
            return last_entry.odo_end_reading
        return Decimal('0.00')