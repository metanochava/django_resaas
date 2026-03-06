
from rest_framework import serializers
from django_saas.models.user import User



class ResetPasswordEmailRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'email', 'username', 'password', 'mobile')
        extra_kwargs = {
            'password': {'write_only': True}
        }