from functools import wraps

from django.contrib.auth.models import Permission

from rest_framework import status
from rest_framework.permissions import BasePermission
from rest_framework.exceptions import PermissionDenied
from django_resaas.engine.core.utils.api_response import ok, fail, warn

from django_resaas.engine.core.utils.translate import Translate
from django_resaas.engine.models.branch_user_group import BranchUserGroup
from django_resaas.engine.models.entity_app import EntityApp


class HasAppPermission(BasePermission):
    """
    Permission base do DRF integrada com o sistema multi-tenant.

    Usa o mesmo motor de permissões:
    - contexto de tenant (X-RESAAS-Context, com entity_type/entity/branch/
      group resolvidos a partir do token assinado - ver TenantContextMiddleware)
    - header de idioma (L)
    - groups
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
        request.entity_type_id,
        request.entity_id,
        request.branch_id,
        request.group_id,
        request.lang_id,
    ]):
        return False

    return BranchUserGroup.objects.filter(
        user=request.user,
        group_id=request.group_id,
        branch_id=request.branch_id,
        branch__entity_id=request.entity_id,
        branch__entity__entity_type_id=request.entity_type_id,
        group__permissions__codename=role,
    ).exists()


def hasApp(codigo):
    def decorator(func):
        @wraps(func)
        def wrapper(self, request, *args, **kwargs):
            entity_id = request.entity_id

            ativo = EntityApp.objects.filter(
                entity_id=entity_id,
                app__codigo=codigo,
                state= 1
            ).exists()

            if not ativo:
                return fail(request,
                   "Module not active",
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

            return fail( request, 'Permission denied', status=status.HTTP_403_FORBIDDEN )
        return wrapper
    return decorator

def isPermited( request=None, role=None):
    return check_permission(request, role)

