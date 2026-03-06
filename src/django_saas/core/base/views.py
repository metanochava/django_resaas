from django.utils import timezone
from django.shortcuts import get_object_or_404

from django.db.models import Q
from django.core.exceptions import FieldDoesNotExist

from rest_framework.viewsets import ModelViewSet
from rest_framework.exceptions import PermissionDenied

from django_saas.core.base.permissions import isPermited
from django_saas.core.utils.translate import Translate
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from django_saas.core.base.permissions import hasPermission
from django_saas.core.utils import all, ok, fail, warn  # noqa



from django_saas.core.base.registry import VIEW_REGISTRY

from django.db.models import Q, ForeignKey, OneToOneField
from django.core.exceptions import FieldDoesNotExist


def build_search_query(Model, search, depth=1):
    """
    depth = nível de profundidade (1 = FK direto)
    """
    q = Q()

    # campos locais
    candidates = [
        "nome", "name", "title", "descricao", "description",
        "username", "email", "codigo", "code"
    ]

    for field in candidates:
        try:
            Model._meta.get_field(field)
            q |= Q(**{f"{field}__icontains": search})
        except FieldDoesNotExist:
            continue

    # 🔥 relações (FK)
    if depth > 0:
        for f in Model._meta.get_fields():
            if isinstance(f, (ForeignKey, OneToOneField)):
                rel_model = f.related_model

                for field in candidates:
                    try:
                        rel_model._meta.get_field(field)
                        q |= Q(**{f"{f.name}__{field}__icontains": search})
                    except FieldDoesNotExist:
                        continue

    return q

def register_view(name=None, module=None):
    def decorator(cls):
        key = name or cls.__name__.lower().replace('APIView', '')+'s'
        module_name = module or cls.__module__.split(".")[0]  # rh, srm, etc

        VIEW_REGISTRY.setdefault(module_name, {})[key] = cls
        return cls
    return decorator


class BaseAPIView(ModelViewSet):
    """
    ViewSet base multi-tenant com controlo automático de permissões.
    """
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = "__all__"   # ou lista controlada

    # search_fields = ["id", "name"]
    ordering_fields = "__all__"

    permission_action_map = {
        'list': 'list',
        'retrieve': 'view',
        'create': 'add',
        'update': 'change',
        'partial_update': 'change',
        'destroy': 'delete',
        'restore': 'restore',
        'hard_delete': 'hard_delete',
    }


    def apply_dynamic_search(self, qs):
        search = (self.request.query_params.get("search") or "").strip()

        if not search:
            return qs

        Model = qs.model

        q = build_search_query(Model, search, depth=1)

        return qs.filter(q)
    
    def get_model(self):
        return self.get_queryset().model

    def get_method_permission(self):
        custom_map = getattr(self, 'method_permission', {})
        return {**self.permission_action_map, **custom_map}

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)

        action = self.action
        model = self.get_queryset().model

        perm_map = self.get_method_permission()
        perm_prefix = perm_map.get(action)

        if not perm_prefix:
            raise PermissionDenied(
                Translate.tdc(request, 'Permissão não definida para esta ação')
            )

        codename = f'{perm_prefix}_{model._meta.model_name}'


        if not isPermited(request=request, role=codename):
            raise PermissionDenied(
                Translate.tdc(request, 'Não autorizado ' +  codename)
            )


    def get_queryset(self):
        qs = super().get_queryset().filter(
            entidade_id=self.request.entidade_id,
            sucursal_id=self.request.sucursal_id,
        )

        status = (self.request.query_params.get("objects") or "").strip()
        
        # Se quiser ver apagados: ?objects=all
        if status == "all":
            Model = qs.model
            if hasattr(Model, "all_objects"):
                return Model.all_objects.filter(
                    entidade_id=self.request.entidade_id,
                    sucursal_id=self.request.sucursal_id,
                )

        # Se quiser so apagados: ?objects=deleted
        if status == "deleted":
            Model = qs.model
            if hasattr(Model, "deleted_objects"):
                return Model.deleted_objects.filter(
                    entidade_id=self.request.entidade_id,
                    sucursal_id=self.request.sucursal_id,
                )

        qs = self.apply_dynamic_search(qs)
        return qs

    def perform_create(self, serializer):
        serializer.save(
            entidade_id=self.request.entidade_id,
            sucursal_id=self.request.sucursal_id,
            created_by=self.request.user,
            updated_by=self.request.user
        )

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)


    def perform_destroy(self, instance):
        if hasattr(instance, "deleted_at"):
            instance.deleted_at = timezone.now()
        instance.delete(user = self.request.user)

    @action(detail=True, methods=["post"], url_path="restore")
    def restore(self, request, pk=None):
        Model = self.get_model()
        instance = get_object_or_404(Model.all_objects, pk=pk)

        if not instance:
            return fail(request, "Objeto não encontrado")

        model = instance._meta.model_name
        codename = f"restore_{model}"

        if not isPermited(request=request, role=codename):
            raise PermissionDenied("Não autorizado")

        instance.restore(user=request.user)  # 🔥 usa teu método do model

        return ok(request, "Restored com sucesso")


    @action(detail=True, methods=["delete"], url_path="hard_delete")
    def hard_delete(self, request, pk=None):
        Model = self.get_model()
        instance = get_object_or_404(Model.all_objects, pk=pk)

        model = instance._meta.model_name
        codename = f"hard_delete_{model}"

        if not isPermited(request=request, role=codename):
            raise PermissionDenied("Não autorizado")

        instance.hard_delete()

        return ok(
            request,
            "Apagado prara sempre com sucesso",
        )

    

    


