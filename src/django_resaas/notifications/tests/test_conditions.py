"""Spec section 89: conditions must be safe - no eval/exec, dunder
attribute access blocked, unknown operator/field fails closed."""

from django_resaas.notifications.conditions import (
    _MISSING,
    evaluate,
    evaluate_condition,
    resolve_field,
)


def test_simple_true():
    assert evaluate_condition(
        {"field": "total", "operator": ">=", "value": 100}, {"total": 150}
    )


def test_simple_false():
    assert not evaluate_condition(
        {"field": "total", "operator": ">=", "value": 100}, {"total": 50}
    )


def test_all_requires_every_condition():
    conditions = {
        "all": [
            {"field": "total", "operator": ">=", "value": 100},
            {"field": "status", "operator": "==", "value": "confirmed"},
        ]
    }
    assert evaluate(conditions, {"total": 150, "status": "confirmed"})
    assert not evaluate(conditions, {"total": 150, "status": "draft"})


def test_any_requires_one_condition():
    conditions = {
        "any": [
            {"field": "total", "operator": ">=", "value": 1000},
            {"field": "status", "operator": "==", "value": "confirmed"},
        ]
    }
    assert evaluate(conditions, {"total": 1, "status": "confirmed"})
    assert not evaluate(conditions, {"total": 1, "status": "draft"})


def test_empty_conditions_always_true():
    assert evaluate({}, {})
    assert evaluate(None, {"anything": 1})


def test_unknown_operator_is_false():
    assert not evaluate_condition(
        {"field": "x", "operator": "eval", "value": 1}, {"x": 1}
    )


def test_missing_field_is_false_except_is_null():
    assert not evaluate_condition(
        {"field": "missing", "operator": "==", "value": 1}, {}
    )
    assert evaluate_condition(
        {"field": "missing", "operator": "is_null", "value": None}, {}
    )


def test_dunder_class_is_blocked():
    class Obj:
        secret = "nope"

    assert (
        resolve_field(Obj(), "__class__") is _MISSING
    )  # never resolves to the real class
    assert not evaluate_condition(
        {"field": "__class__.__mro__", "operator": "is_not_null", "value": None}, Obj()
    )


def test_dunder_dict_is_blocked():
    data = {"__dict__": "whatever"}
    assert not evaluate_condition(
        {"field": "__dict__", "operator": "==", "value": "whatever"}, data
    )


def test_callable_target_is_never_invoked():
    calls = []

    class Obj:
        def dangerous(self):
            calls.append("called")
            return "boom"

    resolve_field(Obj(), "dangerous")
    assert calls == []  # resolve_field must never call the resolved attribute


def test_in_and_not_in():
    assert evaluate_condition(
        {"field": "status", "operator": "in", "value": ["a", "b"]}, {"status": "a"}
    )
    assert evaluate_condition(
        {"field": "status", "operator": "not_in", "value": ["a", "b"]}, {"status": "c"}
    )
