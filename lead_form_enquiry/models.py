from django.db import models

class Enquiry(models.Model):
    date         = models.DateTimeField(auto_now_add=True)
    creator      = models.CharField(max_length=150)
    owner_name   = models.CharField(max_length=200, blank=True)
    shop_name    = models.CharField(max_length=200)
    location     = models.CharField(max_length=200)
    phone_number = models.CharField(max_length=20, blank=True)
    purpose      = models.CharField(max_length=100)
    notes        = models.TextField(blank=True)
    latitude     = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude    = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    def __str__(self):
        return f"{self.shop_name} – {self.purpose}"