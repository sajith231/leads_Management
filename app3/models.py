# app/models.py

from django.db import models
from app1.models import Employee  # Adjust import based on app structure

class SalaryCertificate(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    address = models.CharField(max_length=255, blank=True, null=True)
    joining_date = models.DateField(blank=True, null=True)
    job_title = models.CharField(max_length=100, blank=True, null=True)
    salary = models.DecimalField(max_digits=10, decimal_places=2)
    is_approved = models.BooleanField(default=False)

    def __str__(self):
        return f"Salary Certificate - {self.employee.name}"

    def save(self, *args, **kwargs):
        # Populate fields from the associated Employee instance
        self.address = self.employee.address
        self.joining_date = self.employee.joining_date
        self.job_title = self.employee.job_title
        super().save(*args, **kwargs)
