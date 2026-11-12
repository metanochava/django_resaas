"""Form definitions (schema_version "1.0") and their validation.

A definition is JSON:

    {
      "schema_version": "1.0",
      "key": "hotel.check_in",                   # what a module asks for
      "mode": "declarative",                     # schema | declarative | hybrid | workflow
      "source": {"model": "sales.Customer"},     # schema / hybrid: the model's Schema 1.0 fields
      "layout": "wizard",                        # sections | tabs | wizard | grid
      "sections": [
        {"key": "guest", "label": "Guest", "layout": "card",
         "visible_if": <condition>,
         "fields": [<field>, ...]}
      ],
      "submit": {"endpoint": "hotel/stays/{id}/check_in/", "method": "post"},   # workflow
      "autosave": false
    }

A field:

    {"name": "nights", "type": "integer", "label": "Nights", "cols": 6,
     "required": true, "required_if": <c>, "visible_if": <c>, "readonly_if": <c>, "disabled_if": <c>,
     "default": 1, "help": "...", "options": [{"value": "a", "label": "A"}],
     "relation": {"endpoint": "sales/customers/"},          # remote autocomplete (relative API path)
     "validators": [{"rule": "min", "value": 1}, ...],
     "calculate": {"op": "sum" | "product" | "concat", "of": ["a", "b"]},
     "fields": [<field>, ...],                              # repeater / object
     "min_items": 1, "max_items": 10,                       # repeater
     "component": "saude.vital-signs",                      # a registered custom component
     "from_schema": true,                                   # hybrid: take the model field's metadata
     "locked": true}                                        # a lower layer may not hide or relax it

Labels are canonical English (translated at render time with tdc()).
Everything is data; conditions use dsl.py. validate_definition() refuses
anything else - a definition is checked before it is saved and again before
it is served.
"""
import re

from django_resaas.saas.core.forms.dsl import ConditionError, validate_condition

SCHEMA_VERSION = "1.0"
MODES = ("schema", "declarative", "hybrid", "workflow")
LAYOUTS = ("sections", "tabs", "wizard", "grid")
SECTION_LAYOUTS = ("card", "accordion", "plain")
FIELD_TYPES = (
    "text", "textarea", "email", "phone", "integer", "decimal", "boolean", "date", "time", "datetime",
    "select", "multiselect", "relation", "file", "image", "editor", "repeater", "object", "custom",
)
CONDITION_KEYS = ("visible_if", "required_if", "readonly_if", "disabled_if")
VALIDATOR_RULES = ("min_length", "max_length", "min", "max", "pattern", "email", "min_items", "max_items")
CALCULATE_OPS = ("sum", "product", "concat")
METHODS = ("post", "put", "patch")
NAME = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
KEY = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$")
COMPONENT = re.compile(r"^[a-z][a-z0-9_-]*(\.[a-z][a-z0-9_-]*)*$")
# a relative API path: segments, {placeholders}, a trailing slash - never a URL
ENDPOINT = re.compile(r"^[a-z][a-z0-9_]*(/([a-z0-9_-]+|\{[a-z_]+\}))*/$")
MAX_PATTERN = 200
MAX_FIELDS = 300

FIELD_KEYS = {
    "name", "type", "label", "help", "placeholder", "cols", "required", "default", "options", "relation",
    "validators", "calculate", "fields", "min_items", "max_items", "component", "from_schema", "locked",
    "accept", "multiple", "order", *CONDITION_KEYS,
}
SECTION_KEYS = {"key", "label", "help", "layout", "cols", "fields", "visible_if", "order", "icon"}
DEFINITION_KEYS = {"schema_version", "key", "mode", "source", "layout", "sections", "submit", "autosave", "title"}


class FormDefinitionError(ValueError):
    def __init__(self, message, *, path=""):
        super().__init__(f"{path}: {message}" if path else message)
        self.path = path
        self.detail = message


def _fail(message, path):
    raise FormDefinitionError(message, path=path)


def _condition(value, path):
    try:
        validate_condition(value, path=path)
    except ConditionError as error:
        _fail(str(error), path)


def _validators(validators, path):
    if not isinstance(validators, list):
        _fail("a list of validators.", path)
    for index, rule in enumerate(validators):
        here = f"{path}[{index}]"
        if not isinstance(rule, dict) or rule.get("rule") not in VALIDATOR_RULES:
            _fail(f"rule is one of {', '.join(VALIDATOR_RULES)}.", here)
        if set(rule) - {"rule", "value", "message"}:
            _fail("only rule, value and message.", here)
        if rule["rule"] == "pattern":
            pattern = rule.get("value")
            if not isinstance(pattern, str) or not pattern or len(pattern) > MAX_PATTERN:
                _fail(f"a pattern of at most {MAX_PATTERN} characters.", here)
            try:
                re.compile(pattern)
            except re.error:
                _fail("an invalid pattern.", here)
        elif rule["rule"] != "email" and not isinstance(rule.get("value"), (int, float)):
            _fail("a number as value.", here)


