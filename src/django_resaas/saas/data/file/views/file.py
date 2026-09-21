# =========================
# Django
# =========================
from django_resaas.saas.core.base.access import ExplicitAccessMixin
from django.http import Http404


# =========================
# Django REST Framework
# =========================
from rest_framework import filters
from rest_framework import status
from rest_framework import viewsets
from django_resaas.saas.core.decorators.action import resaas_action
from rest_framework.response import Response


# =========================
# Local application
# =========================
from django_resaas.saas.core.services.disc_manager import DiskManegarService
from django_resaas.saas.core.utils.pagination import ResaasPagination
from django_resaas.saas.core.utils.translate import Translate

from django_resaas.saas.models.file import File

from django_resaas.saas.data.file.serializers.file import FileSerializer
from django_resaas.saas.data.file.serializers.file_gravar import (
    FileGravarSerializer,
)


class FileAPIView(ExplicitAccessMixin, viewsets.ModelViewSet):
    # PROTECTED: authenticated callers only (no public actions)

    search_fields = ["id", "file"]
    filter_backends = (filters.SearchFilter,)
    serializer_class = FileSerializer
    queryset = File.objects.all()
    lookup_field = "id"
    pagination_class = ResaasPagination

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
                        "FILE_NOT_FOUND",
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
                    "FILE_REMOVED_SUCCESS",
                )
            },
            status=status.HTTP_200_OK,
        )

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

        # Standard RESAAS tenant context (X-RESAAS-Context -> tenant
        # middleware -> request.entity_id), same as every other
        # tenant-scoped view - not a one-off "E" header nothing in the
        # frontend ever sent, which made every generic-form file upload
        # fail with ENTITY_NOT_PROVIDED.
        entity_id = getattr(request, "entity_id", None)

        if not entity_id:
            return Response(
                {
                    "alert_error": Translate.tdc(
                        request,
                        "ENTITY_NOT_PROVIDED",
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
                        "FILE_NOT_PROVIDED",
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not DiskManegarService.freeSpace(entity_id, uploaded_file):
            return Response(
                {
                    "alert_error": Translate.tdc(
                        request,
                        "INSUFFICIENT_SPACE",
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        data["size"] = uploaded_file.size

        # 'entity' is forced read-only by BaseSerializer.
        # DEFAULT_READ_ONLY_FIELDS (same as BranchAPIView.perform_create),
        # so data["entity"] alone is silently dropped by is_valid() -
        # pass it straight to save() instead.
        serializer = FileGravarSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save(entity_id=entity_id)

        return Response(
            FileSerializer(instance).data,
            status=status.HTTP_201_CREATED,
        )

    @resaas_action(detail=False, methods=["GET"])
    def por_entity(self, request):
        entity_id = request.query_params.get("entity")

        if not entity_id:
            return Response(
                {
                    "alert_error": Translate.tdc(
                        request,
                        "ENTITY_NOT_PROVIDED",
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        files = File.objects.filter(entity_id=entity_id)
        serializer = self.get_serializer(files, many=True)

        return Response(serializer.data, status=status.HTTP_200_OK)
