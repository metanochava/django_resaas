from django.contrib import admin
from django.db import models
from django.utils import timezone

from django_resaas.saas.core.utils.translate import Translate

# Action descriptions keep Django's own `%(verbose_name_plural)s` placeholder,
# so the model name comes last ("Activate selected Patients"). They are
# canonical English here and translated per request in BaseAdmin.get_actions.

@admin.action(description="Restore selected %(verbose_name_plural)s")
def restore_selected(modeladmin, request, queryset):
    queryset.restore()

@admin.action(description="Soft delete selected %(verbose_name_plural)s")
def soft_delete_selected(modeladmin, request, queryset):
    queryset.soft_delete()


def _set_state(request, queryset, state):
    """Bulk state change that still records who/when, like save() would."""
    values = {"state": state}
    field_names = {f.name for f in queryset.model._meta.fields}

    if "updated_at" in field_names:
        values["updated_at"] = timezone.now()

    if "updated_by" in field_names:
        values["updated_by"] = request.user

    return queryset.update(**values)


@admin.action(description="Activate selected %(verbose_name_plural)s")
def activate_selected(modeladmin, request, queryset):
    _set_state(request, queryset, "Active")


@admin.action(description="Deactivate selected %(verbose_name_plural)s")
def deactivate_selected(modeladmin, request, queryset):
    _set_state(request, queryset, "Inactive")


def all_fields(model):
    return [field.name for field in model._meta.fields]


class BaseAdmin(admin.ModelAdmin):
    class Media:
        css = {
            "all": ("admin/custom.css",)
        }

    actions = [
        activate_selected,
        deactivate_selected,
        restore_selected,
        soft_delete_selected,
    ]

    list_per_page = 25

    # -----------------------------------
    # ⚙️ ACTIONS (só as que o model suporta, com descrição traduzida)
    # -----------------------------------

    def get_actions(self, request):
        actions = super().get_actions(request)
        field_names = {f.name for f in self.model._meta.fields}

        for name, needs in (
            ("activate_selected", "state"),
            ("deactivate_selected", "state"),
            ("restore_selected", "deleted_at"),
            ("soft_delete_selected", "deleted_at"),
        ):
            if name in actions and needs not in field_names:
                del actions[name]

        for name, (func, action_name, description) in list(actions.items()):
            if name in ("activate_selected", "deactivate_selected", "restore_selected", "soft_delete_selected"):
                actions[name] = (func, action_name, Translate.tdc(request, description))

        return actions

    # -----------------------------------
    # 🔍 LIST DISPLAY (teu padrão + extra)
    # -----------------------------------

    def get_list_display(self, request):
        fields = all_fields(self.model)

        # 🔥 adiciona coluna visual
        if hasattr(self.model, "deleted_at"):
            fields = fields + ["is_deleted"]

        return fields

    # -----------------------------------
    # 🔥 COLUNA VISUAL (apagado)
    # -----------------------------------

    def is_deleted(self, obj):
        return obj.deleted_at is not None

    is_deleted.boolean = True
    is_deleted.short_description = "Deleted"

    # -----------------------------------
    # 🎨 HIGHLIGHT LINHAS APAGADAS
    # -----------------------------------

    def get_queryset(self, request):
        Model = self.model

        # 🔥 usa todos por padrão
        if hasattr(Model, "all_objects"):
            qs = Model.all_objects.all()
        else:
            qs = super().get_queryset(request)

        # 🔥 filtro via query param
        objects_filter = (request.GET.get("objects") or "").strip()

        if objects_filter == "deleted" and hasattr(Model, "deleted_objects"):
            qs = Model.deleted_objects.all()

        elif objects_filter == "alive":
            qs = qs.filter(deleted_at__isnull=True)

        # 🔥 performance
        for f in Model._meta.fields:
            if isinstance(f, models.ForeignKey):
                qs = qs.select_related(f.name)

        return qs

    # -----------------------------------
    # 🎨 CSS POR LINHA (apagado = vermelho)
    # -----------------------------------

    def get_row_css(self, obj):
        if hasattr(obj, "deleted_at") and obj.deleted_at:
            return "deleted-row"
        return ""

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context["row_css"] = True
        return super().changelist_view(request, extra_context=extra_context)

    # -----------------------------------
    # 🔎 SEARCH AUTOMÁTICO
    # -----------------------------------

    def get_search_fields(self, request):
        fields = super().get_search_fields(request)

        # `search_fields = ("__all__",)` é a convenção usada nos
        # serializers DRF (BaseSerializer/`fields = "__all__"`), mas o
        # ModelAdmin do Django não a reconhece - trata "__all__" como
        # um nome de campo literal e, ao fazer o split por "__" para
        # resolver a lookup, obtém uma keyword vazia
        # (FieldError: "Cannot resolve keyword '' into field"). Expande
        # para os campos de texto reais do model, preservando a
        # intenção original de "pesquisar em todos os campos".
        if list(fields) == ["__all__"]:
            return [
                f.name for f in self.model._meta.fields
                if isinstance(f, (
                    models.CharField,
                    models.TextField,
                    models.EmailField,
                ))
            ]

        return fields

    # -----------------------------------
    # 🧩 FILTROS AUTOMÁTICOS
    # -----------------------------------

    def get_list_filter(self, request):
        filters = []

        for f in self.model._meta.fields:
            if isinstance(f, (models.BooleanField, models.DateField, models.DateTimeField)):
                filters.append(f.name)

            if isinstance(f, models.ForeignKey):
                filters.append(f.name)

        # 🔥 filtro visual soft delete
        if hasattr(self.model, "deleted_at"):
            filters.append("deleted_at")

        return filters

    # -----------------------------------
    # 🔒 READONLY
    # -----------------------------------

    def get_readonly_fields(self, request, obj=None):
        return [
            f.name for f in self.model._meta.fields
            if f.name in ["id", "created_at", "updated_at", "deleted_at"]
        ]

    # -----------------------------------
    # 🏢 AUTO FIELDS
    # -----------------------------------

    def save_model(self, request, obj, form, change):

        if hasattr(obj, "created_by") and not obj.created_by:
            obj.created_by = request.user

        if hasattr(obj, "updated_by"):
            obj.updated_by = request.user

        if hasattr(obj, "entity_id") and not obj.entity_id:
            obj.entity_id = getattr(request, "entity_id", None)

        if hasattr(obj, "branch_id") and not obj.branch_id:
            obj.branch_id = getattr(request, "branch_id", None)

        super().save_model(request, obj, form, change)


def save_model(self, request, obj, form, change):

    #
    # Utilizador
    #

    if hasattr(obj, "created_by_id") and not obj.created_by_id:
        obj.created_by = request.user

    if hasattr(obj, "updated_by_id"):
        obj.updated_by = request.user

    #
    # Entity
    #

    if hasattr(obj, "entity_id") and not obj.entity_id:
        obj.entity_id = getattr(request, "entity_id", None)

    #
    # Branch
    #

    if hasattr(obj, "branch_id") and not obj.branch_id:
        obj.branch_id = getattr(request, "branch_id", None)

    super().save_model(
        request,
        obj,
        form,
        change,
    )
    