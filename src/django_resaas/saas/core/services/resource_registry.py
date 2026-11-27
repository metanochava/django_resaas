"""ResourceRegistry: the catalogue of resources the Menu Manager may offer
(MENU_IMPLEMENTATION_PROGRESS.md, phase 4).

Read only. It walks the Django app registry and reads each model's
`class RESAAS` with the same conventions the schema builder uses
(core/schema/builder.py: routes default to list_/add_/change_/view_<model>,
overridable with RESAAS["routes"]). It answers three questions for the menu
catalogue:

- which models are resources (declared `crud = True`, explicitly);
- which backend views are registered for their module (core/base/registry.py,
  VIEW_REGISTRY), so a configured route is reported as present or missing;
- which permission codenames the resource uses.

It never creates menus, never grants access and is not used by build_menus yet.
A model is a resource only when it declares it; availability of a model is not
a menu entry.
"""
from dataclasses import dataclass, field

from django.apps import apps

from django_resaas.saas.core.base.registry import VIEW_REGISTRY

ROUTE_KINDS = ("list", "add", "change", "view")


@dataclass(frozen=True)
class ResourceInfo:
    app_label: str
    model_name: str
    label: str
    module: str
    routes: dict = field(default_factory=dict)
    permissions: dict = field(default_factory=dict)
    endpoints: list = field(default_factory=list)

    @property
    def key(self):
        return f"{self.app_label}.{self.model_name}"


def _resaas_dict(Model):
    """The `class RESAAS` the model itself declares. LabelValueMixin gives every
    model a default RESAAS with crud = True, which is NOT a declaration: only a
    RESAAS written in the model's own body counts (Model.__dict__). Read as the
    schema builder reads it (attributes, not a dict)."""
    resaas = Model.__dict__.get("RESAAS")
    if resaas is None:
        return {}
    return {name: getattr(resaas, name) for name in ("crud", "routes", "permissions") if hasattr(resaas, name)}


def _routes_for(model_name, resaas):
    default = {kind: f"{kind}_{model_name}" for kind in ROUTE_KINDS}
    declared = resaas.get("routes") or {}
    return {**default, **{k: v for k, v in declared.items() if k in ROUTE_KINDS and v}}


def _permissions_for(model_name, resaas):
    declared = resaas.get("permissions") or {}
    default = {
        "list": f"list_{model_name}",
        "view": f"view_{model_name}",
        "add": f"add_{model_name}",
        "change": f"change_{model_name}",
        "delete": f"delete_{model_name}",
    }
    return {**default, **{k: v for k, v in declared.items() if v}} if isinstance(declared, dict) else default


def _backend_endpoints(Model, module):
    """Endpoint keys (register_view, VIEW_REGISTRY[module]) of the views whose
    queryset is this Model. Keys are endpoint names (e.g. "agendas"), not the
    frontend route names (list_agenda), so the link is made by the view's model,
    never by guessing the name."""
    endpoints = []
    for key, view in VIEW_REGISTRY.get(module, {}).items():
        queryset = getattr(view, "queryset", None)
        if queryset is not None and getattr(queryset, "model", None) is Model:
            endpoints.append(key)
    return sorted(endpoints)


class ResourceRegistry:

    @staticmethod
    def resources():
        """Every model that declares `class RESAAS` with `crud = True`."""
        found = []
        for Model in apps.get_models():
            if Model._meta.abstract:
                continue
            resaas = _resaas_dict(Model)
            if resaas.get("crud") is not True:
                continue
            app_label = Model._meta.app_label
            model_name = Model._meta.model_name
            found.append(ResourceInfo(
                app_label=app_label,
                model_name=model_name,
                label=str(Model._meta.verbose_name),
                module=app_label,
                routes=_routes_for(model_name, resaas),
                permissions=_permissions_for(model_name, resaas),
                endpoints=_backend_endpoints(Model, app_label),
            ))
        return sorted(found, key=lambda info: info.key)

    @classmethod
    def get(cls, app_label, model_name):
        """The resource for one model, or None when it is not declared as one."""
        for info in cls.resources():
            if info.app_label == app_label and info.model_name == model_name.lower():
                return info
        return None

    @classmethod
    def without_backend_endpoint(cls):
        """Resources declared as CRUD whose model has no registered API view.
        A menu may still point to them (a frontend page), but validate_menus
        reports them so the gap is visible."""
        return [info for info in cls.resources() if not info.endpoints]
