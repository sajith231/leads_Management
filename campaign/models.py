from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User

class Campaigning(models.Model):
    campaign_id = models.AutoField(primary_key=True)
    campaign_unique_id = models.CharField(max_length=50, unique=True, blank=True, null=True)
    campaign_name = models.CharField(max_length=200)
    software_name = models.CharField(max_length=200)
    status = models.CharField(max_length=20, default='draft', choices=[
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('completed', 'Completed')
    ])
    from_date = models.DateField()
    to_date = models.DateField()
    number_of_days = models.IntegerField()
    location = models.CharField(max_length=200, blank=True, null=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    total_reach = models.IntegerField(null=True, blank=True, default=0)
    total_impression = models.IntegerField(null=True, blank=True, default=0)
    total_leads = models.IntegerField(null=True, blank=True, default=0)
    is_deleted = models.BooleanField(default=False)
    
    # Add these fields
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='campaigns_created')
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    

    class Meta:
        ordering = ['-campaign_id']

    def save(self, *args, **kwargs):
        # Generate unique campaign ID if not exists
        if not self.campaign_unique_id:
            # Get the last campaign ID
            last_campaign = Campaigning.objects.all().order_by('-campaign_id').first()
            if last_campaign:
                last_id = last_campaign.campaign_id
                new_id = last_id + 1
            else:
                new_id = 1
            
            # Format: CMP-0001, CMP-0002, etc.
            self.campaign_unique_id = f"CMP-{new_id:04d}"
        
        super().save(*args, **kwargs)

    def __str__(self):
        return self.campaign_name