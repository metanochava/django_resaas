
from rest_framework import serializers


from django_resaas.models.document import Document
from django_resaas.core.base.serializers import BaseSerializer

class DocumentSerializer(BaseSerializer):
    class Meta:
        model = Document
        fields = "__all__"
