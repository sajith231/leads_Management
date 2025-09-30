from django.db import models

# Create your models here.
class SIM(models.Model):
    sim_no = models.CharField(max_length=50, unique=True)
    provider = models.CharField(max_length=100)
    identify_person = models.CharField(max_length=100, blank=True, null=True)
    incharge = models.CharField(max_length=100, blank=True, null=True)
    last_recharge_date = models.DateField(blank=True, null=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    branch = models.CharField(max_length=100, blank=True, null=True)
    validity_date = models.DateField(
        blank=True, null=True,
        help_text="Recharge valid until this date")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.sim_no} - {self.provider}"


# models.py - Add this model
class SIMRecharge(models.Model):
    sim = models.ForeignKey(SIM, on_delete=models.CASCADE, related_name='recharges')
    recharge_date = models.DateField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    recharged_by = models.CharField(max_length=100, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    validity_date = models.DateField(blank=True, null=True)
    class Meta:
        ordering = ['-recharge_date']
    
    def __str__(self):
        return f"{self.sim.sim_no} - {self.recharge_date} - ₹{self.amount}"