from rest_framework import serializers

from django_resaas.saas.models.translation import Translation

from django_resaas.saas.core.base.serializers import BaseSerializer
class TranslationSerializer(BaseSerializer):
    class Meta:
        model = Translation
        fields = "__all__"
