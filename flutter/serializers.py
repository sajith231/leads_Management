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
    class Meta:
        model = User
        fields = ['userid', 'name', 'user_level', 'status']






# flutter/serializers.py
from rest_framework import serializers
from app1.models import Attendance

class AttendanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attendance
        fields = ['employee', 'date', 'day', 'status', 'punch_in', 'punch_out', 'punch_in_location', 'punch_out_location']



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