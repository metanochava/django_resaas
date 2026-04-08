
from rest_framework import serializers


from django_resaas.models.documento import Documento
from django_resaas.core.base.serializers import BaseSerializer

class DocumentoSerializer(BaseSerializer):
    class Meta:
        model = Documento
        fields = "__all__"
