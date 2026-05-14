from rest_framework import serializers
from .models import Feeder

class FeederSerializer(serializers.ModelSerializer):
    # Add readable fields for foreign keys and choices
    branch_name = serializers.CharField(source='branch.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    nature_display = serializers.CharField(source='get_nature_display', read_only=True)
    status_class = serializers.CharField(source='get_status_display_class', read_only=True)
    
    # Add formatted dates
    installation_date_formatted = serializers.DateField(source='installation_date', format='%d/%m/%Y', read_only=True)
    
    class Meta:
        model = Feeder
        fields = '__all__'
        
    def to_representation(self, instance):
        """
        Customize the output to include additional formatted data for mobile app
        """
        representation = super().to_representation(instance)
        
        # Parse modules if stored as comma-separated string
        if instance.modules:
            representation['modules_list'] = [m.strip() for m in instance.modules.split(',') if m.strip()]
        else:
            representation['modules_list'] = []
        
        # Parse more_modules if stored as comma-separated string
        if instance.more_modules:
            representation['more_modules_list'] = [m.strip() for m in instance.more_modules.split(',') if m.strip()]
        else:
            representation['more_modules_list'] = []
        
        return representation