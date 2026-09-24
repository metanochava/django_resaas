from django_resaas.saas.core.base.access import ExplicitAccessMixin
from django.contrib.auth.models import Permission
from django.db import transaction
from django.db.models import F

from rest_framework import filters, status, viewsets
from django_resaas.saas.core.decorators.action import resaas_action
from rest_framework.response import Response

from django_resaas.saas.core.utils.pagination import ResaasPagination
from django_resaas.saas.models.group import Group
from django_resaas.saas.core.services import group_access_service
from django_resaas.saas.models.entity_type_model import EntityTypeModel
from django_resaas.saas.data.permission.serializers.permission import PermissionSerializer


class PermissionAPIView(ExplicitAccessMixin, viewsets.ModelViewSet):
    # PROTECTED: authenticated callers only (no public actions)

    queryset = Permission.objects.all()
    serializer_class = PermissionSerializer
    filter_backends = (filters.SearchFilter,)
    search_fields = ["id", "name"]
    lookup_field = "id"
    pagination_class = ResaasPagination

    # Reading the permission catalogue only needs authentication (group
    # screens list it); every WRITE needs the caller's effective permission
    # in the current signed context - fail closed.
    write_permissions = {
        "create": "add_permission",
        "update": "change_permission",
        "partial_update": "change_permission",
        "destroy": "delete_permission",
    }

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)

        codename = self.write_permissions.get(self.action)
        if codename:
            group_access_service.require_permission(request, codename)

    def get_queryset(self):
        queryset = Permission.objects.select_related("content_type").annotate(
            content_type_model=F("content_type__model"),
            content_type_app=F("content_type__app_label"),
        )

        # Restricting by EntityType is opt-in via an explicit query param,
        # mirroring ModelAPIView.get_queryset() - deriving it automatically
        # from request.entity_type_id broke the default permission list for
        # any EntityType without a fully curated EntityTypeModel allowlist
        # (e.g. "SaaS"), silently returning zero permissions.
        tipo_id = self.request.query_params.get("entitytype")

        if tipo_id:
            queryset = queryset.filter(
                content_type__in=EntityTypeModel.objects.filter(
                    entity_type_id=tipo_id
                ).values_list("model", flat=True)
            )

        return queryset.order_by(
            "content_type__app_label",
            "content_type__model",
            "codename",
        )

    @resaas_action(detail=False, methods=["POST"], url_path="setGroupPermissions")
    def setGroupPermissions(self, request):
        group_access_service.require_permission(request, "change_group")

        group_id = request.data.get("group") or request.data.get("id")
        permission_ids = request.data.get("permissions", [])

        if not group_id:
            return Response(
                {"error": "Group is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        group = Group.objects.filter(id=group_id).first()
        if not group:
            return Response(
                {"error": "Group not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        group_access_service.check_group_changeable(request, group)

        if not isinstance(permission_ids, list):
            return Response(
                {"error": "permissions must be a list"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        permission_ids = list(dict.fromkeys(permission_ids))
        permissions = Permission.objects.filter(id__in=permission_ids)
        existing_ids = set(permissions.values_list("id", flat=True))

        if len(existing_ids) != len(permission_ids):
            existing_str_ids = {str(value) for value in existing_ids}
            invalid_ids = [
                value
                for value in permission_ids
                if str(value) not in existing_str_ids
            ]
            return Response(
                {
                    "error": "One or more permissions were not found",
                    "invalid_permissions": invalid_ids,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            group = Group.objects.select_for_update().get(pk=group.pk)

            # No privilege escalation by delegation: every permission this
            # request ADDS or REMOVES must be one the caller holds. Unchanged
            # ones (the whole list is sent back) are not a grant.
            current = set(group.permissions.all())
            group_access_service.check_delegation(
                request, current.symmetric_difference(set(permissions))
            )

            group.permissions.set(permissions)

        saved_ids = list(group.permissions.values_list("id", flat=True))
        return Response(
            {
                "group": str(group.id),
                "permissions": saved_ids,
                "total": len(saved_ids),
                "alert_success": (
                    f"{len(saved_ids)} permissions updated successfully"
                ),
            },
            status=status.HTTP_200_OK,
        )

    # addToGroup / removeFromGroup / addToUser / removeFromUser were removed:
    # they changed any group's permissions and any user's profile in any
    # branch for any authenticated caller - no permission, no tenant check -
    # and had no consumer. Profiles of a user: UserAPIView addGroup /
    # removeGroup (users/{id}/addGroup/, permission- and tenant-checked).
