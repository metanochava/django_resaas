
from rest_framework import serializers

from django_resaas.core.base.serializers import BaseSerializer
from django_resaas.models.user import User


class UserSerializer(BaseSerializer):
    
    class Meta:
        model = User
        fields = ['id', 'email', 'username', 'perfil', 'mobile']