# =========================
# Django
# =========================
from django.contrib.auth.models import Group, Permission
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
from django_resaas.models.tipo_entidade_modelo import TipoEntidadeModelo
from django_resaas.models.sucursal_user_group import SucursalUserGroup
from django_resaas.data.permission.serializers.permission import PermissionSerializer


class PermissionAPIView(viewsets.ModelViewSet):

    search_fields = ['id', 'name']
    filter_backends = (filters.SearchFilter,)
    serializer_class = PermissionSerializer
    lookup_field = "id"
    pagination_class = None

    # 🔥 QUERYSET BASE OTIMIZADO
    def get_queryset(self):
        tipo_id = getattr(self.request, "tipo_entidade_id", None)

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
                content_type__in=TipoEntidadeModelo.objects.filter(
                    tipo_entidade_id=tipo_id
                ).values_list('modelo', flat=True)  # 🔥 CORRETO
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
            'nome': permission.codename,
            'nomeseparado': permission.name,
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
            'nome': permission.codename,
            'nomeseparado': permission.name,
            'alert_info': f'Permissão <b>{permission.name}</b> removida'
        }, status=status.HTTP_200_OK)

    # ==========================================================
    # 🔥 USER ↔ GROUP
    # ==========================================================

    @action(detail=True, methods=['POST'])
    def addToUser(self, request, id):
        user_id = request.data.get('user')
        sucursal_id = request.data.get('sucursal')

        user = User.objects.filter(id=user_id).first()
        group = Group.objects.filter(id=id).first()

        if not user or not group:
            return Response(
                {'error': 'User or Group not found'},
                status=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():
            # 🔥 evita duplicação
            SucursalUserGroup.objects.get_or_create(
                sucursal_id=sucursal_id,
                user=user,
                group=group
            )

            user.groups.add(group)

        return Response({
            'alert_success': f'Perfil <b>{group.name}</b> adicionado'
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['POST'])
    def removeFromUser(self, request, id):
        user_id = request.data.get('user')
        sucursal_id = request.data.get('sucursal')

        user = User.objects.filter(id=user_id).first()
        group = Group.objects.filter(id=id).first()

        if not user or not group:
            return Response(
                {'error': 'User or Group not found'},
                status=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():
            SucursalUserGroup.objects.filter(
                sucursal_id=sucursal_id,
                user=user,
                group=group
            ).delete()

            user.groups.remove(group)

        return Response({
            'alert_success': f'Perfil <b>{group.name}</b> removido'
        }, status=status.HTTP_200_OK)