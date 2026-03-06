# =========================
# Django
# =========================
from django.contrib.contenttypes.models import ContentType


# =========================
# Django REST Framework
# =========================
from rest_framework import filters
from rest_framework import status
from rest_framework import viewsets
from rest_framework.response import Response


# =========================
# Local application (absolute imports)
# =========================
from django_saas.data.modelo.serializers.modelo import ModeloSerializer



class ModeloAPIView(viewsets.ModelViewSet):
    search_fields = ['id']
    filter_backends = (filters.SearchFilter,)
    serializer_class = ModeloSerializer
    queryset = ContentType.objects.all()
    lookup_field = "id"

    def get_queryset(self):
        return self.queryset.order_by('app_label', 'model')

    def list(self, request, *args, **kwargs):
        self._paginator = None
        serializer = self.get_serializer(self.get_queryset(), many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)