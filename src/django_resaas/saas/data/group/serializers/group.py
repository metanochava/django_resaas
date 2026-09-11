from rest_framework import serializers

from django_resaas.saas.models.group import Group
from django_resaas.saas.core.base.serializers import BaseSerializer

class GroupSerializer(BaseSerializer):
    class Meta:
        model = Group
        fields = "__all__"
