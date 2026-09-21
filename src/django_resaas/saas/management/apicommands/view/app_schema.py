# 📦 Standard library
from django_resaas.saas.core.base.access import ExplicitAccessMixin
import logging
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# 📦 Django
from django.apps import apps, apps as django_apps
from django.conf import settings
from django.contrib.contenttypes.fields import GenericRelation
from django.core.exceptions import PermissionDenied, FieldDoesNotExist
from django.db import models
from django.db.models import Q
from django.http import JsonResponse, Http404

# 📦 Django REST Framework
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from django_resaas.saas.core.decorators.action import resaas_action

# 📦 Local (django_resaas)
from django_resaas.saas.core.base.views import registerView
from django_resaas.saas.core.base.permissions import hasPermission, isPermited as hasPermissionCode
from django_resaas.saas.core.utils import ok, fail, warn, all, clean_name, reorder_fields, clean_class_name
from django_resaas.saas.models.app import App
from django_resaas.saas.models.model_extra_action import ModelExtraAction
from django_resaas.saas.management.apicommands.service.app_service import AppScaffoldService

from django_resaas.saas.core.schema import  ResaasSchemaBuilder 
from django_resaas.saas.core.utils.relation_preview import get_relation_preview_config

# 🔧 Logger
logger = logging.getLogger(__name__)

# ==========================================================
# helpers
# ==========================================================

# LABEL_KEYS = ("name", "name", "title", "descricao", "description", "label", "codigo", "code", "numero", "num", "id")
def get_route(Model):
    resaas = getattr(Model, "RESAAS", None)
    return getattr(resaas, "routes",  {
        'list': f"list_{Model._meta.model_name}",
        'add': f"add_{Model._meta.model_name}",
        'change': f"change_{Model._meta.model_name}",
        'view': f"view_{Model._meta.model_name}"
        })

def get_crud(Model):
    resaas = getattr(Model, "RESAAS", None)
    return getattr(resaas, "crud",  True)
 
def _normalize_model_name(model: str) -> str:
    """
    Aceita: Entity | entity | ENTIDADE
    Tenta resolver para o ModelName real.
    """
    m = (model or "").strip()
    if not m:
        return ""
    # Se já parece CamelCase, mantém
    if m[:1].isupper():
        return m
    # tenta Capitalize
    return m[:1].upper() + m[1:]


def _resolve_app_label(app_name: str) -> str:
    """MY_APPS entries can be either the real app_label directly (e.g.
    'saude') or the dotted AppConfig import path (e.g. 'django_resaas.
    saas', whose actual app_label is 'django_resaas' - see saas/apps.py's
    `label = "django_resaas"`, and likewise 'django_resaas.hr' -> 'hr',
    'django_resaas.notifications' -> 'notifications'). Comparing
    `model._meta.app_label == app_name` (the bug) silently returns 0
    models/no rows for every dotted entry whose label differs from its
    last path segment. Falls back to `app_name` unchanged when no
    AppConfig matches (e.g. an entry that was never actually installed)."""

    for cfg in django_apps.get_app_configs():
        if cfg.name == app_name or cfg.label == app_name:
            return cfg.label

    return app_name


def _get_model(module: str, model: str):
    module = (module or "").strip()
    model = _normalize_model_name(model)
    if not module or not model:
        raise Http404("module/model required")

    try:
        return apps.get_model(_resolve_app_label(module), model)
    except Exception:
        # tentativa: procurar por label case-insensitive
        try:
            app_config = apps.get_app_config(_resolve_app_label(module))
            for m in app_config.get_models():
                if m.__name__.lower() == model.lower():
                    return m
        except Exception:
            pass
        raise Http404(f"model not found: {module}.{model}")


