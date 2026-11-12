"""Server-side validation of what a form submits - the backend is the
authority; hidden or readonly fields in the browser are never security.

validate_submission(definition, data) -> (clean, errors):

- only the definition's fields are kept (unknown keys are dropped);
- a field that is hidden (visible_if false), readonly or disabled for this
  data is dropped - the client cannot set it - and is never required;
- required / required_if, the field's type and its validators are checked;
- calculated fields are computed here (the client's value is ignored);
- repeaters and objects are checked item by item (errors as "items.0.qty").

`errors` is {path: [message, ...]} (canonical English, translated by the
caller), empty when the data is valid. The domain service that persists the
data still validates its own rules: this checks the form, not the business.
"""
import datetime
import re
from decimal import Decimal, InvalidOperation

from django_resaas.saas.core.forms.definition import iter_fields
from django_resaas.saas.core.forms.dsl import evaluate

EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _empty(value):
    return value is None or value == "" or value == []


def _coerce(field, value):
    """(value, error message or None) for the field's type."""
    ftype = field.get("type", "text")
    try:
        if ftype == "integer":
            if isinstance(value, bool) or Decimal(str(value)) != int(Decimal(str(value))):
                return value, "Enter a whole number."
            return int(Decimal(str(value))), None
        if ftype == "decimal":
            if isinstance(value, bool):
                return value, "Enter a number."
            return Decimal(str(value)), None
        if ftype == "boolean":
            return (value, None) if isinstance(value, bool) else (value, "Choose yes or no.")
        if ftype == "date":
            datetime.date.fromisoformat(str(value))
            return str(value), None
        if ftype == "time":
            datetime.time.fromisoformat(str(value))
            return str(value), None
        if ftype == "datetime":
            datetime.datetime.fromisoformat(str(value))
            return str(value), None
        if ftype == "email":
            return (value, None) if isinstance(value, str) and EMAIL.match(value) else (value, "Enter a valid e-mail.")
        if ftype in ("select",) and field.get("options"):
            allowed = [o["value"] for o in field["options"]]
            return (value, None) if value in allowed else (value, "Choose one of the options.")
        if ftype == "multiselect":
            if not isinstance(value, list):
                return value, "Choose from the options."
            if field.get("options"):
                allowed = [o["value"] for o in field["options"]]
                if any(v not in allowed for v in value):
                    return value, "Choose from the options."
            return value, None
    except (InvalidOperation, ValueError, TypeError):
        return value, {"integer": "Enter a whole number.", "decimal": "Enter a number.",
                       "date": "Enter a valid date.", "time": "Enter a valid time.",
                       "datetime": "Enter a valid date and time."}.get(ftype, "Invalid value.")
    return value, None


def _rule_errors(field, value):
    errors = []
    for rule in field.get("validators") or []:
        name, limit = rule["rule"], rule.get("value")
        message = rule.get("message")
        size = len(value) if isinstance(value, (str, list)) else None
        number = None
        try:
            number = Decimal(str(value)) if not isinstance(value, (bool, list, dict)) else None
        except (InvalidOperation, ValueError):
            number = None
        failed = (
            (name == "min_length" and size is not None and size < limit)
            or (name == "max_length" and size is not None and size > limit)
            or (name == "min_items" and isinstance(value, list) and len(value) < limit)
            or (name == "max_items" and isinstance(value, list) and len(value) > limit)
            or (name == "min" and number is not None and number < Decimal(str(limit)))
            or (name == "max" and number is not None and number > Decimal(str(limit)))
            or (name == "pattern" and isinstance(value, str) and not re.fullmatch(limit, value))
            or (name == "email" and isinstance(value, str) and not EMAIL.match(value))
        )
        if failed:
            errors.append(message or {
                "min_length": "Too short.", "max_length": "Too long.", "min": "Too small.", "max": "Too large.",
                "pattern": "Invalid format.", "email": "Enter a valid e-mail.",
                "min_items": "Add more items.", "max_items": "Too many items.",
            }[name])
    return errors


def _calculate(field, data):
    calc = field["calculate"]
    values = [data.get(name) for name in calc["of"]]
    if calc["op"] == "concat":
        return " ".join(str(v) for v in values if not _empty(v))
    numbers = []
    for v in values:
        try:
            numbers.append(Decimal(str(v)) if not _empty(v) else Decimal("0"))
        except (InvalidOperation, ValueError):
            numbers.append(Decimal("0"))
    if calc["op"] == "sum":
        return sum(numbers, Decimal("0"))
    result = Decimal("1")
    for n in numbers:
        result *= n
    return result


def _validate_fields(fields, data, scope, prefix):
    """Validate `fields` over `data` (the conditions read `scope`)."""
    clean, errors = {}, {}
    for field in fields:
        name = field["name"]
        path = f"{prefix}{name}"
        if not evaluate(field.get("visible_if"), scope):
            continue
        if field.get("calculate"):
            clean[name] = _calculate(field, {**data, **clean})
            continue
        if evaluate(field.get("readonly_if"), scope) is True and "readonly_if" in field:
            continue
        if evaluate(field.get("disabled_if"), scope) is True and "disabled_if" in field:
            continue
        value = data.get(name)
        required = bool(field.get("required")) or ("required_if" in field and evaluate(field["required_if"], scope))
        if _empty(value):
            if required:
                errors[path] = ["This field is required."]
            continue
        ftype = field.get("type", "text")
        if ftype == "repeater":
            if not isinstance(value, list):
                errors[path] = ["A list is expected."]
                continue
            items = []
            for index, item in enumerate(value):
                if not isinstance(item, dict):
                    errors[f"{path}.{index}"] = ["An object is expected."]
                    continue
                item_clean, item_errors = _validate_fields(field["fields"], item, {**scope, **item}, f"{path}.{index}.")
                items.append(item_clean)
                errors.update(item_errors)
            rule_errors = _rule_errors({"validators": [
                *([{"rule": "min_items", "value": field["min_items"]}] if "min_items" in field else []),
                *([{"rule": "max_items", "value": field["max_items"]}] if "max_items" in field else []),
                *(field.get("validators") or []),
            ]}, value)
            if rule_errors:
                errors.setdefault(path, []).extend(rule_errors)
            clean[name] = items
            continue
        if ftype == "object":
            if not isinstance(value, dict):
                errors[path] = ["An object is expected."]
                continue
            sub_clean, sub_errors = _validate_fields(field["fields"], value, {**scope, **value}, f"{path}.")
            clean[name] = sub_clean
            errors.update(sub_errors)
            continue
        value, type_error = _coerce(field, value)
        if type_error:
            errors[path] = [type_error]
            continue
        rule_errors = _rule_errors(field, value)
        if rule_errors:
            errors[path] = rule_errors
            continue
        clean[name] = value
    return clean, errors


def validate_submission(definition, data):
    """(clean, errors) - see the module docstring."""
    data = data if isinstance(data, dict) else {}
    fields = []
    for section, field in iter_fields(definition):
        if not evaluate(section.get("visible_if"), data):
            continue
        fields.append(field)
    return _validate_fields(fields, data, data, "")
