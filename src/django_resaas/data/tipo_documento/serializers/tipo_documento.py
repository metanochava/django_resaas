
from rest_framework import serializers
from django_resaas.core.base.serializers import BaseSerializer
from django_resaas.models.documento import TipoDocumento


class TipoDocumentoSerializer(BaseSerializer):
    class Meta:
        model = TipoDocumento
        fields = "__all__"
