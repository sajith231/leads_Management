
# models.py
from django.db import models

class Field(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name


class Credentials(models.Model):
    name = models.CharField(max_length=255)
    category = models.CharField(max_length=255, blank=True, null=True)#CREATED AS NEW
    remark = models.CharField(max_length=255, blank=True, null=True)#CREATED AS NEW
    
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