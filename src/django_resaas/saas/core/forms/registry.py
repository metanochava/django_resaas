"""Forms shipped in code: a module declares its own in `<app>/forms.py`

    FORMS = [ {<definition>}, ... ]

discovered once per process (like `<app>/dashboard.py`); they are the
PLATFORM layer of their key when no published platform row exists in the
database. A broken forms.py import is never hidden, and an invalid
definition stops the discovery with FormDefinitionError (it is a bug in the
module, not data).
"""
import copy
import importlib

from django.apps import apps

from django_resaas.saas.core.forms.definition import validate_definition

_FORMS = {}
_DISCOVERED = False


def register_form(definition):
    validate_definition(definition)
    _FORMS[definition["key"]] = copy.deepcopy(definition)


def discover(force=False):
    global _DISCOVERED
    if _DISCOVERED and not force:
        return
    for config in apps.get_app_configs():
        module_name = f"{config.name}.forms"
        try:
            module = importlib.import_module(module_name)
        except ModuleNotFoundError as exc:
            if exc.name == module_name:
                continue
            raise
        for definition in getattr(module, "FORMS", None) or []:
            register_form(definition)
    _DISCOVERED = True


def code_form(key):
    discover()
    definition = _FORMS.get(key)
    return copy.deepcopy(definition) if definition else None


def code_keys():
    discover()
    return sorted(_FORMS)
