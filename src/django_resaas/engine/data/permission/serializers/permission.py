from rest_framework import serializers

from django.contrib.auth.models import Permission
from django_resaas.engine.core.base.serializers import BaseSerializer

class PermissionSerializer(BaseSerializer):
    class Meta:
        model = Permission
        fields = ['id', 'name', 'codename', 'content_type']
