from rest_framework import serializers

from django_resaas.models.language import Language
from django_resaas.core.base.serializers import BaseSerializer


class LanguageSerializer(BaseSerializer):
    class Meta:
        model = Language
        fields = "__all__"
