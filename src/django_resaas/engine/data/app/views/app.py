from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework import filters

from django_resaas.engine.data.app.serializers.app import AppSerializer
from django_resaas.engine.models.app import App


class AppAPIView(viewsets.ModelViewSet):
    search_fields = ['name']
    filter_backends = (filters.SearchFilter,)
    serializer_class = AppSerializer
    queryset = App.objects.all()
    lookup_field = "id"

    def get_queryset(self):
        return self.queryset.order_by('name')

    def list(self, request, *args, **kwargs):
        self._paginator = None
        serializer = self.get_serializer(self.get_queryset(), many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)