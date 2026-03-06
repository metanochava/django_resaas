# =========================
# Python standard library
# =========================
import importlib


# =========================
# Django
# =========================
from django.apps import apps
from django.core.cache import cache


# =========================
# Django REST Framework
# =========================
from rest_framework import filters
from rest_framework import status
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response


# =========================
# Local application
# =========================
from django_saas.models.idioma import Idioma
from django_saas.models.traducao import Traducao
from django_saas.data.idioma.serializers.idioma import IdiomaSerializer


class IdiomaAPIView(viewsets.ModelViewSet):
    search_fields = ["id", "nome"]
    filter_backends = (filters.SearchFilter,)
    serializer_class = IdiomaSerializer
    queryset = Idioma.objects.all()
    lookup_field = "id"
    pagination_class = None

    def get_queryset(self):
        return self.queryset.order_by("nome")

    def retrieve(self, request, *args, **kwargs):
        idioma = self.get_object()
        serializer = self.get_serializer(idioma)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(
            instance,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        response = serializer.data
        response["alert_success"] = (
            f"%-{response['nome']}-% foi actualizado com sucesso"
        )

        return Response(response, status=status.HTTP_200_OK)

    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        data["admin"] = request.user.id

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        response = serializer.data
        response["alert_success"] = (
            f"%-{response['nome']}-% foi criado com sucesso"
        )

        return Response(response, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["GET"])
    def traducaos(self, request, *args, **kwargs):
        CACHE_TIMEOUT = 1 * 20  # 1 hora

        idioma = self.get_object()
        lang_code = str(idioma.code).lower().replace("-", "")
        cache_key = f"traducao:{lang_code}"

        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached, status=status.HTTP_200_OK)

        traducoes = {}

        # Base de dados
        for item in Traducao.objects.filter(idioma_id=idioma.id):
            traducoes[item.chave] = item.traducao

        # Módulos lang/*.py
        for app in apps.get_app_configs():
            module_name = f"{app.name}.lang.{lang_code}"

            try:
                modulo = importlib.import_module(module_name)
            except ModuleNotFoundError:
                continue

            if hasattr(modulo, "key_value"):
                traducoes.update(modulo.key_value)

        cache.set(cache_key, traducoes, CACHE_TIMEOUT)

        return Response(traducoes, status=status.HTTP_200_OK)
