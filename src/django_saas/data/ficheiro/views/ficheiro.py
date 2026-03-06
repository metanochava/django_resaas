# =========================
# Django
# =========================
from django.http import Http404


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
from django_saas.core.services.disc_manager import DiskManegarService
from django_saas.core.utils.translate import Translate

from django_saas.models.ficheiro import Ficheiro

from django_saas.data.ficheiro.serializers.ficheiro import FicheiroSerializer
from django_saas.data.ficheiro.serializers.ficheiro_gravar import (
    FicheiroGravarSerializer,
)


class FicheiroAPIView(viewsets.ModelViewSet):
    search_fields = ["id", "ficheiro"]
    filter_backends = (filters.SearchFilter,)
    serializer_class = FicheiroSerializer
    queryset = Ficheiro.objects.all()
    lookup_field = "id"

    def get_queryset(self):
        return self.queryset.order_by("-id")

    def retrieve(self, request, *args, **kwargs):
        try:
            ficheiro = self.get_object()
            serializer = self.get_serializer(ficheiro)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Http404:
            return Response(
                {
                    "alert_error": Translate.tdc(
                        request,
                        "FICHEIRO_NAO_ENCONTRADO",
                    )
                },
                status=status.HTTP_404_NOT_FOUND,
            )

    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            DiskManegarService.recoverSpace(instance.entidade_id, instance)
            self.perform_destroy(instance)
        except Http404:
            pass

        return Response(
            {
                "alert_success": Translate.tdc(
                    request,
                    "FICHEIRO_REMOVIDO_SUCESSO",
                )
            },
            status=status.HTTP_200_OK,
        )

    def list(self, request, *args, **kwargs):
        self._paginator = None
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def update(self, request, *args, **kwargs):
        ficheiro = self.get_object()
        serializer = self.get_serializer(
            ficheiro,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data, status=status.HTTP_200_OK)

    def create(self, request, *args, **kwargs):
        data = request.data.copy()

        entidade_id = request.headers.get("E")

        if not entidade_id:
            return Response(
                {
                    "alert_error": Translate.tdc(
                        request,
                        "ENTIDADE_NAO_INFORMADA",
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        uploaded_file = request.FILES.get("ficheiro")
        if not uploaded_file:
            return Response(
                {
                    "alert_error": Translate.tdc(
                        request,
                        "FICHEIRO_NAO_INFORMADO",
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not DiskManegarService.freeSpace(entidade_id, uploaded_file):
            return Response(
                {
                    "alert_error": Translate.tdc(
                        request,
                        "ESPACO_INSUFICIENTE",
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        data["entidade"] = entidade_id
        data["size"] = uploaded_file.size

        serializer = FicheiroGravarSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        return Response(
            FicheiroSerializer(instance).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["GET"])
    def por_entidade(self, request):
        entidade_id = request.query_params.get("entidade")

        if not entidade_id:
            return Response(
                {
                    "alert_error": Translate.tdc(
                        request,
                        "ENTIDADE_NAO_INFORMADA",
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        ficheiros = Ficheiro.objects.filter(entidade_id=entidade_id)
        serializer = self.get_serializer(ficheiros, many=True)

        return Response(serializer.data, status=status.HTTP_200_OK)