def _field(field, path, names, counter):
    counter[0] += 1
    if counter[0] > MAX_FIELDS:
        _fail(f"at most {MAX_FIELDS} fields.", path)
    if not isinstance(field, dict):
        _fail("a field is an object.", path)
    unknown = set(field) - FIELD_KEYS
    if unknown:
        _fail(f"unknown keys {sorted(unknown)}.", path)
    name = field.get("name")
    if not isinstance(name, str) or not NAME.match(name):
        _fail("name: lowercase letters, digits and _ (starting with a letter).", path)
    if name in names:
        _fail(f"the field '{name}' is repeated.", path)
    names.add(name)
    ftype = field.get("type", "text")
    if ftype not in FIELD_TYPES:
        _fail(f"type is one of {', '.join(FIELD_TYPES)}.", f"{path}.type")
    for key in CONDITION_KEYS:
        if key in field:
            _condition(field[key], f"{path}.{key}")
    if "validators" in field:
        _validators(field["validators"], f"{path}.validators")
    if "cols" in field and (not isinstance(field["cols"], int) or not 1 <= field["cols"] <= 12):
        _fail("cols: 1 to 12.", f"{path}.cols")
    if "options" in field:
        options = field["options"]
        if not isinstance(options, list) or any(not isinstance(o, dict) or "value" not in o for o in options):
            _fail("options: a list of {value, label}.", f"{path}.options")
    if "relation" in field:
        endpoint = (field["relation"] or {}).get("endpoint") if isinstance(field["relation"], dict) else None
        if not isinstance(endpoint, str) or not ENDPOINT.match(endpoint):
            _fail("relation.endpoint: a relative API path (app/resource/).", f"{path}.relation")
    if ftype == "custom" or "component" in field:
        if not isinstance(field.get("component"), str) or not COMPONENT.match(field["component"]):
            _fail("component: the name of a registered component (module.name).", f"{path}.component")
    if "calculate" in field:
        calc = field["calculate"]
        if not isinstance(calc, dict) or calc.get("op") not in CALCULATE_OPS or not isinstance(calc.get("of"), list) \
                or not calc["of"] or any(not isinstance(n, str) for n in calc["of"]) or set(calc) - {"op", "of"}:
            _fail(f"calculate: {{op: {'|'.join(CALCULATE_OPS)}, of: [field names]}}.", f"{path}.calculate")
    if ftype in ("repeater", "object"):
        children = field.get("fields")
        if not isinstance(children, list) or not children:
            _fail(f"a {ftype} has its own fields.", f"{path}.fields")
        child_names = set()
        for index, child in enumerate(children):
            _field(child, f"{path}.fields[{index}]", child_names, counter)
    elif "fields" in field:
        _fail("only a repeater or an object has fields.", f"{path}.fields")
    for key in ("min_items", "max_items"):
        if key in field and (not isinstance(field[key], int) or field[key] < 0):
            _fail(f"{key}: a whole number.", f"{path}.{key}")


def validate_definition(definition):
    """Raise FormDefinitionError unless the definition is valid; returns it."""
    if not isinstance(definition, dict):
        _fail("a definition is an object.", "")
    unknown = set(definition) - DEFINITION_KEYS
    if unknown:
        _fail(f"unknown keys {sorted(unknown)}.", "")
    if definition.get("schema_version") != SCHEMA_VERSION:
        _fail(f'schema_version must be "{SCHEMA_VERSION}".', "schema_version")
    if not isinstance(definition.get("key"), str) or not KEY.match(definition["key"]):
        _fail("key: module.name (lowercase, dotted).", "key")
    mode = definition.get("mode", "declarative")
    if mode not in MODES:
        _fail(f"mode is one of {', '.join(MODES)}.", "mode")
    if mode in ("schema", "hybrid"):
        model = (definition.get("source") or {}).get("model") if isinstance(definition.get("source"), dict) else None
        if not isinstance(model, str) or not re.match(r"^[a-z_]+\.[A-Za-z]+$", model):
            _fail("source.model: app_label.Model for a schema or hybrid form.", "source")
    if mode == "workflow":
        submit = definition.get("submit")
        if not isinstance(submit, dict) or not isinstance(submit.get("endpoint"), str) \
                or not ENDPOINT.match(submit["endpoint"]):
            _fail("submit.endpoint: a relative API path - a workflow submits to its own endpoint.", "submit")
        if submit.get("method", "post") not in METHODS:
            _fail(f"submit.method is one of {', '.join(METHODS)}.", "submit.method")
    if definition.get("layout", "sections") not in LAYOUTS:
        _fail(f"layout is one of {', '.join(LAYOUTS)}.", "layout")
    sections = definition.get("sections")
    if mode != "schema" and (not isinstance(sections, list) or not sections):
        _fail("a non-empty list of sections.", "sections")
    names, keys, counter = set(), set(), [0]
    for index, section in enumerate(sections or []):
        here = f"sections[{index}]"
        if not isinstance(section, dict):
            _fail("a section is an object.", here)
        unknown = set(section) - SECTION_KEYS
        if unknown:
            _fail(f"unknown keys {sorted(unknown)}.", here)
        if not isinstance(section.get("key"), str) or not NAME.match(section["key"]) or section["key"] in keys:
            _fail("key: a unique name.", f"{here}.key")
        keys.add(section["key"])
        if section.get("layout", "card") not in SECTION_LAYOUTS:
            _fail(f"layout is one of {', '.join(SECTION_LAYOUTS)}.", f"{here}.layout")
        if "visible_if" in section:
            _condition(section["visible_if"], f"{here}.visible_if")
        fields = section.get("fields")
        if not isinstance(fields, list) or not fields:
            _fail("a section has fields.", f"{here}.fields")
        for findex, field in enumerate(fields):
            _field(field, f"{here}.fields[{findex}]", names, counter)
    return definition


def iter_fields(definition):
    """(section, field) of every top-level field, in order."""
    for section in definition.get("sections") or []:
        for field in section.get("fields") or []:
            yield section, field
