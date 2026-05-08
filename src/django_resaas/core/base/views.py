from django.utils import timezone
from django.shortcuts import get_object_or_404

from django.db.models import Q, ForeignKey, OneToOneField
from django.core.exceptions import FieldDoesNotExist

from rest_framework.viewsets import ModelViewSet
from rest_framework.exceptions import PermissionDenied
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status

from django_filters.rest_framework import DjangoFilterBackend

from django_resaas.core.base.permissions import isPermited
from django_resaas.core.utils.translate import Translate
from django_resaas.core.utils import ok, fail  # noqa
from django_resaas.core.base.registry import VIEW_REGISTRY
from django_resaas.models.entity_app import EntityApp


from .mixins.view.select import SelectMixin
from django_resaas.core.utils import build_select_data



# -----------------------------------
# 🔍 SEARCH BUILDER
# -----------------------------------

def build_search_query(Model, search, depth=1):
    q = Q()

    candidates = [
        "name", "name", "title", "descricao", "description",
        "username", "email", "codigo", "code"
    ]

    # campos locais
    for field in candidates:
        try:
            Model._meta.get_field(field)
            q |= Q(**{f"{field}__icontains": search})
        except FieldDoesNotExist:
            continue

    # relações (FK)
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


# -----------------------------------
# 🧩 VIEW REGISTRY
# -----------------------------------

def registerView(name=None, module=None):
    def decorator(cls):
        key = name or cls.__name__.lower().replace('apiview', '') + 's'
        module_name = module or cls.__module__.split(".")[0]
        # 🔥 registra no registry
        VIEW_REGISTRY.setdefault(module_name, {})[key] = cls
        # 🔥 AUTOMÁTICO: define module_name na class
        cls.module_name = module_name
        return cls
    return decorator


# -----------------------------------
# 🚀 BASE API VIEW
# -----------------------------------

class BaseAPIView(SelectMixin, ModelViewSet):


    """
    ViewSet base multi-tenant com controlo automático de permissões.
    """

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = "__all__"
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

    # -----------------------------------
    # 🔍 SEARCH
    # -----------------------------------

    def apply_dynamic_search(self, qs):
        search = (self.request.query_params.get("search") or "").strip()

        if not search:
            return qs

        Model = qs.model
        q = build_search_query(Model, search, depth=1)

        return qs.filter(q)

    # -----------------------------------
    # 🧠 MODEL
    # -----------------------------------

    def get_model(self):
        return self.queryset.model

    def get_method_permission(self):
        custom_map = getattr(self, 'method_permission', {})
        return {**self.permission_action_map, **custom_map}

    # -----------------------------------
    # 🔐 PERMISSIONS (COM CACHE)
    # -----------------------------------

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)

        # -----------------------------------
        # 🔐 CHECK MODULE
        # -----------------------------------
        module = getattr(self, "module_name", None)

        if module:
            ativo = EntityApp.objects.filter(
                entity__id=request.entity_id,
                app__name=module,
                estado=1
            ).exists()

            if not ativo:
                fail(request, "Módulo '{module}' não ativo")


        action = self.action
        model = self.get_model()

        perm_map = self.get_method_permission()
        perm_prefix = perm_map.get(action)

        if not perm_prefix:
            raise PermissionDenied(
                Translate.tdc(request, 'Permissão não definida para esta ação')
            )

        codename = f'{perm_prefix}_{model._meta.model_name}'

        # 🔥 cache de permissões
        if not hasattr(request, "_perm_cache"):
            request._perm_cache = {}

        if codename not in request._perm_cache:
            request._perm_cache[codename] = isPermited(
                request=request,
                role=codename
            )

        if not request._perm_cache[codename]:
            raise PermissionDenied(
                Translate.tdc(request, f'Não autorizado {codename}')
            )

    # -----------------------------------
    # 📊 QUERYSET (SAFE MULTI-TENANT)
    # -----------------------------------

    def get_queryset(self):
        qs = super().get_queryset()
        Model = qs.model

        # 🔥 aplica tenant só se existir no model
        if hasattr(Model, "entity_id"):
            qs = qs.filter(entity_id=self.request.entity_id)

        if hasattr(Model, "branch_id"):
            qs = qs.filter(branch_id=self.request.branch_id)

        objects_filter = (self.request.query_params.get("objects") or "").strip()

        # ver todos
        if objects_filter == "all" and hasattr(Model, "all_objects"):
            qs = Model.all_objects.all()

        # só apagados
        elif objects_filter == "deleted" and hasattr(Model, "deleted_objects"):
            qs = Model.deleted_objects.all()

        # reaplicar tenant após troca de manager
        if hasattr(Model, "entity_id"):
            qs = qs.filter(entity_id=self.request.entity_id)

        if hasattr(Model, "branch_id"):
            qs = qs.filter(branch_id=self.request.branch_id)

        qs = self.apply_dynamic_search(qs)

        return qs

    # -----------------------------------
    # ✍️ CREATE / UPDATE
    # -----------------------------------

    def perform_create(self, serializer):
        data = {
            "created_by": self.request.user,
            "updated_by": self.request.user
        }

        if hasattr(serializer.Meta.model, "entity_id"):
            data["entity_id"] = self.request.entity_id

        if hasattr(serializer.Meta.model, "branch_id"):
            data["branch_id"] = self.request.branch_id

        serializer.save(**data)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    # -----------------------------------
    # 🗑 DELETE (SOFT)
    # -----------------------------------

    def perform_destroy(self, instance):
        if hasattr(instance, "deleted_at"):
            instance.deleted_at = timezone.now()
        instance.delete(user=self.request.user)

    # -----------------------------------
    # ♻️ RESTORE
    # -----------------------------------

    @action(detail=True, methods=["post"], url_path="restore")
    def restore(self, request, pk=None):
        Model = self.get_model()
        instance = get_object_or_404(Model.all_objects, pk=pk)

        codename = f"restore_{Model._meta.model_name}"

        if not isPermited(request=request, role=codename):
            raise PermissionDenied("Não autorizado")

        instance.restore(user=request.user)

        return ok(request, "Restored com sucesso")

    # -----------------------------------
    # 💀 HARD DELETE
    # -----------------------------------

    @action(detail=True, methods=["delete"], url_path="hard_delete")
    def hard_delete(self, request, pk=None):
        Model = self.get_model()
        instance = get_object_or_404(Model.all_objects, pk=pk)

        codename = f"hard_delete_{Model._meta.model_name}"

        if not isPermited(request=request, role=codename):
            raise PermissionDenied("Não autorizado")

        instance.hard_delete()

        return ok(request, "Apagado para sempre com sucesso")

    
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        # 🔥 SELECT MODE (NÃO ALTERA NADA DO RESTO)
        if self.is_select_mode():
            page = self.paginate_queryset(queryset)

            if page is not None:
                data = build_select_data(page)
                return self.get_paginated_response(data)

            data = build_select_data(queryset)
            return Response(data)

        # 🔥 comportamento normal (inalterado)
        return super().list(request, *args, **kwargs)