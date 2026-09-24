from rest_framework import serializers

from django_resaas.saas.models.group import Group
from django_resaas.saas.core.base.serializers import BaseSerializer

class GroupSerializer(BaseSerializer):
    class Meta:
        model = Group
        fields = ['id', 'name', 'editable']
        # server-controlled: it decides whether an Entity may change the
        # group's permissions (PermissionAPIView._check_group_scope), so a
        # client can never set it
        read_only_fields = ['editable']
