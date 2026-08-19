from django.utils import timezone
from django.shortcuts import get_object_or_404

from django.db.models import Q, ForeignKey, OneToOneField
from django.db.models import CharField, TextField, EmailField
from django.core.exceptions import FieldDoesNotExist

from rest_framework.viewsets import ModelViewSet
from rest_framework.exceptions import PermissionDenied
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status

from django_resaas.core.base.permissions import isPermited
from django_resaas.core.utils.translate import Translate
from django_resaas.core.utils import ok, fail  # noqa
from django_resaas.core.base.registry import VIEW_REGISTRY
from django_resaas.models.entity_app import EntityApp


from .mixins.view.select import SelectMixin
from django_resaas.core.utils import build_select_data
from django.db import models



from django_filters.rest_framework import (
    DjangoFilterBackend,
    FilterSet,
)


# ============================================================
# VERIFICAR SE UM CAMPO DE PESQUISA É VÁLIDO
# ============================================================

def is_valid_search_field(Model, field_path):

    parts = field_path.split("__")

    current_model = Model

    for index, part in enumerate(parts):

        try:
            field = current_model._meta.get_field(part)

        except FieldDoesNotExist:
            return False

        # último campo
        if index == len(parts) - 1:

            return isinstance(
                field,
                (
                    CharField,
                    TextField,
                    EmailField,
                )
            )

        # ainda existem campos depois deste
        # portanto este precisa ser uma relação
        if not field.is_relation:
            return False

        current_model = field.related_model

        if current_model is None:
            return False

    return False


# ============================================================
# GERAR QUERY DE PESQUISA
# ============================================================

def build_search_query(Model, search):

    q = Q()

    if not search:
        return q


    # --------------------------------------------------------
    # CONFIGURAÇÃO _resaas DO MODEL
    # --------------------------------------------------------

    resaas = getattr(
        Model,
        "RESAAS",
        None
    )

    search_fields = getattr(
        resaas,
        "search_fields",
        None
    )


    # --------------------------------------------------------
    # SE O MODEL DEFINIU search_fields
    # --------------------------------------------------------

    if search_fields:

        for field in search_fields:

            if not is_valid_search_field(
                Model,
                field
            ):
                continue

            q |= Q(
                **{
                    f"{field}__icontains": search
                }
            )

        return q


    # --------------------------------------------------------
    # FALLBACK AUTOMÁTICO
    # --------------------------------------------------------

    for field in Model._meta.get_fields():

        # campos texto do próprio model
        if isinstance(
            field,
            (
                CharField,
                TextField,
                EmailField,
            )
        ):

            q |= Q(
                **{
                    f"{field.name}__icontains": search
                }
            )

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




class DynamicFilterBackend(DjangoFilterBackend):

    def get_filterset_class(self, view, queryset=None):

        if queryset is None:
            return None

        Model = queryset.model

        filter_fields = [
            field.name
            for field in Model._meta.fields
            if not isinstance(
                field,
                (
                    models.FileField,
                    models.ImageField,
                )
            )
        ]

        Meta = type(
            "Meta",
            (),
            {
                "model": Model,
                "fields": filter_fields,
            }
        )

        AutoFilterSet = type(
            f"{Model.__name__}AutoFilterSet",
            (FilterSet,),
            {
                "Meta": Meta
            }
        )

        return AutoFilterSet

# -----------------------------------
# 🚀 BASE API VIEW
# -----------------------------------

class BaseAPIView(SelectMixin, ModelViewSet):
    """
    ViewSet base multi-tenant com controlo automático de permissões.
    """

    filter_backends = [
        DynamicFilterBackend,
        OrderingFilter
    ]

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
        'pdf': 'pdf',
        'pdf_list': 'pdf_list',
    }

    # -----------------------------------
    # 🔍 SEARCH
    # -----------------------------------

    def apply_dynamic_search(self, qs):

        search = (
            self.request
            .query_params
            .get("search", "")
            .strip()
        )

        if not search:
            return qs

        Model = qs.model

        q = build_search_query(
            Model,
            search
        )

        # Se nenhum campo pesquisável foi encontrado,
        # não devolver todos os registos.
        if not q.children:
            return qs.none()

        return qs.filter(q).distinct()

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
                state="Active"
            ).exists()

            if not ativo:
                fail(request, "Módulo '{module}' não ativo")
        else:
            fail(request, "Módulo '{module}' não definido")

        action = self.action
        model = self.get_model()

        perm_map = self.get_method_permission()
        perm_prefix = perm_map.get(action)

        if not perm_prefix:
            fail(request, 'Permissão não definida para esta ação')
            

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
            fail(request, f'Não autorizado ')
            

    # -----------------------------------
    # 📊 QUERYSET (SAFE MULTI-TENANT)
    # -----------------------------------

    def get_queryset(self):

        qs = super().get_queryset()

        Model = qs.model


        # ========================================================
        # TENANT
        # ========================================================

        if hasattr(Model, "entity_id"):
            qs = qs.filter(
                entity_id=self.request.entity_id
            )

        if hasattr(Model, "branch_id"):
            qs = qs.filter(
                branch_id=self.request.branch_id
            )


        # ========================================================
        # OBJECTS
        # ========================================================

        objects_filter = (
            self.request
            .query_params
            .get("objects", "")
            .strip()
        )


        # TODOS
        if (
            objects_filter == "all"
            and hasattr(Model, "all_objects")
        ):

            qs = Model.all_objects.all()


        # APAGADOS
        elif (
            objects_filter == "deleted"
            and hasattr(Model, "deleted_objects")
        ):

            qs = Model.deleted_objects.all()


        # ========================================================
        # REAPLICAR TENANT
        # ========================================================

        if hasattr(Model, "entity_id"):
            qs = qs.filter(
                entity_id=self.request.entity_id
            )

        if hasattr(Model, "branch_id"):
            qs = qs.filter(
                branch_id=self.request.branch_id
            )


        # ========================================================
        # SEARCH
        # ========================================================

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