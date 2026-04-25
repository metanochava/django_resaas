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
from django_resaas.data.group.serializers.group import GroupSerializer


class GroupAPIView(viewsets.ModelViewSet):
    """
    API de gestão de Groups (Profiles / Roles).
    """

    serializer_class = GroupSerializer
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
        group = self.get_object()

        # Se ?permissions=1 → retorna permissões do group
        if request.query_params.get("permissions"):
            permissions = (
                group.permissions
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

        serializer = self.get_serializer(group)
        return Response(serializer.data, status=status.HTTP_200_OK)

    # -------------------------
    # Update
    # -------------------------

    def update(self, request, id, *args, **kwargs):
        group = self.get_object()
        group.name = request.data.get("name", group.name)
        group.save()

        return Response(
            {
                "id": group.id,
                "name": group.name,
                "alert_success": f'%-{group.name}-% foi actualizado com sucesso',
            },
            status=status.HTTP_202_ACCEPTED,
        )

    # -------------------------
    # Destroy
    # -------------------------

    def destroy(self, request, id, *args, **kwargs):
        group = self.get_object()
        nome = group.name
        group.delete()

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
        group = self.get_object()

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

        group.permissions.add(permission)

        return Response(
            {
                "id": permission.id,
                "codename": permission.codename,
                "name": permission.name,
                "alert_success": f'Permissão <b>{permission.name}</b> adicionada com sucesso',
            },
            status=status.HTTP_201_CREATED,
        )

    
    


    @action(detail=True, methods=["POST"])
    def removePermission(self, request, pk=None):
        group = self.get_object()

        codename = request.data.get("codename")

        if not codename:
            return Response(
                {"alert_error": "codename é obrigatório"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            permission = Permission.objects.get(codename=codename)
        except Permission.DoesNotExist:
            return Response(
                {"alert_error": "Permissão não encontrada"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # 🔥 remover permissão
        group.permissions.remove(permission)

        return Response(
            {
                "id": permission.id,
                "codename": permission.codename,
                "name": permission.name,
                "alert_success": f'Permissão <b>{permission.name}</b> removida com sucesso',
            },
            status=status.HTTP_200_OK,
        )

    
    @action(
        detail=True,
        methods=['GET'],
    )
    def permissions(self, request, id, *args, **kwargs):
        per = []
        group = Group.objects.get(id=id)
        permissions = group.permissions.all()

        for permission in permissions:
            per.append({'id': permission.id, 'codename': permission.codename, 'name': permission.name})

        if True:
            return Response(per, status.HTTP_200_OK)
        return Response([], status.HTTP_400_BAD_REQUEST)
