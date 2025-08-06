from django.db import models

class License(models.Model):
    name = models.CharField(max_length=100)
    branch = models.CharField(max_length=100)
    license_key = models.TextField()

    def __str__(self):
        return f"{self.name} - {self.branch}"

class Printer(models.Model):
    name = models.CharField(max_length=100)
