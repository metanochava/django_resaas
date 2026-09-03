
from rest_framework import serializers
from django_resaas.engine.core.base.serializers import BaseSerializer
from django_resaas.engine.models.document import DocumentType


class DocumentTypeSerializer(BaseSerializer):
    class Meta:
        model = DocumentType
        fields = "__all__"
