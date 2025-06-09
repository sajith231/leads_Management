from django.db import models
from django.contrib.auth.models import User
from app1.models import Employee  # Adjust import based on app structure

class SalaryCertificate(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    address = models.CharField(max_length=255, blank=True, null=True)
    joining_date = models.DateField(blank=True, null=True)
    job_title = models.CharField(max_length=100, blank=True, null=True)
    salary = models.DecimalField(max_digits=10, decimal_places=2)
    is_approved = models.BooleanField(default=False)
    
    # New fields
    added_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='added_certificates')
    added_on = models.DateTimeField(auto_now_add=True)
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_certificates')
    approved_on = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Salary Certificate - {self.employee.name}"

    def save(self, *args, **kwargs):
        # Populate fields from the associated Employee instance
        self.address = self.employee.address
        self.joining_date = self.employee.joining_date
        self.job_title = self.employee.job_title
        super().save(*args, **kwargs)