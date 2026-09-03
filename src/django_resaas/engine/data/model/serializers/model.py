from rest_framework import serializers

from django.contrib.contenttypes.models import ContentType
from django_resaas.engine.core.base.serializers import BaseSerializer

class ModelSerializer(BaseSerializer):
    class Meta:
        model = ContentType
        fields = "__all__"