def _field_type(f: models.Field) -> str:
    """
    Retorna string compatível com teu frontend rawTypes:
    CharField, TextField, ForeignKey, ManyToManyField, MoneyField, etc.
    """
    # djmoney MoneyField costuma ter internal_type MoneyField
    it = None
    try:
        it = f.get_internal_type()
    except Exception:
        it = f.__class__.__name__

    # Alguns campos proxy/relacionais podem retornar tipos internos diferentes
    # mas para teu builder basta mapear pelos names do Django.
    if isinstance(f, models.ForeignKey):
        return "ForeignKey"
    if isinstance(f, models.OneToOneField):
        return "OneToOneField"
    if isinstance(f, models.ManyToManyField):
        return "ManyToManyField"

    # ImageField.get_internal_type() returns "FileField" - Django's own
    # ImageField never overrides FileField's implementation of that
    # method, so `it` above is ALWAYS "FileField" for an ImageField too,
    # and _resolve_ui()'s own `elif ftype == "ImageField"` branch (isImage,
    # accept defaulting to "image/*", ...) could never be reached for any
    # real model field. isinstance(), checked here before the generic
    # get_internal_type() fallback below, is the actual reliable way to
    # tell them apart - same reasoning as the ForeignKey/OneToOneField
    # checks above (order relative to those doesn't matter: an
    # ImageField is never a relation field).
    if isinstance(f, models.ImageField):
        return "ImageField"

    # fallback para o internal type / classname
    return it or f.__class__.__name__


def _relation_str(f: models.Field) -> Optional[str]:
    """
    relation no formato: "app_label.ModelName"
    """
    if not isinstance(f, (models.ForeignKey, models.OneToOneField, models.ManyToManyField)):
        return None

    rel_model = f.remote_field.model
    # pode ser string "app.Model"
    if isinstance(rel_model, str):
        return rel_model

    try:
        app_label = rel_model._meta.app_label
        model_name = rel_model.__name__
        return f"{app_label}.{model_name}"
    except Exception:
        return None


def _resolve_relation_model(f: models.Field):
    """
    Returns the actual related Model class for a ForeignKey/
    OneToOneField/ManyToManyField, or None when it isn't a relation
    field or the reference is still an unresolved lazy string (should
    never happen once app registry is fully loaded, at request time,
    but _relation_str() already guards the same case defensively).
    """
    if not isinstance(f, (models.ForeignKey, models.OneToOneField, models.ManyToManyField)):
        return None

    rel_model = f.remote_field.model
    if isinstance(rel_model, str):
        return None

    return rel_model


# the rich relation picker: "card" renders the selected record as a card in
# place, "modal" as a compact input that opens the search in a modal
RELATION_PICKER_VARIANTS = ("card", "modal")


def _build_relation_config(related_model, field_config=None) -> Dict[str, Any]:
    """
    Django-Admin-style "add related" support: the schema is the only
    place that knows a relation field's target model, so it's also the
    only place that can hand the frontend everything a generic
    s-select/s-multiselect needs to let a user create a related record
    inline - which model/app to build a form for (reusing the exact
    same {app, model} pair buildFormFromSchema() already takes), which
    endpoint to POST it to (reusing ResaasSchemaBuilder.build_model()'s
    own RESAAS.endpoint-aware resolution instead of re-guessing the
    "{app}/{model}s/" convention here), and which permission codenames
    gate add/change/view - the SAME naming convention
    ResaasSchemaBuilder.build_permissions() already uses for the
    primary model. Deliberately skips build_permissions() itself (it
    queries ModelExtraAction for custom actions this doesn't need -
    would be one extra DB query per relation field per schema call).
    """
    model_info = ResaasSchemaBuilder(Model=related_model).build_model()
    related_name = related_model._meta.model_name

    config = {
        "app": model_info["app"],
        "model": model_info["class_name"],
        "endpoint": model_info["endpoint"],
        "permissions": {
            # "list" is what searching the related model requires (its own
            # endpoint enforces it); the frontend only uses it to decide
            # whether to offer the picker's search at all.
            "list": f"list_{related_name}",
            "add": f"add_{related_name}",
            "change": f"change_{related_name}",
            "view": f"view_{related_name}",
        },
        # How a generic relation picker presents this relation:
        #   "select" - the lightweight label-only select (the default)
        #   "card"   - the rich relation picker: search results + selected
        #              value as cards built from the related model's
        #              RESAAS.preview
        #   "modal"  - the same picker as a compact input that opens the
        #              search in a modal (fields that must stay one line high)
        # A declared preview alone never changes an existing form - "card" is
        # opt-in, either per relation field in the OWNING model
        # (RESAAS.fields = {"employee": {"relation_variant": "card"}}) or for
        # every relation to a model (RESAAS.preview = {..., "variant": "card"}).
        # Pages that build the picker by hand (add_employee, add_paciente)
        # read `preview` regardless of the variant.
        "variant": "select",
    }

    # the frontend route that shows ALL the data of a related record (the
    # picker's "View"); RESAAS.routes / the default view_<model> convention
    view_route = (get_route(related_model) or {}).get("view")
    if view_route:
        config["routes"] = {"view": view_route}

    preview = get_relation_preview_config(related_model)

    if preview:
        config["preview"] = preview

        declared = getattr(getattr(related_model, "RESAAS", None), "preview", None) or {}
        wanted = (field_config or {}).get("relation_variant") or declared.get("variant")

        if wanted in RELATION_PICKER_VARIANTS:
            config["variant"] = wanted

    return config


