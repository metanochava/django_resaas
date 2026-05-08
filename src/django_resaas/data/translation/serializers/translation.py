from rest_framework import serializers

from django_resaas.models.translation import Translation

from django_resaas.core.base.serializers import BaseSerializer
class TranslationSerializer(BaseSerializer):
    class Meta:
        model = Translation
        fields = "__all__"
