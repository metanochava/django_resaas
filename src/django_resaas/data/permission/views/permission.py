# =========================
# Django
# =========================
from django_resaas.models.group import Group
from django.contrib.auth.models import Permission
from django.db.models import F
from django.db import transaction


# =========================
# DRF
# =========================
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response


# =========================
# Local
# =========================
from django_resaas.models.user import User
from django_resaas.models.entity_type_model import EntityTypeModel
from django_resaas.models.branch_user_group import BranchUserGroup
from django_resaas.data.permission.serializers.permission import PermissionSerializer


class PermissionAPIView(viewsets.ModelViewSet):

    search_fields = ['id', 'name']
    filter_backends = (filters.SearchFilter,)
    serializer_class = PermissionSerializer
    lookup_field = "id"
    pagination_class = None

    # 🔥 QUERYSET BASE OTIMIZADO
    def get_queryset(self):
        tipo_id = getattr(self.request, "entity_type_id", None)

        queryset = (
            Permission.objects
            .select_related('content_type')
            .annotate(
                content_type_model=F('content_type__model'),
                content_type_app=F('content_type__app_label')
            )
        )

        if tipo_id:
            queryset = queryset.filter(
                content_type__in=EntityTypeModel.objects.filter(
                    entity_type_id=tipo_id
                ).values_list('model', flat=True)  # 🔥 CORRETO
            )

        return queryset.order_by(
            'content_type__app_label',
            'content_type__model',
            'codename'
        )

    # 🔥 LIST LIMPO (SEM REPETIÇÃO)
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    # ==========================================================
    # 🔥 GROUP PERMISSIONS
    # ==========================================================

    @action(detail=True, methods=['POST'])
    def addToGroup(self, request, id):
        group_id = request.data.get('id')

        # 🔥 evita exceção + menos custo
        group = Group.objects.filter(id=group_id).first()
        permission = Permission.objects.filter(id=id).first()

        if not group or not permission:
            return Response(
                {'error': 'Group or Permission not found'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 🔥 evita duplicação silenciosa
        if not group.permissions.filter(id=permission.id).exists():
            group.permissions.add(permission)

        return Response({
            'id': permission.id,
            'name': permission.codename,
            'nameseparado': permission.name,
            'alert_success': f'Permissão <b>{permission.name}</b> adicionada'
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['POST'])
    def removeFromGroup(self, request, id):
        group_id = request.data.get('id')

        group = Group.objects.filter(id=group_id).first()
        permission = Permission.objects.filter(id=id).first()

        if not group or not permission:
            return Response(
                {'error': 'Group or Permission not found'},
                status=status.HTTP_400_BAD_REQUEST
            )

        group.permissions.remove(permission)

        return Response({
            'id': permission.id,
            'name': permission.codename,
            'nameseparado': permission.name,
            'alert_info': f'Permissão <b>{permission.name}</b> removida'
        }, status=status.HTTP_200_OK)

    # ==========================================================
    # 🔥 USER ↔ GROUP
    # ==========================================================

    @action(detail=True, methods=['POST'])
    def addToUser(self, request, id):
        user_id = request.data.get('user')
        branch_id = request.data.get('branch')

        user = User.objects.filter(id=user_id).first()
        group = Group.objects.filter(id=id).first()

        if not user or not group:
            return Response(
                {'error': 'User or Group not found'},
                status=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():
            # 🔥 evita duplicação
            BranchUserGroup.objects.get_or_create(
                branch_id=branch_id,
                user=user,
                group=group
            )

            # user.groups.add(group)

        return Response({
            'alert_success': f'Perfil <b>{group.name}</b> adicionado'
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['POST'])
    def removeFromUser(self, request, id):
        user_id = request.data.get('user')
        branch_id = request.data.get('branch')

        user = User.objects.filter(id=user_id).first()
        group = Group.objects.filter(id=id).first()

        if not user or not group:
            return Response(
                {'error': 'User or Group not found'},
                status=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():
            BranchUserGroup.objects.filter(
                branch_id=branch_id,
                user=user,
                group=group
            ).delete()

            # user.groups.remove(group)

        return Response({
            'alert_success': f'Perfil <b>{group.name}</b> removido'
        }, status=status.HTTP_200_OK)