def _extract_min_max_from_validators(validators) -> Tuple[Optional[float], Optional[float], Optional[int], Optional[int]]:
    """
    Retorna: (min_value, max_value, min_length, max_length_validator)
    Observação: CharField max_length é propriedade do campo, mas às vezes também vem via MaxLengthValidator.
    """
    min_v = None
    max_v = None
    min_len = None
    max_len_v = None

    for v in validators or []:
        cname = v.__class__.__name__
        if cname == "MinValueValidator":
            try:
                min_v = float(getattr(v, "limit_value", None))
            except Exception:
                pass
        elif cname == "MaxValueValidator":
            try:
                max_v = float(getattr(v, "limit_value", None))
            except Exception:
                pass
        elif cname == "MinLengthValidator":
            try:
                min_len = int(getattr(v, "limit_value", None))
            except Exception:
                pass
        elif cname == "MaxLengthValidator":
            try:
                max_len_v = int(getattr(v, "limit_value", None))
            except Exception:
                pass

    return min_v, max_v, min_len, max_len_v

# ==========================================================
# RULES BUILDER (🔥 validação automática)
# ==========================================================
def _build_rules(payload: dict, ftype: str) -> List[Dict[str, Any]]:
    rules = []

    # ---------------- REQUIRED ----------------
    # A read_only field can never be filled in from this form (the value
    # comes from wherever actually owns it), so validating it as
    # required here would block submission over something the user has
    # no way to satisfy - required only applies to fields the user can
    # actually edit.
    if payload.get("required") and not payload.get("read_only"):
        rules.append({
            "type": "required",
            "message": "Field is required"
        })

    # ---------------- MIN LENGTH ----------------
    if payload.get("min_length") is not None:
        rules.append({
            "type": "min_length",
            "value": payload["min_length"],
            "message": f"Minimum {payload['min_length']} characters"
        })

    # ---------------- MAX LENGTH ----------------
    if payload.get("max_length") is not None:
        rules.append({
            "type": "max_length",
            "value": payload["max_length"],
            "message": f"Maximum {payload['max_length']} characters"
        })

    # ---------------- MIN VALUE ----------------
    if payload.get("min") is not None:
        rules.append({
            "type": "min",
            "value": payload["min"],
            "message": f"Minimum value {payload['min']}"
        })

    # ---------------- MAX VALUE ----------------
    if payload.get("max") is not None:
        rules.append({
            "type": "max",
            "value": payload["max"],
            "message": f"Maximum value {payload['max']}"
        })

    # ---------------- EMAIL ----------------
    if ftype == "EmailField":
        rules.append({
            "type": "email",
            "message": "Invalid email"
        })

    return rules


def _get_resaas_field_config(field_obj):
    Model = field_obj.model
    resaas = getattr(Model, "RESAAS", None)
    if not resaas:
        return {}

    fields = getattr(resaas, "fields", {}) or {}
    return fields.get(field_obj.name, {})


