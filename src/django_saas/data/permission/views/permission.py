# =========================
# Django
# =========================
from django.contrib.auth.models import Group
from django.contrib.auth.models import Permission
from django.db.models import F


# =========================
# Django REST Framework
# =========================
from rest_framework import filters
from rest_framework import status
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response


# =========================
# Local application (absolute imports)
# =========================
from django_saas.models.user import User
from django_saas.models.sucursal_user_group import SucursalUserGroup

from django_saas.data.permission.serializers.permission import PermissionSerializer



class  PermissionAPIView(viewsets.ModelViewSet):
 
    search_fields = ['id','name']
    filter_backends = (filters.SearchFilter,)
    serializer_class = PermissionSerializer
    queryset = Permission.objects.annotate(content_type_model= F('content_type__model'), content_type_app= F('content_type__app_label'))
    lookup_field = "id"
    paginator = None


    def get_queryset(self):
        return self.queryset.filter().order_by('codename')

    def list(self, request, *args, **kwargs):
        self._paginator = None
        queryset = self.filter_queryset(self.get_queryset().filter().order_by('content_type__app_label', 'content_type__model', 'codename'))
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @action(
        detail=True,
        methods=['POST'],
    )
    def addToGroup(self, request, id):
        grupo = Group.objects.get(id=request.data['id'])
        permission = Permission.objects.get(id=id)
        grupo.permissions.add(permission)
    
        per= {'id': permission.id, 'nome': permission.codename, 'nomeseparado':permission.name, 'alert_success': 'Permicao <b>' +permission.name + '</b> foi Adicionado consucesso'}
        return Response(per,status.HTTP_201_CREATED )


    @action(
        detail=True,
        methods=['POST'],
    )
    def removeFromGroup(self, request, id):
        # print(id, request.data) 
        grupo = Group.objects.get(id=request.data['id'])
        permission = Permission.objects.get(id=id)
        grupo.permissions.remove(permission)
    
        per= {'id': permission.id, 'nome': permission.codename, 'nomeseparado':permission.name, 'alert_info': 'Permicao <b>' +permission.name + '</b> foi removido consucesso'}
        return Response(per,status.HTTP_201_CREATED )


    @action(
        detail=True,
        methods=['POST'],
    )
    def addToUser(self, request, id):
        user = User.objects.get(id=request.data['user'])
        group = Group.objects.get(id=id)
        SucursalUserGroup.objects.create(sucursal_id=request.data['sucursal'], user=user, group=group)
        user.groups.add(group)
        per= {'alert_success': 'Perfil <b>' +group.name + '</b> foi Adicionado consucesso'}
        return Response(per,status.HTTP_201_CREATED )


    @action(
        detail=True,
        methods=['POST'],
    )
    def removeFromUser(self, request, id):
        user = User.objects.get(id=request.data['user'])
        group = Group.objects.get(id=id)
        SucursalUserGroup.objects.get(sucursal_id=request.data['sucursal'], user=user, group=group).delete()
        per= {'alert_success': 'Perfil <b>' +group.name + '</b> foi Removido consucesso'}
        return Response(per,status.HTTP_200_OK )


