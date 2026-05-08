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
from django_resaas.core.services.disc_manager import DiskManegarService
from django_resaas.core.utils.translate import Translate

from django_resaas.models.file import File

from django_resaas.data.file.serializers.file import FileSerializer
from django_resaas.data.file.serializers.file_gravar import (
    FileGravarSerializer,
)


class FileAPIView(viewsets.ModelViewSet):
    search_fields = ["id", "file"]
    filter_backends = (filters.SearchFilter,)
    serializer_class = FileSerializer
    queryset = File.objects.all()
    lookup_field = "id"

    def get_queryset(self):
        return self.queryset.order_by("-id")

    def retrieve(self, request, *args, **kwargs):
        try:
            file = self.get_object()
            serializer = self.get_serializer(file)
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
            DiskManegarService.recoverSpace(instance.entity_id, instance)
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
        file = self.get_object()
        serializer = self.get_serializer(
            file,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data, status=status.HTTP_200_OK)

    def create(self, request, *args, **kwargs):
        data = request.data.copy()

        entity_id = request.headers.get("E")

        if not entity_id:
            return Response(
                {
                    "alert_error": Translate.tdc(
                        request,
                        "ENTIDADE_NAO_INFORMADA",
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        uploaded_file = request.FILES.get("file")
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

        if not DiskManegarService.freeSpace(entity_id, uploaded_file):
            return Response(
                {
                    "alert_error": Translate.tdc(
                        request,
                        "ESPACO_INSUFICIENTE",
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        data["entity"] = entity_id
        data["size"] = uploaded_file.size

        serializer = FileGravarSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        return Response(
            FileSerializer(instance).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["GET"])
    def por_entity(self, request):
        entity_id = request.query_params.get("entity")

        if not entity_id:
            return Response(
                {
                    "alert_error": Translate.tdc(
                        request,
                        "ENTIDADE_NAO_INFORMADA",
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        files = File.objects.filter(entity_id=entity_id)
        serializer = self.get_serializer(files, many=True)

        return Response(serializer.data, status=status.HTTP_200_OK)
