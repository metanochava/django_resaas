
from rest_framework import serializers

from django_resaas.engine.core.base.serializers import BaseSerializer
from django_resaas.engine.models.user import User


class UserSerializer(BaseSerializer):
    
    class Meta:
        model = User
        fields = ['id', 'email', 'username', 'profile', 'mobile']