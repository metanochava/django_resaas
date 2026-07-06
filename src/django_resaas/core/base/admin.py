from django.contrib import admin
from django.db import models

# mantém tuas funções
@admin.action(description="Restaurar selecionados")
def restore_selected(modeladmin, request, queryset):
    queryset.restore()

@admin.action(description="Soft delete selecionados")
def soft_delete_selected(modeladmin, request, queryset):
    queryset.soft_delete()

def all_fields(model):
    return [field.name for field in model._meta.fields]


class BaseAdmin(admin.ModelAdmin):
    class Media:
        css = {
            "all": ("admin/custom.css",)
        }

    actions = [restore_selected, soft_delete_selected]

    list_per_page = 25

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
    is_deleted.short_description = "Apagado"

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
        candidates = [
            "name", "name", "title", "descricao",
            "codigo", "email", "username"
        ]

        return [
            f.name for f in self.model._meta.fields
            if f.name in candidates
        ]

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
    