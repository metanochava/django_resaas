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
from django_resaas.data.modelo.serializers.modelo import ModeloSerializer



class ModeloAPIView(viewsets.ModelViewSet):
    search_fields = ['id']
    filter_backends = (filters.SearchFilter,)
    serializer_class = ModeloSerializer
    queryset = ContentType.objects.all()
    lookup_field = "id"

    def get_queryset(self):
        qs = self.queryset

        tipo_id = self.request.query_params.get("tipoentidade")

        # 🔥 SE NÃO VIER PARAM → comportamento normal
        if not tipo_id:
            return qs.order_by('app_label', 'model')

        # 🔥 SE VIER → aplicar filtro
        modulos = TipoEntidadeModulo.objects.filter(
            tipo_entidade_id=tipo_id
        ).select_related('modulo')

        nomes_modulos = [m.modulo.nome for m in modulos]

        # 🔥 se não tiver módulos → retorna vazio (segurança)
        if not nomes_modulos:
            return qs.none()

        qs = qs.filter(app_label__in=nomes_modulos)

        return qs.order_by('app_label', 'model')

    def list(self, request, *args, **kwargs):
        self._paginator = None
        serializer = self.get_serializer(self.get_queryset(), many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)