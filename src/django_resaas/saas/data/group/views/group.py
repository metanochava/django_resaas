# =========================
# Python standard library
# =========================
from django_resaas.saas.core.base.access import ExplicitAccessMixin
import json


# =========================
# Django
# =========================
from django_resaas.saas.models.group import Group
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.db.models import F
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
# Local application (absolute import)
# =========================
from django_resaas.saas.core.exceptions import ConflictError, ResaasAPIException
from django_resaas.saas.core.services import group_access_service
from django_resaas.saas.core.utils.pagination import ResaasPagination
from django_resaas.saas.data.group.serializers.group import GroupSerializer
from django_resaas.saas.models.branch import Branch
from django_resaas.saas.models.branch_group import BranchGroup
from django_resaas.saas.models.entity_group import EntityGroup


class GroupAPIView(ExplicitAccessMixin, viewsets.ModelViewSet):
    # PROTECTED: authenticated callers only (no public actions)

    """
    API de gestão de Groups (Profiles / Roles).

    Every action needs its permission in the current signed context (fail
    closed: an action missing from action_permissions is denied). What a
    caller sees and may change follows core/services/group_access_service.py:
    the current Entity's groups, changeable only when editable and not
    shared - or every group at platform level (change_entitytype).
    """

    serializer_class = GroupSerializer
    queryset = Group.objects.all()
    lookup_field = "id"
    filter_backends = (filters.SearchFilter,)
    search_fields = ["id", "name"]
    pagination_class = ResaasPagination

    action_permissions = {
        "list": "list_group",
        "retrieve": "view_group",
        "permissions": "view_group",
        "create": "add_group",
        "update": "change_group",
        "partial_update": "change_group",
        "destroy": "delete_group",
        "addPermission": "change_group",
        "removePermission": "change_group",
    }

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)

        codename = self.action_permissions.get(self.action)

        if not codename:
            raise ResaasAPIException(
                "Permission denied",
                code="permission_denied",
                status_code=status.HTTP_403_FORBIDDEN,
            )

        group_access_service.require_permission(request, codename)

    # -------------------------
    # Queryset
    # -------------------------

    def get_queryset(self):
        # Group NÃO tem codename
        return group_access_service.visible_groups(
            self.request, Group.objects.all()
        ).order_by("name")

    def get_changeable_object(self):
        group = self.get_object()
        group_access_service.check_group_changeable(self.request, group)
        return group

    # -------------------------
    # Create
    # -------------------------

    @transaction.atomic
    def perform_create(self, serializer):
        group = serializer.save()

        if group_access_service.is_platform(self.request):
            return

        # An Entity creates a group FOR ITSELF: linked to the current Entity
        # and its branches (as EntityAPIView.createGroup does) and editable,
        # so it stays inside this tenant.
        group.editable = True
        group.save(update_fields=["editable"])

        EntityGroup.objects.get_or_create(
            entity_id=self.request.entity_id, group=group, defaults={"state": "Active"}
        )
        BranchGroup.objects.bulk_create([
            BranchGroup(branch=branch, group=group, state="Active")
            for branch in Branch.objects.filter(entity_id=self.request.entity_id)
        ], ignore_conflicts=True)

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
        group = self.get_changeable_object()
        group.name = request.data.get("name", group.name)
        group.save()

        return Response(
            {
                "id": group.id,
                "name": group.name,
                "alert_success": f'%-{group.name}-% updated successfully',
            },
            status=status.HTTP_202_ACCEPTED,
        )

    # -------------------------
    # Destroy
    # -------------------------

    def destroy(self, request, id, *args, **kwargs):
        group = self.get_changeable_object()

        # never lock yourself out of the profile you are acting with
        if str(group.id) == str(request.group_id):
            raise ResaasAPIException(
                "You cannot delete the profile you are currently using.",
                code="cannot_delete_active_group",
            )

        name = group.name
        group.delete()

        return Response(
            {
                "alert_success": f"<b>{name}</b> deleted successfully"
            },
            status=status.HTTP_202_ACCEPTED,
        )

    # -------------------------
    # Actions
    # -------------------------

    @resaas_action(detail=True, methods=["POST"])
    def addPermission(self, request, id):
        group = self.get_changeable_object()

        codename = request.data.get("codename")
        name = request.data.get("name")

        if not codename or not name:
            return Response(
                {"alert_error": "codename and name are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        content_type, _ = ContentType.objects.get_or_create(
            app_label="custom",
            model="custom_permission",
        )

        # Authorization matches codenames only (check_permission), so a
        # "custom" permission reusing a real codename would grant that
        # capability - never allowed.
        if Permission.objects.filter(codename=codename).exclude(content_type=content_type).exists():
            raise ConflictError(
                "A permission with this codename already exists.",
                code="permission_codename_exists",
            )

        permission = Permission.objects.filter(
            content_type=content_type, codename=codename
        ).first()

        if permission is None:
            group_access_service.require_permission(request, "add_permission")
            permission = Permission.objects.create(
                content_type=content_type, codename=codename, name=name
            )
        else:
            # an existing custom permission: adding it is a grant
            group_access_service.check_delegation(request, [permission])

        group.permissions.add(permission)

        return Response(
            {
                "id": permission.id,
                "codename": permission.codename,
                "name": permission.name,
                "alert_success": f'Permission <b>{permission.name}</b> added successfully',
            },
            status=status.HTTP_201_CREATED,
        )

    
    


    @resaas_action(detail=True, methods=["POST"])
    def removePermission(self, request, id=None):
        group = self.get_changeable_object()

        codename = request.data.get("codename")

        if not codename:
            return Response(
                {"alert_error": "codename is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        permission = group.permissions.filter(codename=codename).first()

        if permission is None:
            return Response(
                {"alert_error": "Permission not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        group_access_service.check_delegation(request, [permission])

        # 🔥 remover permissão
        group.permissions.remove(permission)

        return Response(
            {
                "id": permission.id,
                "codename": permission.codename,
                "name": permission.name,
                "alert_success": f'Permission <b>{permission.name}</b> removed successfully',
            },
            status=status.HTTP_200_OK,
        )

    
    @resaas_action(
        detail=True,
        methods=['GET'],
    )
    def permissions(self, request, id, *args, **kwargs):
        per = []
        group = self.get_object()
        permissions = group.permissions.all()

        for permission in permissions:
            per.append({'id': permission.id, 'codename': permission.codename, 'name': permission.name})

        if True:
            return Response(per, status.HTTP_200_OK)
        return Response([], status.HTTP_400_BAD_REQUEST)
