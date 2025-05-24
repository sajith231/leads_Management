
# models.py
from django.db import models

class Field(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name


class Credentials(models.Model):
    name = models.CharField(max_length=255)
    category = models.CharField(max_length=255, blank=True, null=True)
    remark = models.CharField(max_length=255, blank=True, null=True)
    credential_type = models.CharField(max_length=50, choices=[('priority 1', 'Priority 1'), ('priority 2', 'Priority 2')], default='priority 1')

    
    def __str__(self):
        return self.name
    


class CredentialDetail(models.Model):
    credential = models.ForeignKey(Credentials, on_delete=models.CASCADE, related_name='details')
    field = models.ForeignKey(Field, on_delete=models.CASCADE)
    value = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.credential.name} - {self.field.name}"
    




class Category(models.Model):
    name = models.CharField(max_length=255, unique=True)
    
    def __str__(self):
        return self.name
    


#CREATED AS NEW
#CREATED AS NEW
#CREATED AS NEW
#CREATED AS NEW
#CREATED AS NEW


from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class ProductType(models.Model):
    name = models.CharField(max_length=100)
    
    def __str__(self):
        return self.name

class ProductCategory(models.Model):
    name = models.CharField(max_length=100)
    
    
    def __str__(self):
        return self.name

PRIORITY_CHOICES = [
    ('priority1', 'Priority 1'),
    ('priority2', 'Priority 2'),
]

class InformationCenter(models.Model):
    title = models.CharField(max_length=200)
    remark = models.TextField(blank=True)
    url = models.URLField()
    added_date = models.DateField(default=timezone.now)
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE)
    product_type = models.ForeignKey(ProductType, on_delete=models.CASCADE)
    product_category = models.ForeignKey(ProductCategory, on_delete=models.CASCADE)
    thumbnail = models.ImageField(upload_to='information_thumbnails/')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES)
    
    def __str__(self):
        return self.title
    








from django.db import models
from django.contrib.auth.models import User

class DailyTask(models.Model):
    STATUS_CHOICES = [
        ('complete', 'Complete'),
        ('started', 'Started'),
        ('finish', 'Finish'),
        ('in_progress', 'In Progress'),
    ]
    project = models.CharField(max_length=255)
    task = models.CharField(max_length=255)
    duration = models.CharField(max_length=50)  # Changed to CharField
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    added_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    remark = models.TextField(blank=True, null=True) 

    def __str__(self):
        return f"{self.task} in {self.project}"