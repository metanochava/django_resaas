
from rest_framework import serializers


from django_resaas.engine.models.document import Document
from django_resaas.engine.core.base.serializers import BaseSerializer

class DocumentSerializer(BaseSerializer):
    class Meta:
        model = Document
        fields = "__all__"
