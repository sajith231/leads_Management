from django.db import models
from django.contrib.auth.models import User
from purchase_order.models import Department


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
        ('paid', 'Paid'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    # --- client / purpose ---------------------------------------------
    client = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Optional client code or identifier"
    )
    client_name = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Optional client name (can be blank)"
    )
    purpose = models.TextField(blank=True, null=True)

    # --- department is now a FK to master Department table -------------
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='claims'
    )

    expense_type = models.CharField(max_length=50, choices=EXPENSE_TYPES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField()
    receipt = models.FileField(upload_to='receipts/', blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='claimed')

    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='claims',
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        related_name='claims_updated',
        null=True,
        blank=True
    )
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        who = self.created_by.username if self.created_by else 'Unknown'
        identifier = self.client_name or (self.purpose[:30] if self.purpose else 'No Client/Purpose')
        return f"{identifier} - {self.get_expense_type_display()} - {self.amount} ({who})"

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Claim"
        verbose_name_plural = "Claims"
