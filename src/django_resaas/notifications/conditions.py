"""
Safe, declarative condition evaluation for NotificationRule.conditions.

No eval()/exec(), no Python expressions from the database. A closed set
of operators, a small allowlist-based field-path resolver, and
fail-closed behaviour everywhere: an unknown operator, a missing field,
or a blocked "dunder" attribute all evaluate to False rather than
raising - a broken condition should silently mean "don't send", never
crash the event that's evaluating it.
"""

_OPERATORS = {
    "==": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
    ">=": lambda a, b: a is not None and b is not None and a >= b,
    ">": lambda a, b: a is not None and b is not None and a > b,
    "<=": lambda a, b: a is not None and b is not None and a <= b,
    "<": lambda a, b: a is not None and b is not None and a < b,
    "in": lambda a, b: a in b if b is not None else False,
    "not_in": lambda a, b: a not in b if b is not None else True,
    "is_null": lambda a, b: a is None,
    "is_not_null": lambda a, b: a is not None,
}

_MISSING = object()


def resolve_field(data, field_path):
    """Resolve a dotted field path (e.g. "customer.email") against a dict
    or object. Any path segment starting with "_" is rejected outright -
    this is what blocks __class__, __dict__, __mro__, __globals__, and
    every other dunder/private attribute, whether the target is a dict or
    a live object. Returns _MISSING (never raises) if the path can't be
    resolved."""

    current = data

    for segment in str(field_path).split("."):
        if not segment or segment.startswith("_"):
            return _MISSING

        if isinstance(current, dict):
            if segment not in current:
                return _MISSING
            current = current[segment]
        else:
            if not hasattr(current, segment):
                return _MISSING
            current = getattr(current, segment)

        if callable(current):
            # Never call anything a condition happens to resolve to -
            # conditions read data, they never execute code.
            return _MISSING

    return current


def evaluate_condition(condition, data):
    """Evaluate one {"field": ..., "operator": ..., "value": ...} leaf."""

    field = condition.get("field")
    operator = condition.get("operator")

    if field is None or operator not in _OPERATORS:
        return False

    left = resolve_field(data, field)

    if left is _MISSING:
        return operator in ("is_null",)

    try:
        return bool(_OPERATORS[operator](left, condition.get("value")))
    except TypeError:
        return False


def evaluate(conditions, data):
    """Evaluate a full conditions tree: {"all": [...]}, {"any": [...]},
    a single leaf dict, or an empty/falsy tree (always True - no
    conditions configured means the rule always matches)."""

    if not conditions:
        return True

    if "all" in conditions:
        return all(evaluate(c, data) for c in conditions["all"])

    if "any" in conditions:
        return any(evaluate(c, data) for c in conditions["any"])

    return evaluate_condition(conditions, data)
