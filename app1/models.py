from django.db import models
from django.utils import timezone
from django.contrib.auth.models import AbstractBaseUser

class Branch(models.Model):
    name = models.CharField(max_length=100)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

class Requirement(models.Model):
    name = models.CharField(max_length=100)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name
    
class District(models.Model):
    name = models.CharField(max_length=100)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

class Area(models.Model):
    name = models.CharField(max_length=100)
    district = models.ForeignKey(District, on_delete=models.CASCADE, related_name='areas')

    class Meta:
        ordering = ['name']
        unique_together = ('name', 'district')  # Ensure unique area names within a district

    def __str__(self):
        return f"{self.name} ({self.district.name} District)"
    

class Location(models.Model):
    name = models.CharField(max_length=100)
    district = models.ForeignKey(District, on_delete=models.CASCADE, related_name="locations")
    area = models.ForeignKey(Area, on_delete=models.CASCADE, related_name="locations")

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} - {self.area.name} ({self.district.name})"


class User(models.Model):
    USER_LEVEL_CHOICES = [
        ('normal', 'Normal User'),
        ('admin_level', 'Admin Level User'),
    ]

    name = models.CharField(max_length=100)
    userid = models.CharField(max_length=100, unique=True)
    password = models.CharField(max_length=100)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE)
    user_level = models.CharField(
        max_length=20,
        choices=USER_LEVEL_CHOICES,
        default='normal',
    )
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.get_user_level_display()})"

    @classmethod
    def authenticate(cls, userid, password):
        try:
            return cls.objects.get(userid=userid, password=password, is_active=True)
        except cls.DoesNotExist:
            return None


class Lead(models.Model):
    BUSINESS_NATURE_CHOICES = [
        ('', 'Select'),
        ('supermarket', 'Supermarket'),
        ('textile', 'Textile'),
        ('restaurant', 'Restaurant'),
        ('Agency/Distribution', 'Agency/Distribution'),
        ('retail', 'Retail'),
        ('Auto Mobiles', 'Auto Mobiles'),
        ('Bakery', 'Bakery'),
        ('Boutique', 'Boutique'),
        ('Hyper Market', 'Hyper Market'),
        ('Lab', 'Lab'),
        ('Opticals', 'Opticals'),
        ('Pharmacy', 'Pharmacy'),
        ('School', 'School'),
        ('Hotels/ Resorts', 'Hotels/ Resorts'),
        ('wholesale', 'Wholesale'),
        ('footware', 'Footware'),
        ('Travels', 'Travels'),
        ('Jewellery', 'Jewellery'),
        ('production', 'Production'),
        ('hardware', 'Hardware'),
        ('hospital', 'Hospital'),
        ('clinic', 'Clinic'),
        ('another', 'Another'),
    ]

    # Keep 'Select' first and 'Another' last, sort others alphabetically
    BUSINESS_NATURE_CHOICES = [BUSINESS_NATURE_CHOICES[0]] + sorted(
        BUSINESS_NATURE_CHOICES[1:-1],  # Exclude 'Select' and 'Another'
        key=lambda x: x[1].lower()      # Sort alphabetically by display value (case-insensitive)
    ) + [BUSINESS_NATURE_CHOICES[-1]]  # Append 'Another' at the end

    firm_name = models.CharField(max_length=200)
    customer_name = models.CharField(max_length=100)
    contact_number = models.CharField(max_length=20)
    landmark = models.CharField(max_length=200)
    business_nature = models.CharField(
        max_length=100,
        choices=BUSINESS_NATURE_CHOICES,
        default=''
    )
    requirements = models.ManyToManyField('Requirement')
    user = models.ForeignKey('User', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    follow_up_required = models.BooleanField(default=False)
    quotation_required = models.BooleanField(default=False)
    image = models.ImageField(upload_to='lead_images/', null=True, blank=True)
    remarks = models.TextField(blank=True, null=True)
    planet_entry = models.BooleanField(default=False)
    voice_note = models.FileField(upload_to='voice_notes/', null=True, blank=True)
    location = models.ForeignKey(Location, on_delete=models.SET_NULL, null=True, blank=True, related_name="leads")
    district = models.ForeignKey(District, on_delete=models.SET_NULL, null=True, blank=True, related_name="leads")
    area = models.ForeignKey(Area, on_delete=models.SET_NULL, null=True, blank=True, related_name="leads")
    hardwares = models.ManyToManyField('Hardware', blank=True, related_name='leads')
    added_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    added_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    
    def get_location_url(self):
        if self.added_latitude and self.added_longitude:
            return f"https://www.google.com/maps?q={self.added_latitude},{self.added_longitude}"
        return None
    

    def __str__(self):
        return f"{self.firm_name} - {self.customer_name}"
    

class LeadRequirementAmount(models.Model):
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name='requirement_amounts')
    requirement = models.ForeignKey(Requirement, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    remarks = models.TextField(blank=True, null=True)  # Add this field

    class Meta:
        unique_together = ('lead', 'requirement')

    def __str__(self):
        return f"{self.lead} - {self.requirement}: {self.amount}"





class Hardware(models.Model):
    name = models.CharField(max_length=200)
    specification = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} (₹{self.price})"
    
class LeadHardwarePrice(models.Model):
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name="hardware_prices")
    hardware = models.ForeignKey(Hardware, on_delete=models.CASCADE)
    custom_price = models.FloatField()

    class Meta:
        unique_together = ('lead', 'hardware')  # Enforces one price per lead-hardware combination

    def __str__(self):
        return f"Lead: {self.lead.firm_name}, Hardware: {self.hardware.name}, Price: ₹{self.custom_price}"

