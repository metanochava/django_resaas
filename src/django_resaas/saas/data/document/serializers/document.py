
from rest_framework import serializers


from django_resaas.saas.models.document import Document
from django_resaas.saas.core.base.serializers import BaseSerializer

class DocumentSerializer(BaseSerializer):
    class Meta:
        model = Document
        fields = "__all__"
