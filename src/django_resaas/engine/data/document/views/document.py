
from rest_framework import viewsets
from django_resaas.engine.models.document import Document
from django_resaas.engine.data.document.serializers.document import DocumentSerializer


class  DocumentAPIView(viewsets.ModelViewSet):
    serializer_class = DocumentSerializer
    queryset = Document.objects.all()
    def get_queryset(self):
        return self.queryset.filter().order_by('-id')

   