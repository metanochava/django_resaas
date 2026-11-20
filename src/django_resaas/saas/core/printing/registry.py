"""The printable documents, registered by the modules.

Each module declares its documents in `<app>/documents.py` (the core never
imports a module by name - it looks for that file, like mobile_tabs.py):

    DOCUMENTS = [{
        "code": "sales.receipt",              # unique, "<app>.<name>"
        "label": "Receipt",                   # canonical English (translated on render)
        "permission": "view_sale",            # needed to print it
        "template": "sales/receipt.html",     # extends django_resaas/print/base.html
        "formats": ["thermal_80", "thermal_58", "a4", "a5", "a6"],
        "default_format": "thermal_80",
        "queryset": lambda request: ...,      # the objects the request may print (tenant scope)
        "context": lambda request, obj, paper: {...},
        "title": lambda obj: "Receipt 12",    # optional, the PDF's title
    }]

`register(document)` adds one at runtime (tests, apps without the file).
"""
import importlib
import logging

from django.apps import apps

from .formats import PAPER_FORMATS

logger = logging.getLogger(__name__)

REQUIRED = ("code", "label", "permission", "template", "formats", "queryset", "context")

_documents = None
_extra = {}


def _valid(document, app_label):
    missing = [key for key in REQUIRED if key not in document]
    unknown = [code for code in document.get("formats", []) if code not in PAPER_FORMATS]
    if missing or unknown or not document.get("formats"):
        logger.warning("printing: document %r of %s ignored (missing %s, unknown formats %s)",
                       document.get("code"), app_label, missing, unknown)
        return None
    return {**document, "app": document.get("app", app_label),
            "default_format": document.get("default_format") or document["formats"][0]}


def _discover():
    found = {}
    for config in apps.get_app_configs():
        module_name = f"{config.name}.documents"
        try:
            module = importlib.import_module(module_name)
        except ModuleNotFoundError as exc:
            if exc.name == module_name:
                continue
            raise
        for document in getattr(module, "DOCUMENTS", []) or []:
            valid = _valid(document, config.label) if isinstance(document, dict) else None
            if valid:
                found[valid["code"]] = valid
    return found


def documents():
    global _documents
    if _documents is None:
        _documents = _discover()
    return {**_documents, **_extra}


def get(code):
    return documents().get(str(code or ""))


def register(document, app_label="django_resaas"):
    valid = _valid(document, app_label)
    if valid:
        _extra[valid["code"]] = valid
    return valid


def unregister(code):
    _extra.pop(code, None)


def available(request):
    """The documents the CURRENT profile may print: its permission (an Active
    assignment), the document's module active and entitled for the Entity."""
    from django_resaas.saas.core.base.permissions import check_permission
    from django_resaas.saas.core.entitlements import has_module
    from django_resaas.saas.core.menus import active_app_names, is_active_app

    entity_type_id = getattr(request, "entity_type_id", None)
    if not entity_type_id:
        return []
    active = active_app_names(entity_type_id)
    configs = {config.label: config for config in apps.get_app_configs()}
    result = []
    for document in documents().values():
        config = configs.get(document["app"])
        if config is None or not is_active_app(config, active) or not has_module(request, document["app"]):
            continue
        if not check_permission(request, document["permission"]):
            continue
        result.append(document)
    return sorted(result, key=lambda document: document["code"])
