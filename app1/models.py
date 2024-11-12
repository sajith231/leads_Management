# models.py
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

class User(models.Model):
    name = models.CharField(max_length=100)
    userid = models.CharField(max_length=100, unique=True)
    password = models.CharField(max_length=100)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

    @classmethod
    def authenticate(cls, userid, password):
        try:
            user = cls.objects.get(userid=userid, password=password, is_active=True)
            return user
        except cls.DoesNotExist:
            return None
        


class Lead(models.Model):
    BUSINESS_NATURE_CHOICES = [
        ('', 'Select'),  # This will be disabled
        ('supermarket', 'Supermarket'),
        ('textile', 'Textile'),
        ('restaurant', 'Restaurant'),
        ('retail', 'Retail'),
        ('wholesale', 'Wholesale'),
        ('footware', 'Footware'),
        ('hardware', 'Hardware'),
        ('pharmacy', 'Pharmacy'),
        ('hospital', 'Hospital'),
        ('clinic', 'Clinic'),
        ('another', 'Another'),
    ]

    SOFTWARE_CHOICES = [
         # This will be disabled
        ('TASK', 'TASK'),
        ('B CARE', 'B CARE'),
        ('I CARE', 'I CARE'),
        ('SHADE', 'SHADE'),
        ('VTASK', 'VTASK'),
        ('MAGNET', 'MAGNET'),
        ('DINE', 'DINE'),
        ('STARSTAY', 'STARSTAY'),
        ('AURIC', 'AURIC'),
        ('CLUBLOGIC', 'CLUBLOGIC'),
    ]

    firm_name = models.CharField(max_length=200)
    customer_name = models.CharField(max_length=100)
    contact_number = models.CharField(max_length=20)
    location = models.CharField(max_length=200)
    business_nature = models.CharField(
        max_length=100,
        choices=BUSINESS_NATURE_CHOICES,
        default=''
    )
    software = models.CharField(
        max_length=500,  # Increased to store multiple choices
        blank=True
    )
    requirements = models.ManyToManyField('Requirement')
    user = models.ForeignKey('User', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    follow_up_required = models.BooleanField(default=False)
    quotation_required = models.BooleanField(default=False)
    image = models.ImageField(upload_to='lead_images/', null=True, blank=True)
    remarks = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.firm_name} - {self.customer_name}"

    def get_software_list(self):
        if not self.software:
            return []
        # Remove any extra whitespace and split by comma
        return [s.strip() for s in self.software.split(',') if s.strip()]
    
    def get_software_display(self):
        """Returns software as a comma-separated string without brackets"""
        return ', '.join(self.get_software_list())
    