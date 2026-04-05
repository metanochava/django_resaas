
from rest_framework import viewsets
from django_resaas.models.documento import Documento
from django_resaas.data.documento.serializers.documento import DocumentoSerializer


class  DocumentoAPIView(viewsets.ModelViewSet):
    serializer_class = DocumentoSerializer
    queryset = Documento.objects.all()
    def get_queryset(self):
        return self.queryset.filter().order_by('-id')

   