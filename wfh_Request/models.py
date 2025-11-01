from django.db import models
from django.conf import settings
from django.utils import timezone
from app1.models import Employee  # reuse your existing Employee

class WorkFromHomeRequest(models.Model):
    STATUS_CHOICES = [('pending','Pending'), ('approved','Approved'), ('rejected','Rejected')]
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    processed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                     on_delete=models.SET_NULL, related_name='processed_wfh_requests')
    processed_at = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if self.status in ('approved', 'rejected') and not self.processed_at:
            self.processed_at = timezone.now()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.employee.name} - {self.start_date} to {self.end_date} ({self.status})"
