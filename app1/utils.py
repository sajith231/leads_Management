from django.utils import timezone
from .models import Holiday

def is_holiday(date=None):
    """
    Check if a given date is a holiday.
    If no date is provided, check for today.
    """
    if date is None:
        date = timezone.now().date()
    
    return Holiday.objects.filter(date=date).exists()