def _json_safe(value):
    """Best-effort coercion of a Django field default into something the
    Response's JSON renderer can actually serialize (UUID, Decimal, date/
    datetime, model instances, etc. all fail json.dumps as-is). Anything
    that already round-trips (str/int/float/bool/None) is returned
    untouched; anything else falls back to str() rather than crashing
    the whole schema response over one field's default."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    try:
        return str(value)
    except Exception:
        return None


def _get_field_default(field_obj):
    """Django's own default resolution (field.get_default()) already
    handles callable defaults (e.g. `default=list`, `default=uuid.uuid4`)
    correctly - reading `field.default` directly would hand back the
    callable itself instead of its value. auto_now/auto_now_add fields
    (created_at/updated_at) report has_default()=False, which is
    correct here: their value comes from Django's pre_save() at save
    time, not from a static default a form should ever prefill."""
    try:
        if not field_obj.has_default():
            return None
        return _json_safe(field_obj.get_default())
    except Exception:
        return None


# ==========================================================
# UI RESOLVER (🔥 BONUS SEM ALTERAR LÓGICA)
# ==========================================================
def _resolve_ui(field_obj, ftype: str, payload: dict) -> dict:
    ui = {}
    component = ""
    props = {}
    
    # ---------------- FILE ----------------
    if ftype == "FileField":
        component = "s-file"
        ui["isFile"] = True
        cfg = _get_resaas_field_config(field_obj)
        props["accept"] = cfg.get("accept", "*")
        props["multiple"] = bool(cfg.get("multiple", False))
        if cfg.get("max_size"):
            props["maxSize"] = cfg.get("max_size")

    elif ftype == "ImageField":
        # "s-image" was never an actual registered component (boot/
        # components.js only ever registered s-upload/s-file, both
        # UploadComponent.vue) - every ImageField field in the schema
        # resolved to a component Vue couldn't find. s-file/s-upload
        # already previews an image correctly on its own (File.type/
        # mime_type-based - see UploadComponent.vue's resolvePreview()),
        # so there's no need for a separate component at all.
        component = "s-file"
        ui["isImage"] = True
        cfg = _get_resaas_field_config(field_obj)
        props["accept"] = cfg.get("accept", "image/*")
        props["multiple"] = bool(cfg.get("multiple", False))
        if cfg.get("max_size"):
            props["maxSize"] = cfg.get("max_size")

    # ---------------- RELATIONS ----------------
    elif ftype in ["ForeignKey", "OneToOneField"]:
        component = "s-select"
        ui["isRelation"] = True

    elif ftype == "ManyToManyField":
        component = "s-multiselect"
        ui["isRelation"] = True

    # ---------------- BOOLEAN ----------------
    elif ftype == "BooleanField":
        component = "s-toggle"


    # ---------------- TEXT (🔥 EDITOR) ----------------
    elif ftype == "TextField":
        component = "s-editor"
        ui["isRichText"] = True

        props["toolbar"] = [
            ["bold", "italic", "underline"],
            ["quote", "unordered", "ordered"],
            ["link"],
            ["undo", "redo", "fullscreen"]
        ]
        
        props["minHeight"] = "150px"


  # ---------------- NUMBERS ----------------
    elif ftype in ["IntegerField", "FloatField", "DecimalField"]:
        component = "s-input"


        props["type"] = "number"
        if payload.get("min") is not None:
            props["min"] = payload["min"]

        if payload.get("max") is not None:
            props["max"] = payload["max"]

    # ---------------- CHAR ----------------
    elif ftype == "CharField":
        component = "s-input"
            
        if payload.get("max_length"):
            props["maxlength"] = payload["max_length"]

        if payload.get("min_length"):
            props["minlength"] = payload["min_length"]

    elif ftype == "BooleanField":
        component = "s-switch"

    # ---------------- DATE ----------------
    elif ftype == "DateField":
        component = "s-date"

    # ---------------- TIME ----------------
    elif ftype == "TimeField":
        component = "s-time"

    # ---------------- DATETIME ----------------
    elif ftype == "DateTimeField":
        component = "s-date-time"

    if payload.get("choices"):
        component = "s-select"

    # Generic read_only support, for ANY field type - payload["read_only"]
    # is already fully resolved by _schema_fields() (field.editable=False
    # OR a RESAAS.fields override, e.g. RESAAS.fields = {"email":
    # {"read_only": True}}), so read it from there instead of
    # recomputing it from the RESAAS config alone (which would miss the
    # editable=False case). Mirrors "required" being a plain schema-level
    # flag every component can read, and also flows straight into
    # props["readonly"] (the actual HTML/Quasar attribute name) so it
    # reaches the real <s-input>/etc. via the existing v-bind="f.props"
    # every field already goes through - no per-model frontend
    # workaround needed.
    if payload.get("read_only"):
        props["readonly"] = True

    result = {
        "component": component,
        "ui": ui,
    }

    if props:
        result["props"] = props

    return result


def _schema_fields(Model) -> List[Dict[str, Any]]:
    """
    Constrói fields[] pro teu builder.
    """
    out: List[Dict[str, Any]] = []

    # pega campos concretos + m2m
    for f in Model._meta.get_fields():

        if f.name in []:
            continue
        # ignora relações reversas
        if getattr(f, "auto_created", False) and not getattr(f, "concrete", False):
            continue

        # GenericRelation (e.g. AddressMixin's `addresses`) is explicitly
        # declared, so auto_created=False lets it slip past the check
        # above - it's still not a real form field (no single value to
        # edit), so it needs its own exclusion.
        if isinstance(f, GenericRelation):
            continue

        # f pode ser ManyToOneRel etc; queremos só Fields
        if not hasattr(f, "name"):
            continue


        # ignora through automático de m2m reverso
        if getattr(f, "many_to_many", False) and getattr(f, "remote_field", None) and getattr(f.remote_field, "through", None):
            # se for o M2M "real" do Model (concrete), deixa passar
            if not getattr(f, "concrete", False):
                continue

        field_obj = f
        if not isinstance(field_obj, (models.Field, models.ManyToManyField)):
            continue

        ftype = _field_type(field_obj)
        relation = _relation_str(field_obj)

        # required: no teu frontend “required = not blank”
        required = True
        try:
            required = not bool(getattr(field_obj, "blank", False))
        except Exception:
            required = True

        cfg = _get_resaas_field_config(field_obj)

        # read_only: mirrors DRF's own ModelSerializer behavior - a field
        # Django already excludes from forms (editable=False, e.g. the
        # id/entity/branch fields BaseModel/SoftBaseModel declare) is
        # read_only for the exact same reason a serializer would mark it
        # so automatically. A RESAAS.fields override covers the fields
        # that stay editable=True at the model level but are still only
        # ever settable through a separate flow (e.g. User.email/mobile/
        # password - see saas/models/user.py).
        read_only = (not bool(getattr(field_obj, "editable", True))) or bool(cfg.get("read_only", False))

        # write_only: no Django model-level equivalent (nothing like
        # DRF's Field(write_only=True) exists on a model field) - purely
        # a RESAAS.fields declarative override, for fields that are
        # accepted on input but the real serializer never returns (e.g.
        # a set-password field). The schema only ever *describes* this -
        # actual enforcement still lives in the serializer, exactly like
        # read_only above.
        write_only = bool(cfg.get("write_only", False))

        # allow_null: Django already tracks this natively (field.null) -
        # no override needed, same as required reading field.blank
        # directly.
        allow_null = bool(getattr(field_obj, "null", False))

        # default: the value a new/add form can safely prefill and the
        # value the backend itself falls back to when the field is
        # omitted - see _get_field_default() for why field.get_default()
        # (not field.default) is used.
        default_value = _get_field_default(field_obj)

        # initial: a rarer, form-only prefill override for when the
        # form's starting value should differ from the actual model/DB
        # default (e.g. defaulting a status picker to "draft" in the UI
        # without changing what the column defaults to at the DB level).
        # Falls back to `default` when a model declares no override, so
        # every field still has one sensible initial value to seed a new
        # form with.
        initial_value = cfg.get("initial", default_value)

        # choices
        choices = None
        try:
            if getattr(field_obj, "choices", None):
                ch = list(field_obj.choices)
                # normaliza para [[value,label], ...]
                choices = [[c[0], str(c[1])] for c in ch]
        except Exception:
            choices = None

        # lengths
        max_length = getattr(field_obj, "max_length", None)

        # validators
        validators = getattr(field_obj, "validators", []) or []
        min_v, max_v, min_len, max_len_validator = _extract_min_max_from_validators(validators)

        # se veio MaxLengthValidator e o campo não tem max_length definido, usamos o do validator
        if max_length is None and max_len_validator is not None:
            max_length = max_len_validator

        payload: Dict[str, Any] = {
            "name": field_obj.name,
            "type": ftype,
            "label": str(getattr(field_obj, "verbose_name", field_obj.name) or field_obj.name).replace("_", " ").title(),
            "verbose_name": str(getattr(field_obj, "verbose_name", "") or ""),
            "help_text": str(getattr(field_obj, "help_text", "") or ""),
            "required": bool(required),
            "read_only": bool(read_only),
            "write_only": bool(write_only),
            "allow_null": bool(allow_null),
            "default": default_value,
            "initial": initial_value,
            "choices": choices or [],
            "relation": relation,  # None se não for relacional
            "max_length": max_length,
            "min_length": min_len,
            "min": min_v,
            "max": max_v,
        }

        # relation_config: Django-Admin-style "add related" metadata -
        # only relation fields get it, see _build_relation_config().
        if relation:
            related_model = _resolve_relation_model(field_obj)
            if related_model is not None:
                payload["relation_config"] = _build_relation_config(related_model, cfg)

                # the card picker is single-selection; a many-to-many keeps
                # the multi-select
                if isinstance(field_obj, models.ManyToManyField):
                    payload["relation_config"]["variant"] = "select"

        # limpa keys None pra ficar bonito
        payload = {k: v for k, v in payload.items() if v is not None}

        # 🔥 RULES
        rules = _build_rules(payload, ftype)
        if rules:
            payload["rules"] = rules

        ui_data = _resolve_ui(field_obj, ftype, payload)
        payload.update(ui_data)

        out.append(payload)

    return out


class AppSchemaAPIView(ExplicitAccessMixin, ModelViewSet):
    # PROTECTED: authenticated callers only (no public actions)


    A = []
    serializer_class = None

    def _ensure_dev(self, request):
        if not settings.DEBUG:
            raise PermissionDenied("module_creation_disabled")

    def list(self, request):
        self._ensure_dev(request)
        result = []

        for app in settings.MY_APPS:

            app_label = _resolve_app_label(app)

            models = [
                m for m in django_apps.get_models()
                if m._meta.app_label == app_label
            ]

            result.append({
                "name": app,
                "models": len(models)
            })

        return all(request, apps= result)

    # ======================================================
    # GET /api/django_resaas/resaasapps/lookup/?app=<name>
    # Mesma informação de retrieve() (lista de models), mas o nome vai
    # em query param em vez de path segment - necessário para nomes
    # com ponto (ex.: "django_resaas.saas"), que o router do DRF nunca
    # consegue rotear como pk (um "." num path segment é sempre
    # interpretado como separador de format suffix - "django_resaas.
    # saas/" resolve para pk="django_resaas", format="saas", nunca
    # chega a retrieve() com o pk inteiro). retrieve() continua a
    # existir tal e qual para nomes sem ponto - isto só cobre o caso
    # que o path nunca conseguiria representar.
    # ======================================================
    @resaas_action(detail=False, methods=["get"])
    def lookup(self, request):
        app_label = _resolve_app_label(request.query_params.get("app", ""))
        models = [
            m.__name__ for m in apps.get_models()
            if m._meta.app_label == app_label
        ]
        return all(request, models=models)


    @hasPermission("delete_app")
    def destroy(self, request, pk=None):
        name = pk.lower()
        self._ensure_dev(request)

        # Qualquer app "django_resaas" ou "django_resaas.<algo>" (saas,
        # hr, notifications, ...) é core da própria plataforma - nunca
        # apagável por aqui, independentemente de ter ou não pasta
        # própria em BASE_DIR (django_resaas.saas/hr/notifications vivem
        # dentro do pacote da biblioteca, não como pasta scaffolded).
        # Verificado ANTES do "not found" - "protegido" é a resposta
        # certa mesmo quando module_path não existe fisicamente.
        if name == "django_resaas" or name.startswith("django_resaas."):
            return warn(request, "module_protected")

        if name == "hr":
            return warn(request, "module_protected")

        module_path = Path(settings.BASE_DIR) / name

        if not module_path.exists():
            return fail(request, "module_not_found")

        shutil.rmtree(module_path)

        AppScaffoldService._remove_from_settings(name)
        AppScaffoldService.delete_front(name)
        App.objects.get(name=name).hard_delete()
        return ok(request, "Module deleted success")

    def create(self, request):

        self._ensure_dev(request)

        name = request.data.get("name")

        if not name:
            return fail(request, "module name required")
            
        try:
            path = AppScaffoldService.create_back(name)
        except Exception as e:
            return fail( request, str(e),  )

        try:
            if name in ['django_resaas','hr','notifications']:
                return fail(request, "Module {name} is protected")

            AppScaffoldService.create_front(name)
            return ok(request, "app created success",  path=path )
        except Exception as e:
            return fail(  request,  "ERROR \n "+ str(e),  )



    # ======================================================
    # GET /api/django_resaas/app/<module>ac
    # lista models
    # ======================================================
    def retrieve(self, request, pk=None):

        module = _resolve_app_label(pk)
        models = []

        for model in apps.get_models():

            if model._meta.app_label == module:
                models.append(model.__name__)

        return all(request, models=models)


    # ======================================================
    # GET /api/django_resaas/app/<module>/<model>/data/
    # Retorna todos os dados do model
    # ======================================================
    
    @resaas_action(detail=True, methods=["get"], url_path=r"(?P<model>[^/.]+)/data")
    def model_data(self, request, pk=None, model=None):
        module = pk
        Model = _get_model(module, model)

        qs = Model.objects.all()

        data = list(qs.values()[:50])

        return Response({
            "results": data,
            "count": qs.count()
        })


    # ======================================================
    # GET /api/django_resaas/app/<module>/<model>/schema/
    # lista campos detalhados
    # ======================================================
    

    @resaas_action(
        detail=True,
        methods=["get"],
        url_path=r"(?P<model>[^/.]+)/schema",
    )
    def model_schema(self, request, pk=None, model=None):
        try:
            Model = apps.get_model(_resolve_app_label(pk), model)
        except LookupError:
            return fail(request, "model_not_found")

        fields = reorder_fields(
            _schema_fields(Model),
            ["id", "nid", "codigo", "code", "nome", "name", "person"],
            ["state", "entity", "branch", "created_by", "updated_by",  "created_at", "updated_at", "deleted_at", ],
        )

        schema = ResaasSchemaBuilder(Model=Model, fields=fields).build()
        return all(request, **schema)
    


class RelationsAPIView(APIView):
    """
    GET /api/django_resaas/relations/?model=app.Model&search=abc
    -> [{id, label}, ...]
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        model_str = (request.query_params.get("model") or "").strip()
        search = (request.query_params.get("search") or "").strip()

        if "." not in model_str:
            return Response({"detail": "model param must be app_label.ModelName"}, status=400)

        app_label, model_name = model_str.split(".", 1)
        Model = _get_model(app_label, model_name)

        qs = Model.objects.all()

        # Tenant + permission: this endpoint used to hand ANY model's rows to
        # ANY authenticated user. A RESAAS model (one that declares RESAAS)
        # now needs its own list/view permission in the current context and
        # only exposes the current Entity's rows; plain framework models
        # (auth.Permission, ContentType, ...) carry no tenant/permission
        # conventions and keep their previous behaviour.
        if getattr(Model, "RESAAS", None) is not None:
            model_key = Model._meta.model_name

            if not (
                hasPermissionCode(request, f"list_{model_key}")
                or hasPermissionCode(request, f"view_{model_key}")
            ):
                return Response({"detail": "Permission denied"}, status=403)

            entity_id = getattr(request, "entity_id", None)

            if hasattr(Model, "entity_id"):
                qs = qs.filter(entity_id=entity_id)

        from django.db.models import Q, CharField, TextField, EmailField

        if search:
            q = Q()

            # 🔥 tenta pegar do RESAAS
            resaas = getattr(Model, "RESAAS", None)
            search_fields = getattr(resaas, "search_fields", None)

            # 🔥 fallback (caso não exista)
            if not search_fields:
                for field in Model._meta.get_fields():

                    # 🔥 campos diretos
                    if isinstance(field, (CharField, TextField, EmailField)):
                        q |= Q(**{f"{field.name}__icontains": search})

                    # 🔥 foreign keys simples
                    elif field.is_relation and field.many_to_one:
                        try:
                            rel_model = field.related_model

                            # tenta campo name - hasattr() sozinho
                            # confunde uma property Python (ex.:
                            # ContentType.name, calculada, não uma
                            # coluna real) com um campo de BD
                            # realmente pesquisável, rebentando com
                            # FieldError: "Unsupported lookup" - só
                            # tenta o filtro quando get_field()
                            # confirma que 'name' é mesmo um campo do
                            # modelo relacionado.
                            rel_model._meta.get_field("name")
                            q |= Q(**{f"{field.name}__name__icontains": search})

                        except Exception:
                            continue
            else:
                for field in search_fields:
                    try:
                        Model._meta.get_field(field)
                        q |= Q(**{f"{field}__icontains": search})
                    except:
                        continue

            if q:
                qs = qs.filter(q)

        qs = qs.order_by("-id")[:50]

        # Not every model passed here is a RESAAS model (e.g.
        # auth.Permission/auth.Group/contenttypes.ContentType don't
        # inherit LabelValueMixin) - get_value()/get_label() only exist
        # on models that do, so both need a plain fallback (pk/str())
        # instead of assuming every model has them.
        rows = [
            {
                "id": o.pk,
                "value": o.get_value() if hasattr(o, "get_value") else o.pk,
                "label": o.get_label() if hasattr(o, "get_label") else str(o),
            }
            for o in qs
        ]
        return Response(rows, status=200)



