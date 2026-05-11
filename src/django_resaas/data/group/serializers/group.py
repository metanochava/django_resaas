from rest_framework import serializers

from django_resaas.models.group import Group
from django_resaas.core.base.serializers import BaseSerializer

class GroupSerializer(BaseSerializer):
    class Meta:
        model = Group
        fields = "__all__"
