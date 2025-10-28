from django.db import models
from django.contrib.auth.models import User

class Claim(models.Model):
    EXPENSE_TYPES = [
        ('travel', 'Travel/Public Transport Expense'),
        ('food', 'Food/Meal Expense'),
        ('accommodation', 'Accommodation Expense'),
        ('fuel', 'Fuel/Parking and Toll Expense'),
        ('self', 'Self/Personal Expense'),
    ]

    STATUS_CHOICES = [
        ('claimed', 'Claimed'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    client = models.CharField(max_length=255)
    client_name = models.CharField(max_length=255, blank=True)
    expense_type = models.CharField(max_length=50, choices=EXPENSE_TYPES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField()

    # ✅ Make receipt optional so "self" can skip uploads
    receipt = models.FileField(upload_to='receipts/', blank=True, null=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='claimed')

    # Created/Updated metadata
    created_by = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='claims', null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    # ✅ Add fields referenced by the edit view
    updated_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, related_name='claims_updated',
        null=True, blank=True
    )
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        who = self.created_by.username if self.created_by else 'Unknown'
        return f"{self.client_name} - {self.get_expense_type_display()} - {self.amount} ({who})"

    class Meta:
        ordering = ['-created_at']
