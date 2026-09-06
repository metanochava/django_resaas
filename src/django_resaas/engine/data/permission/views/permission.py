from django.contrib.auth.models import Permission
from django.db import transaction
from django.db.models import F

from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from django_resaas.engine.models.group import Group
from django_resaas.engine.models.user import User
from django_resaas.engine.models.entity_type_model import EntityTypeModel
from django_resaas.engine.models.branch_user_group import BranchUserGroup
from django_resaas.engine.data.permission.serializers.permission import PermissionSerializer


class PermissionAPIView(viewsets.ModelViewSet):
    queryset = Permission.objects.all()
    serializer_class = PermissionSerializer
    filter_backends = (filters.SearchFilter,)
    search_fields = ["id", "name"]
    lookup_field = "id"
    pagination_class = None

    def get_queryset(self):
        tipo_id = getattr(self.request, "entity_type_id", None)
        queryset = Permission.objects.select_related("content_type").annotate(
            content_type_model=F("content_type__model"),
            content_type_app=F("content_type__app_label"),
        )

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

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        return Response(
            self.get_serializer(queryset, many=True).data,
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["POST"], url_path="setGroupPermissions")
    def setGroupPermissions(self, request):
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

    @action(detail=True, methods=["POST"])
    def addToGroup(self, request, id=None):
        group = Group.objects.filter(id=request.data.get("id")).first()
        permission = Permission.objects.filter(id=id).first()

        if not group or not permission:
            return Response(
                {"error": "Group or Permission not found"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        group.permissions.add(permission)
        return Response(
            {
                "id": permission.id,
                "name": permission.codename,
                "nameseparado": permission.name,
                "alert_success": (
                    f"Permission <b>{permission.name}</b> added"
                ),
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["POST"])
    def removeFromGroup(self, request, id=None):
        group = Group.objects.filter(id=request.data.get("id")).first()
        permission = Permission.objects.filter(id=id).first()

        if not group or not permission:
            return Response(
                {"error": "Group or Permission not found"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        group.permissions.remove(permission)
        return Response(
            {
                "id": permission.id,
                "name": permission.codename,
                "nameseparado": permission.name,
                "alert_info": (
                    f"Permission <b>{permission.name}</b> removed"
                ),
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["POST"])
    def addToUser(self, request, id=None):
        user = User.objects.filter(id=request.data.get("user")).first()
        group = Group.objects.filter(id=id).first()

        if not user or not group:
            return Response(
                {"error": "User or Group not found"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            _, created = BranchUserGroup.objects.get_or_create(
                branch_id=request.data.get("branch"),
                user=user,
                group=group,
            )

        return Response(
            {"alert_success": f"Profile <b>{group.name}</b> added"},
            status=(
                status.HTTP_201_CREATED
                if created
                else status.HTTP_200_OK
            ),
        )

    @action(detail=True, methods=["POST"])
    def removeFromUser(self, request, id=None):
        user = User.objects.filter(id=request.data.get("user")).first()
        group = Group.objects.filter(id=id).first()

        if not user or not group:
            return Response(
                {"error": "User or Group not found"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            BranchUserGroup.objects.filter(
                branch_id=request.data.get("branch"),
                user=user,
                group=group,
            ).delete()

        return Response(
            {"alert_success": f"Profile <b>{group.name}</b> removed"},
            status=status.HTTP_200_OK,
        )