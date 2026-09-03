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

from django_resaas.engine.models.entity_type_app import EntityTypeApp


# =========================
# Local application (absolute imports)
# =========================
from django_resaas.engine.data.model.serializers.model import ModelSerializer



class ModelAPIView(viewsets.ModelViewSet):
    search_fields = ['id']
    filter_backends = (filters.SearchFilter,)
    serializer_class = ModelSerializer
    queryset = ContentType.objects.all()
    lookup_field = "id"

    def get_queryset(self):
        qs = self.queryset

        tipo_id = self.request.query_params.get("entitytype")

        # 🔥 SE NÃO VIER PARAM → comportamento normal
        if not tipo_id:
            return qs.order_by('app_label', 'model')

        # 🔥 SE VIER → aplicar filtro
        apps = EntityTypeApp.objects.filter(
            entity_type_id=tipo_id
        ).select_related('app')

        names_apps = [m.app.name for m in apps]

        # 🔥 se não tiver módulos → retorna vazio (segurança)
        if not names_apps:
            return qs.none()

        qs = qs.filter(app_label__in=names_apps)

        return qs.order_by('app_label', 'model')

    def list(self, request, *args, **kwargs):
        self._paginator = None
        serializer = self.get_serializer(self.get_queryset(), many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)