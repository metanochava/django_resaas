from rest_framework import serializers

from django_resaas.models.traducao import Traducao

from django_resaas.core.base.serializers import BaseSerializer
class TraducaoSerializer(BaseSerializer):
    class Meta:
        model = Traducao
        fields = "__all__"
