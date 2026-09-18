
from django_resaas.saas.models.document import DocumentType
from django_resaas.saas.data.document_type.serializers.document_type import DocumentTypeSerializer
from django_resaas.saas.core.base.views import BaseAPIView, registerView


@registerView('documenttypes')
class DocumentTypeAPIView(BaseAPIView):
    serializer_class = DocumentTypeSerializer
    queryset = DocumentType.objects.all().order_by('-id')
    lookup_field = "id"
