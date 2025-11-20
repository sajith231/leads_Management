from django.contrib import admin
from .models import VehicleDetail, Challan

@admin.register(VehicleDetail)
class VehicleDetailAdmin(admin.ModelAdmin):
    list_display = ['vehicle', 'detail_date', 'description', 'created_at']
    list_filter = ['detail_date', 'vehicle']
    search_fields = ['vehicle__vehicle_number', 'description']
    date_hierarchy = 'detail_date'

@admin.register(Challan)
class ChallanAdmin(admin.ModelAdmin):
    list_display = ['challan_number', 'vehicle', 'challan_date', 'offense_type', 
                    'fine_amount', 'status', 'payment_date', 'get_user']
    list_filter = ['status', 'challan_date', 'vehicle']
    search_fields = ['challan_number', 'vehicle__vehicle_number', 'offense_type']
    date_hierarchy = 'challan_date'
    readonly_fields = ['created_at', 'updated_at']
    
    def get_user(self, obj):
        """Display the user associated with the challan through fuel entry"""
        user = obj.get_user()
        return user.name if user else '-'
    get_user.short_description = 'User'