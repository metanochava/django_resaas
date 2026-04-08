from rest_framework import serializers

from django.contrib.auth.models import Group
from django_resaas.core.base.serializers import BaseSerializer

class GrupoSerializer(BaseSerializer):
    class Meta:
        model = Group
        fields = "__all__"
