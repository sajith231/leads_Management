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