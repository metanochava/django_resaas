
from django_resaas.saas.models.document import Document
from django_resaas.saas.data.document.serializers.document import DocumentSerializer
from django_resaas.saas.core.base.views import BaseAPIView, registerView


@registerView('documents')
class DocumentAPIView(BaseAPIView):
    serializer_class = DocumentSerializer
    queryset = Document.objects.all().order_by('-id')
    lookup_field = "id"
