# 📦 Standard library
import logging
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# 📦 Django
from django.apps import apps, apps as django_apps
from django.conf import settings
from django.core.exceptions import PermissionDenied, FieldDoesNotExist
from django.db import models
from django.db.models import Q
from django.http import JsonResponse, Http404

# 📦 Django REST Framework
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import action

# 📦 Local (django_resaas)
from django_resaas.core.base.views import registerView
from django_resaas.core.base.permissions import hasPermission
from django_resaas.core.utils import ok, fail, warn, all, clean_name, reorder_fields, clean_class_name
from django_resaas.models.app import App
from django_resaas.models.model_extra_action import ModelExtraAction
from django_resaas.management.apicommands.service.app_service import AppScaffoldService

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


def _get_model(module: str, model: str):
    module = (module or "").strip()
    model = _normalize_model_name(model)
    if not module or not model:
        raise Http404("module/model required")

    try:
        return apps.get_model(module, model)
    except Exception:
        # tentativa: procurar por label case-insensitive
        try:
            app_config = apps.get_app_config(module.split(".")[-1])
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
    if payload.get("required"):
        rules.append({
            "type": "required",
            "message": "Campo obrigatório"
        })

    # ---------------- MIN LENGTH ----------------
    if payload.get("min_length") is not None:
        rules.append({
            "type": "min_length",
            "value": payload["min_length"],
            "message": f"Mínimo {payload['min_length']} caracteres"
        })

    # ---------------- MAX LENGTH ----------------
    if payload.get("max_length") is not None:
        rules.append({
            "type": "max_length",
            "value": payload["max_length"],
            "message": f"Máximo {payload['max_length']} caracteres"
        })

    # ---------------- MIN VALUE ----------------
    if payload.get("min") is not None:
        rules.append({
            "type": "min",
            "value": payload["min"],
            "message": f"Valor mínimo {payload['min']}"
        })

    # ---------------- MAX VALUE ----------------
    if payload.get("max") is not None:
        rules.append({
            "type": "max",
            "value": payload["max"],
            "message": f"Valor máximo {payload['max']}"
        })

    # ---------------- EMAIL ----------------
    if ftype == "EmailField":
        rules.append({
            "type": "email",
            "message": "Email inválido"
        })

    return rules


def _get_resaas_field_config(field_obj):
    Model = field_obj.model
    resaas = getattr(Model, "RESAAS", None)
    if not resaas:
        return {}

    fields = getattr(resaas, "fields", {}) or {}
    return fields.get(field_obj.name, {})


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

    elif ftype == "ImageField":
        component = "s-image"
        ui["isImage"] = True
        cfg = _get_resaas_field_config(field_obj)
        props["accept"] = cfg.get("accept", "image/*")

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
        component = "s-datetime"

    if payload.get("choices"):
        component = "s-select"

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
            "choices": choices or [],
            "relation": relation,  # None se não for relacional
            "max_length": max_length,
            "min_length": min_len,
            "min": min_v,
            "max": max_v,
        }

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


def label_value(obj, arr) -> str:
    v = ''
    for k in arr:
        if hasattr(obj, k):
            v = v +' '+ str(obj._get_attr(k)) 
    return str(v)



class AppSchemaAPIView(ModelViewSet):

    A = []
    serializer_class = None

    def _ensure_dev(self, request):
        if not settings.DEBUG:
            raise PermissionDenied("module_creation_disabled")

    def list(self, request):
        self._ensure_dev(request)
        result = []

        for app in settings.MY_APPS:

            models = [
                m for m in django_apps.get_models()
                if m._meta.app_label == app
            ]

            result.append({
                "name": app,
                "models": len(models)
            })

        return all(request, apps= result)
        


    @hasPermission("delete_app")
    def destroy(self, request, pk=None):
        name = pk.lower()
        self._ensure_dev(request)

        module_path = Path(settings.BASE_DIR) / name

        if not module_path.exists():
            return fail(request, "module_not_found")

        if name == "django_resaas":
            return warn(request, "module_protected")

        if name == "hr":
            return warn(request, "module_protected")

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
            if name in ['hr', 'django_resaas']:
                return fail(request, "Module {name} protegido")

            AppScaffoldService.create_front(name)
            return ok(request, "app created success",  path=path )
        except Exception as e:
            return fail(  request,  "ERRO \n "+ str(e),  )



    # ======================================================
    # GET /api/django_resaas/app/<module>ac
    # lista models
    # ======================================================
    def retrieve(self, request, pk=None):

        module = pk
        models = []

        for model in apps.get_models():

            if model._meta.app_label == module:
                models.append(model.__name__)

        return all(request, models=models)


    # ======================================================
    # GET /api/django_resaas/app/<module>/<model>/data/
    # Retorna todos os dados do model
    # ======================================================
    
    @action(detail=True, methods=["get"], url_path=r"(?P<model>[^/.]+)/data")
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
    

    # GET /api/django_resaas/app/<module>/<model>/schema/

    @action(
        detail=True,
        methods=["get"],
        url_path=r"(?P<model>[^/.]+)/schema",
    )
    def model_schema(self, request, pk=None, model=None):
        module = pk

        try:
            Model = apps.get_model(module, model)
        except LookupError:
            return fail(request, "model_not_found")

        app_label = Model._meta.app_label
        model_name = Model._meta.model_name

        fields = reorder_fields(
            _schema_fields(Model),
            [
                "id",
                "nid",
                "codigo",
                "code",
                "nome",
                "name",
                "person",
            ],
            [
                "state",
                "entity",
                "branch",
                "created_by",
                "updated_by",
                "created_at",
                "updated_at",
                "deleted_at",
            ],
        )

        extras = ModelExtraAction.objects.filter(
            app=app_label,
            model=model_name,
            visible=True,
        ).order_by("order", "action")

        actions = [
            {
                "action": extra.action,
                "app": extra.app,
                "model": extra.model,
                "label": extra.label,
                "icon": extra.icon,
                "tooltip": extra.tooltip,
                "position": extra.position,
                "order": extra.order,
                "visible": extra.visible,
                "method": extra.method,
                "url": extra.url,
                "details": extra.details,
                "permission": extra.permission,
            }
            for extra in extras
        ]

        return all(
            request,
            module=app_label,
            model=model_name,
            fields=fields,
            actions=actions,
            config={
                "crud": get_crud(Model),
                "routes": get_route(Model),
            },
        )


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

                            # tenta campo name
                            if hasattr(rel_model, "name"):
                                q |= Q(**{f"{field.name}__name__icontains": search})

                        except:
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

        rows = [{"id": o.pk, "value": o.pk, "label": label_value(o, o.get_label_field())} for o in qs]

        # rows = [
        #     {
        #         "id": o.pk,
        #         "value": o.get_value() if hasattr(o, "get_value") else o.pk,
        #         "label": o.get_label() if hasattr(o, "get_label") else str(o),
        #     }
        #     for o in qs
        # ]
        return Response(rows, status=200)



