from django_resaas.core.base.serializers import BaseSerializer
from django_resaas.models.entity import Entity
from rest_framework import serializers



class EntitySerializer(BaseSerializer):
    permanent_fields_files = ['logo']
    login_background = serializers.ReadOnlyField()
    login_config = serializers.ReadOnlyField()
    class Meta:
        model = Entity
        fields = "__all__"
