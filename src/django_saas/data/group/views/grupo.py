# =========================
# Python standard library
# =========================
import json


# =========================
# Django
# =========================
from django.contrib.auth.models import Group
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.db.models import F
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
# Local application (absolute import)
# =========================
from django_saas.data.group.serializers.grupo import GrupoSerializer


class GrupoAPIView(viewsets.ModelViewSet):
    """
    API de gestão de Grupos (Profiles / Roles).
    """

    serializer_class = GrupoSerializer
    queryset = Group.objects.all()
    lookup_field = "id"
    filter_backends = (filters.SearchFilter,)
    search_fields = ["id", "name"]
    pagination_class = None

    # -------------------------
    # Queryset
    # -------------------------

    def get_queryset(self):
        # Group NÃO tem codename
        return self.queryset.order_by("name")

    # -------------------------
    # Retrieve
    # -------------------------

    def retrieve(self, request, id, *args, **kwargs):
        grupo = self.get_object()

        # Se ?permissions=1 → retorna permissões do grupo
        if request.query_params.get("permissions"):
            permissions = (
                grupo.permissions
                .annotate(
                    content_type_model=F("content_type__model"),
                    content_type_app=F("content_type__app_label"),
                )
                .order_by("content_type_app", "content_type_model", "codename")
            )

            return Response(
                [
                    {
                        "id": p.id,
                        "name": p.name,
                        "codename": p.codename,
                        "content_type": p.content_type.id,
                        "content_type_model": p.content_type_model,
                        "content_type_app": p.content_type_app,
                    }
                    for p in permissions
                ],
                status=status.HTTP_200_OK,
            )

        serializer = self.get_serializer(grupo)
        return Response(serializer.data, status=status.HTTP_200_OK)

    # -------------------------
    # Update
    # -------------------------

    def update(self, request, id, *args, **kwargs):
        grupo = self.get_object()
        grupo.name = request.data.get("name", grupo.name)
        grupo.save()

        return Response(
            {
                "id": grupo.id,
                "name": grupo.name,
                "alert_success": f'%-{grupo.name}-% foi actualizado com sucesso',
            },
            status=status.HTTP_202_ACCEPTED,
        )

    # -------------------------
    # Destroy
    # -------------------------

    def destroy(self, request, id, *args, **kwargs):
        grupo = self.get_object()
        nome = grupo.name
        grupo.delete()

        return Response(
            {
                "alert_success": f"<b>{nome}</b> foi apagado com sucesso"
            },
            status=status.HTTP_202_ACCEPTED,
        )

    # -------------------------
    # Actions
    # -------------------------

    @action(detail=True, methods=["POST"])
    def addPermission(self, request, id):
        grupo = self.get_object()

        codename = request.data.get("codename")
        name = request.data.get("name")

        if not codename or not name:
            return Response(
                {"alert_error": "codename e name são obrigatórios"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        content_type, _ = ContentType.objects.get_or_create(
            app_label="custom",
            model="custom_permission",
        )

        permission, _ = Permission.objects.get_or_create(
            content_type=content_type,
            codename=codename,
            defaults={"name": name},
        )

        grupo.permissions.add(permission)

        return Response(
            {
                "id": permission.id,
                "codename": permission.codename,
                "name": permission.name,
                "alert_success": f'Permissão <b>{permission.name}</b> adicionada com sucesso',
            },
            status=status.HTTP_201_CREATED,
        )

    
