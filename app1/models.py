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
        ('', 'Select'), 
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
        """Returns a list of dictionaries containing software names and their amounts"""
        if not self.software:
            return []
        
        # Get software names from the comma-separated string
        software_names = [s.strip() for s in self.software.split(',') if s.strip()]
        
        # Get all software amounts for this lead
        amounts = self.software_amounts.all()
        
        # Create a list of dictionaries with software names and amounts
        result = []
        for software in software_names:
            amount = next((amt.amount for amt in amounts if amt.software_name == software), None)
            result.append({
                'name': software,
                'amount': amount
            })
        return result
    
    
class SoftwareAmount(models.Model):
    lead = models.ForeignKey('Lead', on_delete=models.CASCADE, related_name='software_amounts')
    software_name = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('lead', 'software_name')

    def __str__(self):
        return f"{self.software_name} - {self.amount}"
