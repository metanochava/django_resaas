
from rest_framework import viewsets
from django_resaas.models.documento import TipoDocumento
from django_resaas.data.tipo_documento.serializers.tipo_documento import TipoDocumentoSerializer


class  TipoDocumentoAPIView(viewsets.ModelViewSet):
    serializer_class = TipoDocumentoSerializer
    queryset = TipoDocumento.objects.all()
    def get_queryset(self):
        return self.queryset.filter().order_by('-id')

    def update(self, request, *args, **kwargs):
        partial = request.method == 'PATCH'

        instance = self.get_object()

        serializer = self.get_serializer(
            instance,
            data=request.data,
            partial=partial
        )

        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data)