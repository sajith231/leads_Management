from django.db import models
from django.utils import timezone
from app1.models import Employee, Attendance, LeaveRequest, LateRequest, EarlyRequest
from wfh_Request.models import WorkFromHomeRequest

class CancelRequest(models.Model):
    REQUEST_TYPE_CHOICES = [
        ('late', 'Late'),
        ('early', 'Early'),
        ('leave', 'Leave'),
        ('wfh', 'Work From Home'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    request_type = models.CharField(max_length=20, choices=REQUEST_TYPE_CHOICES)
    request_id = models.IntegerField()  # ID of related request
    reason = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(default=timezone.now)
    processed_by = models.CharField(max_length=100, blank=True, null=True)
    processed_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"{self.employee.name} - {self.request_type} ({self.status})"
