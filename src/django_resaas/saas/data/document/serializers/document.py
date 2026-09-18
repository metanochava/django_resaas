
from rest_framework import serializers


from django_resaas.saas.models.document import Document
from django_resaas.saas.core.base.serializers import BaseSerializer
from django_resaas.saas.data.document_type.serializers.document_type import DocumentTypeSerializer


class DocumentSerializer(BaseSerializer):
    # Read-only nested representation, same "xxx_data" convention as
    # EmployeeSerializer.position_data/job_grade_data - `tipo` on its
    # own only serializes as the DocumentType's raw id, not enough to
    # show a document ("ID Card - 123456") anywhere in the frontend.
    tipo_data = DocumentTypeSerializer(source='tipo', read_only=True)

    class Meta:
        model = Document
        fields = "__all__"
