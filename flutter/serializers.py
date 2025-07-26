from rest_framework import serializers
from app1.models import User  # Adjust the import based on your actual app name

class UserLoginSerializer(serializers.Serializer):
    userid = serializers.CharField()
    password = serializers.CharField()

    def validate(self, data):
        userid = data.get('userid')
        password = data.get('password')

        if userid and password:
            try:
                user = User.objects.get(userid=userid, password=password, is_active=True)
                data['user'] = user
            except User.DoesNotExist:
                raise serializers.ValidationError("Invalid credentials")
        else:
            raise serializers.ValidationError("Must include 'userid' and 'password'.")

        return data
    





# flutter/serializers.py

from rest_framework import serializers
from app1.models import User  # Adjust the import based on your actual app name

class UserSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['userid', 'name', 'user_level', 'status', 'image', 'image_url']
    
    def get_image_url(self, obj):
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None






# flutter/serializers.py
from rest_framework import serializers
from app1.models import Attendance

class AttendanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attendance
        fields = ['employee', 'date', 'day', 'status', 'punch_in', 'punch_out', 'punch_in_location', 'punch_out_location']




from rest_framework import serializers
from app1.models import Attendance
from datetime import datetime
from rest_framework import serializers
from app1.models import Attendance
from datetime import datetime

class AttendanceMonthlyQuerySerializer(serializers.Serializer):
    userid = serializers.CharField()
    password = serializers.CharField()
    month = serializers.IntegerField(min_value=1, max_value=12)
    year = serializers.IntegerField(min_value=2020, max_value=2030)

class AttendanceDetailSerializer(serializers.ModelSerializer):
    punch_in_time = serializers.SerializerMethodField()
    punch_out_time = serializers.SerializerMethodField()
    date_formatted = serializers.SerializerMethodField()
    day_name = serializers.SerializerMethodField()
    working_hours = serializers.SerializerMethodField()
    
    class Meta:
        model = Attendance
        fields = [
            'id', 'date', 'date_formatted', 'day', 'day_name', 'status', 
            'punch_in', 'punch_out', 'punch_in_time', 'punch_out_time',
            'punch_in_location', 'punch_out_location', 'working_hours', 'verified', 'note'
        ]
    
    def get_punch_in_time(self, obj):
        if obj.punch_in:
            return obj.punch_in.strftime('%H:%M:%S')
        return None
    
    def get_punch_out_time(self, obj):
        if obj.punch_out:
            return obj.punch_out.strftime('%H:%M:%S')
        return None
    
    def get_date_formatted(self, obj):
        return obj.date.strftime('%d-%m-%Y')
    
    def get_day_name(self, obj):
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        return days[obj.day]
    
    def get_working_hours(self, obj):
        if obj.punch_in and obj.punch_out:
            duration = obj.punch_out - obj.punch_in
            total_seconds = int(duration.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            return f"{hours:02d}:{minutes:02d}"
        return None





from rest_framework import serializers
from app1.models import BreakTime

class BreakTimeSerializer(serializers.ModelSerializer):
    class Meta:
        model = BreakTime
        fields = ['employee', 'date', 'break_punch_in', 'break_punch_out', 'is_active']

class BreakStatusSerializer(serializers.Serializer):
    punch_in = serializers.DateTimeField(allow_null=True)
    punch_out = serializers.DateTimeField(allow_null=True)
    is_active = serializers.BooleanField()



# flutter/serializers.py

from rest_framework import serializers

class LeaveRequestListQuerySerializer(serializers.Serializer):
    userid   = serializers.CharField()
    password = serializers.CharField()
    status   = serializers.ChoiceField(
        choices=[('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected')],
        required=False
    )

class LeaveRequestDeleteSerializer(serializers.Serializer):
    userid     = serializers.CharField()
    password   = serializers.CharField()
    request_id = serializers.IntegerField()







from rest_framework import serializers
from app1.models import LateRequest, EarlyRequest, Employee, User

# ---- LATE ----
class LateRequestCreateSerializer(serializers.Serializer):
    userid     = serializers.CharField()
    password   = serializers.CharField()
    date       = serializers.DateField()
    delay_time = serializers.CharField()
    reason     = serializers.CharField()

class LateRequestListQuerySerializer(serializers.Serializer):
    userid   = serializers.CharField()
    password = serializers.CharField()
    status   = serializers.ChoiceField(
        choices=[('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected')],
        required=False
    )

class LateRequestDeleteSerializer(serializers.Serializer):
    userid     = serializers.CharField()
    password   = serializers.CharField()
    request_id = serializers.IntegerField()

# ---- EARLY ----
class EarlyRequestCreateSerializer(serializers.Serializer):
    userid     = serializers.CharField()
    password   = serializers.CharField()
    date       = serializers.DateField()
    early_time = serializers.TimeField()
    reason     = serializers.CharField()

class EarlyRequestListQuerySerializer(serializers.Serializer):
    userid   = serializers.CharField()
    password = serializers.CharField()
    status   = serializers.ChoiceField(
        choices=[('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected')],
        required=False
    )

class EarlyRequestDeleteSerializer(serializers.Serializer):
    userid     = serializers.CharField()
    password   = serializers.CharField()
    request_id = serializers.IntegerField()