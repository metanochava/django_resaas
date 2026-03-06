from functools import wraps

from django.contrib.auth.models import Permission, Group

from rest_framework import status
from rest_framework.permissions import BasePermission
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from django_saas.core.utils.translate import Translate
from django_saas.models.sucursal_user_group import SucursalUserGroup
from django_saas.models.entidade_modulo import EntidadeModulo


class HasAppPermission(BasePermission):
    """
    Permission base do DRF integrada com o sistema multi-tenant.

    Usa o mesmo motor de permissões:
    - headers (ET, E, S, G, L)
    - grupos
    - permissões do Django
    - uma única query
    """

    message = 'Permission denied'

    def has_permission(self, request, view):
        """
        Verificação antes da execução da view.
        A view deve definir `permission_codename`.
        """

        # A view precisa declarar explicitamente a permissão
        codename = getattr(view, 'permission_codename', None)

        if not codename:
            # Segurança: se não declarou, não passa
            return False

        allowed = check_permission(
            request=request,
            role=codename
        )

        if not allowed:
            # mantém compatibilidade com DRF
            raise PermissionDenied(Translate.tdc(request,self.message))

        return True


def check_permission(request, role):
    role = role 

    if not all([
        request.user,
        request.user.is_authenticated,
        request.tipo_entidade_id,
        request.entidade_id,
        request.sucursal_id,
        request.group_id,
        request.lang_id,
    ]):
        return False

    return SucursalUserGroup.objects.filter(
        user=request.user,
        group_id=request.group_id,
        sucursal_id=request.sucursal_id,
        sucursal__entidade_id=request.entidade_id,
        sucursal__entidade__tipo_entidade_id=request.tipo_entidade_id,
        group__permissions__codename=role,
    ).exists()


def hasModulo(codigo):
    def decorator(func):
        @wraps(func)
        def wrapper(self, request, *args, **kwargs):
            entidade_id = request.entidade_id

            if not EntidadeModulo.objects.filter(
                entidade_id=entidade_id,
                modulo__codigo=codigo,
                estado=1
            ).exists():
                return Response(
                    {"detail": "Módulo não ativo"},
                    status=status.HTTP_403_FORBIDDEN
                )

            return func(self, request, *args, **kwargs)
        return wrapper
    return decorator


def hasPermission(role=None):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(self, request, *args, **kwargs):
            if check_permission(request, role):
                return view_func(self, request, *args, **kwargs)

            txt = Translate.tdc(request, 'Permission denied')
            return Response( {'alert_error': txt}, status=status.HTTP_403_FORBIDDEN )
        return wrapper
    return decorator

def isPermited( request=None, role=None):
    return check_permission(request, role)

