"""The condition DSL of form definitions - JSON only, never code.

A condition is one of:

    {"field": "<name>", "op": "<operator>", "value": <json>}
    {"all": [<condition>, ...]}       every one is true
    {"any": [<condition>, ...]}       at least one is true
    {"not": <condition>}

`field` may be a dotted path into nested objects ("guest.country"). Operators
compare the field's value with `value`; `empty` / `not_empty` take no value.
Nothing is ever evaluated as code (no eval / exec / Function): unknown keys or
operators are refused by validate_condition() before a definition is saved,
and evaluate() only reads data. The frontend (quasar_resaas
utils/formConditions.js) implements the same operators.
"""
from decimal import Decimal, InvalidOperation

OPERATORS = ("eq", "ne", "in", "not_in", "gt", "gte", "lt", "lte", "empty", "not_empty", "contains")
NO_VALUE = ("empty", "not_empty")
MAX_DEPTH = 8


class ConditionError(ValueError):
    """An invalid condition (structure, operator, depth)."""


def validate_condition(condition, *, path="condition", depth=0):
    """Raise ConditionError unless `condition` is a well-formed condition."""
    if depth > MAX_DEPTH:
        raise ConditionError(f"{path}: conditions nest at most {MAX_DEPTH} levels.")
    if not isinstance(condition, dict) or not condition:
        raise ConditionError(f"{path}: a condition is an object.")
    keys = set(condition)
    if keys in ({"all"}, {"any"}):
        (key,) = keys
        items = condition[key]
        if not isinstance(items, list) or not items:
            raise ConditionError(f"{path}.{key}: a non-empty list of conditions.")
        for index, item in enumerate(items):
            validate_condition(item, path=f"{path}.{key}[{index}]", depth=depth + 1)
        return
    if keys == {"not"}:
        validate_condition(condition["not"], path=f"{path}.not", depth=depth + 1)
        return
    if "field" in keys and "op" in keys and keys <= {"field", "op", "value"}:
        if not isinstance(condition["field"], str) or not condition["field"].strip():
            raise ConditionError(f"{path}.field: the name of a field.")
        op = condition["op"]
        if op not in OPERATORS:
            raise ConditionError(f"{path}.op: one of {', '.join(OPERATORS)}.")
        if op not in NO_VALUE and "value" not in condition:
            raise ConditionError(f"{path}.value: required by '{op}'.")
        if op in ("in", "not_in") and not isinstance(condition.get("value"), list):
            raise ConditionError(f"{path}.value: '{op}' takes a list.")
        return
    raise ConditionError(f"{path}: unknown keys {sorted(keys)}.")


def read(data, path):
    """The value at a dotted path of the data, or None."""
    value = data
    for part in str(path).split("."):
        if isinstance(value, dict):
            value = value.get(part)
        else:
            return None
    return value


def _is_empty(value):
    return value is None or value == "" or value == [] or value == {}


def _number(value):
    if isinstance(value, bool):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None


def _compare(left, right, op):
    a, b = _number(left), _number(right)
    if a is None or b is None:
        # dates / times as ISO strings compare as text; anything else is false
        if isinstance(left, str) and isinstance(right, str):
            a, b = left, right
        else:
            return False
    return {"gt": a > b, "gte": a >= b, "lt": a < b, "lte": a <= b}[op]


def evaluate(condition, data):
    """True / False for this data. A missing condition (None) is true."""
    if condition is None:
        return True
    if "all" in condition:
        return all(evaluate(item, data) for item in condition["all"])
    if "any" in condition:
        return any(evaluate(item, data) for item in condition["any"])
    if "not" in condition:
        return not evaluate(condition["not"], data)

    value = read(data, condition["field"])
    op, expected = condition["op"], condition.get("value")
    if op == "empty":
        return _is_empty(value)
    if op == "not_empty":
        return not _is_empty(value)
    if op == "eq":
        return value == expected
    if op == "ne":
        return value != expected
    if op == "in":
        return value in expected
    if op == "not_in":
        return value not in expected
    if op == "contains":
        return isinstance(value, (list, str)) and expected in value
    return _compare(value, expected, op)
