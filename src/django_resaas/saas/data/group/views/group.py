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
from django.http import Http404, HttpResponse



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
from django_resaas.saas.core.services import group_access_service, group_permissions_io_service
from django_resaas.saas.core.utils.translate import Translate
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
        # export / import of the group's permissions
        # (core/services/group_permissions_io_service.py)
        "permissions_csv": "view_group",
        "permissions_pdf": "view_group",
        "import_permissions": "change_group",
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

    
    # -------------------------
    # Export / import of the permissions
    # -------------------------

    @resaas_action(detail=True, methods=["GET"], label="Download permissions (CSV)", icon="download",
                   permission="view_group")
    def permissions_csv(self, request, id, *args, **kwargs):
        group = self.get_object()
        response = HttpResponse(
            group_permissions_io_service.to_csv(group), content_type="text/csv; charset=utf-8"
        )
        response["Content-Disposition"] = f'attachment; filename="{_safe_filename(group.name)}-permissions.csv"'
        return response

    @resaas_action(detail=True, methods=["GET"], label="Download permissions (PDF)", icon="picture_as_pdf",
                   permission="view_group")
    def permissions_pdf(self, request, id, *args, **kwargs):
        """Reuses the generic list PDF (django_resaas/pdf/list.html) and the
        entity branding helpers of BaseAPIView."""
        group = self.get_object()
        rows = group_permissions_io_service.permission_rows(group)
        title = f"{Translate.tdc(request, 'Permissions')} - {group.name}"

        return group_permissions_io_service.render_list_pdf(
            self, request,
            title=title,
            section_title=f"{len(rows)} {Translate.tdc(request, 'permissions')}",
            fields=[("app", "App"), ("model", "Model"), ("codename", "Codename"), ("name", "Name")],
            rows=[[r["app"], r["model"], r["codename"], r["name"]] for r in rows],
        )

    @resaas_action(detail=True, methods=["POST"], label="Import permissions (CSV)", icon="upload",
                   permission="change_group")
    def import_permissions(self, request, id, *args, **kwargs):
        """multipart: file=<csv>, mode=add|replace (default add). All or
        nothing; the rules of setGroupPermissions apply."""
        summary = group_permissions_io_service.import_csv(
            request, self.get_object(), request.FILES.get("file"), request.data.get("mode") or "add",
        )
        return Response(summary, status=status.HTTP_200_OK)

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


def _safe_filename(name):
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in str(name))[:60] or "group"
