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
from django_resaas.engine.models.language import Language
from django_resaas.engine.models.translation import Translation
from django_resaas.engine.data.language.serializers.language import LanguageSerializer

from django_resaas.engine.core.base.views import BaseAPIView

class LanguageAPIView(viewsets.ModelViewSet):
    search_fields = ["id", "name"]
    filter_backends = (filters.SearchFilter,)
    serializer_class = LanguageSerializer
    queryset = Language.objects.all()
    lookup_field = "id"
    pagination_class = None

    def get_queryset(self):
        return self.queryset.order_by("name")

    def retrieve(self, request, *args, **kwargs):
        language = self.get_object()
        serializer = self.get_serializer(language)
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
            f"%-{response['name']}-% updated successfully"
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
            f"%-{response['name']}-% created successfully"
        )

        return Response(response, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["GET"])
    def translations(self, request, *args, **kwargs):
        CACHE_TIMEOUT = 1 * 20  # 1 hora

        language = self.get_object()
        lang_code = str(language.code).lower().replace("-", "")
        cache_key = f"translation:{lang_code}"

        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached, status=status.HTTP_200_OK)

        traducoes = {}

        # Base de dados
        for item in Translation.objects.filter(language_id=language.id):
            traducoes[item.chave] = item.translation

        # Módulos lang/*.py
        for app in apps.get_app_configs():
            module_name = f"{app.name}.lang.{lang_code}"

            try:
                app = importlib.import_module(module_name)
            except ModuleNotFoundError:
                continue

            if hasattr(app, "key_value"):
                traducoes.update(app.key_value)

        cache.set(cache_key, traducoes, CACHE_TIMEOUT)

        return Response(traducoes, status=status.HTTP_200_OK)
