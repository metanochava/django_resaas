
from rest_framework import serializers
from django_resaas.models.user import User



class SetNewPasswordSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'email', 'username', 'password', 'mobile')
        extra_kwargs = {
            'password': {'write_only': True}
        }