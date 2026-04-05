
from rest_framework import serializers


from django_resaas.models.documento import Documento


class DocumentoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Documento
        fields = "__all__"
