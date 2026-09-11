
from rest_framework import serializers
from django_resaas.saas.core.base.serializers import BaseSerializer
from django_resaas.saas.models.document import DocumentType


class DocumentTypeSerializer(BaseSerializer):
    class Meta:
        model = DocumentType
        fields = "__all__"
