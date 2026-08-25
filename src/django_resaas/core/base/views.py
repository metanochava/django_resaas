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
from django_resaas.models.entity import Entity

from .mixins.view.select import SelectMixin
from django_resaas.core.utils import build_select_data
from django_resaas.core.utils.pagination import ResaasPagination
from django.db import models

from django.template.loader import select_template

from django_filters.rest_framework import (
    DjangoFilterBackend,
    FilterSet,
)

from django_resaas.core.utils import (
    make_qr_b64,
    make_barcode_b64,
    png_bytes_to_b64,
    PDF
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

    pagination_class = ResaasPagination

    filter_backends = [
        DynamicFilterBackend,
        OrderingFilter
    ]

    ordering_fields = "__all__"

    # method : permission
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
        'pdflist': 'pdf_list',
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

    # ============================================================
    # 🔐 RESOLVE ACTION PERMISSION
    # ============================================================

    def get_action_permission(self):

        action_name = getattr(
            self,
            "action",
            None
        )

        if not action_name:
            return None


        # ========================================================
        # RESAAS CUSTOM ACTION
        # ========================================================

        method = getattr(
            self,
            action_name,
            None
        )

        metadata = getattr(
            method,
            "_resaas_action",
            None
        )

        if metadata:

            # O nome da função é o prefixo da permission
            #
            # discharge()
            #     ↓
            # discharge_paciente

            return metadata.get(
                "action",
                action_name
            )


        # ========================================================
        # DEFAULT / LEGACY ACTION
        # ========================================================

        return self.get_method_permission().get(
            action_name
        )

    # -----------------------------------
    # 🔐 PERMISSIONS (COM CACHE)
    # -----------------------------------

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)

        # -----------------------------------
        # 🔐 CHECK MODULE
        # -----------------------------------
        module = getattr(self, "module_name", None)

        

        if not request.entity_id:
            return fail( request,  f"{request.user}, you are not associated with any entity.",  status=403  )

        if module:
            ativo = EntityApp.objects.filter(
                entity__id=request.entity_id,
                app__name=module,
                state="Active"
            ).exists()

            if not ativo:
                return fail(request, f"Module <b>'{module}'</b> is not active.", status=403)
        else:
            return fail(request, f"Module <b>'{module}'</b> is not defined.", status=403)

        # ========================================================
        # ACTION / MODEL
        # ========================================================

        action = self.action

        model = self.get_model()


        # ========================================================
        # RESOLVE PERMISSION
        # ========================================================

        perm_prefix = self.get_action_permission()

        if not perm_prefix:
            return fail(
                request,
                "Permission is not defined for this action.",
                status=status.HTTP_403_FORBIDDEN
            )


        # ========================================================
        # CODENAME
        # ========================================================

        codename = (
            f"{perm_prefix}_"
            f"{model._meta.model_name}"
        )

        # 🔥 cache de permissões
        if not hasattr(request, "_perm_cache"):
            request._perm_cache = {}

        if codename not in request._perm_cache:
            request._perm_cache[codename] = isPermited(
                request=request,
                role=codename
            )

        if not request._perm_cache[codename]:
            fail(request, f"Unauthorized")
            

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

    @action(
        detail=True,
        methods=["post"],
        url_path="restore"
    )
    def restore(
        self,
        request,
        pk=None
    ):

        Model = self.get_model()

        queryset = Model.all_objects.all()

        if hasattr(Model, "entity_id"):
            queryset = queryset.filter(entity_id=request.entity_id)

        if hasattr(Model, "branch_id"):
            queryset = queryset.filter(branch_id=request.branch_id)

        instance = get_object_or_404(
            queryset,
            pk=pk
        )

        instance.restore(
            user=request.user
        )

        return ok(
            request,
            "Restored successfully"
        )

    # -----------------------------------
    # 💀 HARD DELETE
    # -----------------------------------

    @action(
        detail=True,
        methods=["delete"],
        url_path="hard_delete"
    )
    def hard_delete(
        self,
        request,
        pk=None
    ):

        Model = self.get_model()

        queryset = Model.all_objects.all()

        if hasattr(Model, "entity_id"):
            queryset = queryset.filter(entity_id=request.entity_id)

        if hasattr(Model, "branch_id"):
            queryset = queryset.filter(branch_id=request.branch_id)

        instance = get_object_or_404(
            queryset,
            pk=pk
        )

        instance.hard_delete()

        return ok(
            request,
            "Permanently deleted successfully"
        )

    
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




    # -----------------------------------
    # 📄 PDF
    # -----------------------------------


    def get_pdf_template(self):

        model = self.get_model()._meta.model_name
        module = self.module_name

        templates = []

        # Template explicitamente configurado
        if getattr(self, "pdf_template", None):
            templates.append(self.pdf_template)

        # Template automático do módulo
        templates.append(
            f"{module}/{model}.html"
        )

        # Default django_resaas
        templates.append(
            "django_resaas/pdf/detail.html"
        )

        return select_template(
            templates
        ).template.name


    def get_pdflist_template(self):

        model = self.get_model()._meta.model_name
        module = self.module_name

        templates = []

        if getattr(self, "pdflist_template", None):
            templates.append(
                self.pdflist_template
            )

        templates.append(
            f"{module}/{model}_list.html"
        )

        templates.append(
            "django_resaas/pdf/list.html"
        )

        return select_template(
            templates
        ).template.name


        
    # -----------------------------------
    # 📄 PDF HELPERS
    # -----------------------------------

    def get_request_entity(self, request):

        entity_id = getattr(
            request,
            "entity_id",
            None
        )

        if not entity_id:
            return None

        try:

            return Entity.objects.get(
                id=entity_id
            )

        except Entity.DoesNotExist:
            return None

    def get_logo_b64(self, entity):

        if not entity:
            return None

        try:

            if (
                entity.logo
                and entity.logo.path
            ):

                with open(
                    entity.logo.path,
                    "rb"
                ) as f:

                    return png_bytes_to_b64(
                        f.read()
                    )

        except Exception:
            pass

        return None


    # -----------------------------------
    # 📄 PDF CONTEXT
    # -----------------------------------
    def get_pdf_context(
        self,
        request,
        instance
    ):

        entity = self.get_request_entity(
            request
        )

        now = timezone.now()

        return {
            "object": instance,

            "entity": entity,

            "logo_b64": self.get_logo_b64(
                entity
            ),

            "qr_b64": make_qr_b64(
                str(instance.pk)
            ),

            "barcode_b64": make_barcode_b64(
                str(instance.pk)
            ),

            "data_emissao": now.date(),

            # =====================================
            # PDF METADATA
            # =====================================

            "pdf_title": str(instance),

            "pdf_author": (
                entity.name
                if entity
                else "RESAAS"
            ),

            "pdf_subject": (
                f"Documento de {self.get_model()._meta.verbose_name}"
            ),

            "pdf_keywords": (
                f"{self.module_name}, "
                f"{self.get_model()._meta.model_name}, "
                f"RESAAS"
            ),

            "pdf_created": now.isoformat(),

            "pdf_modified": now.isoformat(),

            "pdf_generator": "RESAAS / WeasyPrint",
        }


    def get_pdflist_context(
        self,
        request,
        queryset
    ):

        entity = self.get_request_entity(
            request
        )

        Model = self.get_model()

        now = timezone.now()

        ignore_fields = {
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
            "deleted_at",
        }

        fields = [
            field
            for field in Model._meta.fields
            if field.name not in ignore_fields
        ]

        pdf_fields = [
            {
                "name": field.name,
                "label": str(
                    field.verbose_name
                ).title(),
            }
            for field in fields
        ]

        pdf_rows = []

        for instance in queryset:

            row = []

            for field in fields:

                value = getattr(
                    instance,
                    field.name,
                    None
                )

                if field.is_relation:

                    value = (
                        str(value)
                        if value
                        else "-"
                    )

                elif field.choices:

                    display_method = getattr(
                        instance,
                        f"get_{field.name}_display",
                        None
                    )

                    if display_method:
                        value = display_method()

                elif value is None:
                    value = "-"

                row.append(value)

            pdf_rows.append(row)

        entity_id = (
            entity.pk
            if entity
            else "report"
        )

        model_label = str(
            Model._meta.verbose_name_plural
        ).title()

        return {
            "objects": queryset,

            "pdf_fields": pdf_fields,
            "pdf_rows": pdf_rows,

            "entity": entity,

            "logo_b64": self.get_logo_b64(
                entity
            ),

            "qr_b64": make_qr_b64(
                str(entity_id)
            ),

            "barcode_b64": make_barcode_b64(
                str(entity_id)
            ),

            "data_emissao": now.date(),

            # =====================================
            # PDF METADATA
            # =====================================

            "pdf_title": (
                f"Lista de {model_label}"
            ),

            "pdf_author": (
                entity.name
                if entity
                else "RESAAS"
            ),

            "pdf_subject": (
                f"Listagem de {model_label}"
            ),

            "pdf_keywords": (
                f"{self.module_name}, "
                f"{Model._meta.model_name}, "
                f"listagem, RESAAS"
            ),

            "pdf_created": now.isoformat(),

            "pdf_modified": now.isoformat(),

            "pdf_generator": "RESAAS / WeasyPrint",
        }
    @action(
        detail=True,
        methods=["get"],
        url_path="pdf"
    )
    def pdf(self, request, pk=None, *args, **kwargs):

        instance = self.get_object()

        template = self.get_pdf_template()

        context = self.get_pdf_context(
            request=request,
            instance=instance
        )

        return PDF(
            template,
            request,
            **context
        )


    # -----------------------------------
    # 📄 PDF LIST
    # -----------------------------------

    @action(
        detail=False,
        methods=["get"],
        url_path="pdflist"
    )
    def pdflist(self, request, *args, **kwargs):

        queryset = self.filter_queryset(
            self.get_queryset()
        )

        template = self.get_pdflist_template()

        context = self.get_pdflist_context(
            request=request,
            queryset=queryset
        )

        return PDF(
            template,
            request,
            **context
        )

