from rest_framework import serializers

from django.contrib.contenttypes.models import ContentType
from django_resaas.core.base.serializers import BaseSerializer

class ModeloSerializer(BaseSerializer):
    class Meta:
        model = ContentType
        fields = "__all__"
