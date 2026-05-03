from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework import filters

from django_resaas.data.modulo.serializers.modulo import ModuloSerializer
from django_resaas.models.modulo import Modulo


class ModuloAPIView(viewsets.ModelViewSet):
    search_fields = ['nome']
    filter_backends = (filters.SearchFilter,)
    serializer_class = ModuloSerializer
    queryset = Modulo.objects.all()
    lookup_field = "id"

    def get_queryset(self):
        return self.queryset.order_by('nome')

    def list(self, request, *args, **kwargs):
        self._paginator = None
        serializer = self.get_serializer(self.get_queryset(), many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)