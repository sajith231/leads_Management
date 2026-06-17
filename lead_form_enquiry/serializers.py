from rest_framework import serializers
from .models import Enquiry

class EnquirySerializer(serializers.ModelSerializer):
    class Meta:
        model  = Enquiry
        fields = [
            'id', 'date', 'creator', 'owner_name', 'shop_name', 'location',
            'phone_number', 'purpose', 'notes', 'latitude', 'longitude'
        ]
        read_only_fields = ['id', 'date']