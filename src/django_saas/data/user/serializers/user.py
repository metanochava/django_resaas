
from rest_framework import serializers

from django_saas.core.base.serializers import BaseSerializer
from django_saas.models.user import User


class UserSerializer(BaseSerializer):
    
    class Meta:
        model = User
        fields = ['id', 'email', 'username', 'perfil', 'mobile']