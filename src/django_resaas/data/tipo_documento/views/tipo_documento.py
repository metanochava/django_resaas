
from rest_framework import viewsets
from django_resaas.models.documento import TipoDocumento
from django_resaas.data.tipo_documento.serializers.tipo_documento import TipoDocumentoSerializer


class  TipoDocumentoAPIView(viewsets.ModelViewSet):
    serializer_class = TipoDocumentoSerializer
    queryset = TipoDocumento.objects.all()
    def get_queryset(self):
        return self.queryset.filter().order_by('-id')

   