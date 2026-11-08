from rest_framework import serializers

from django.contrib.auth.models import Permission
from django_resaas.saas.core.base.serializers import BaseSerializer

class PermissionSerializer(BaseSerializer):
    # the module (Django app label) of the permission: the Permissions modal
    # uses it to show / hide that module in the profile's menu
    app_label = serializers.CharField(source="content_type.app_label", read_only=True)

    class Meta:
        model = Permission
        fields = ['id', 'name', 'codename', 'content_type', 'app_label']
