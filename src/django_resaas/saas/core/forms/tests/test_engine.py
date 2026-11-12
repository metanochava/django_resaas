"""Form Engine core (no database): the condition DSL, definition validation,
layer merging (a lower layer never weakens a higher one) and server-side
validation of submissions."""
from decimal import Decimal

import pytest

from django_resaas.saas.core.forms.definition import FormDefinitionError, validate_definition
from django_resaas.saas.core.forms.dsl import ConditionError, evaluate, validate_condition
from django_resaas.saas.core.forms.merge import merge
from django_resaas.saas.core.forms.validation import validate_submission


def _definition(**extra):
    base = {
        "schema_version": "1.0", "key": "hotel.check_in", "mode": "declarative", "layout": "wizard",
        "sections": [
            {"key": "guest", "label": "Guest", "fields": [
                {"name": "full_name", "type": "text", "label": "Full name", "required": True},
                {"name": "foreigner", "type": "boolean", "label": "Foreigner"},
                {"name": "passport", "type": "text", "label": "Passport",
                 "required_if": {"field": "foreigner", "op": "eq", "value": True},
                 "visible_if": {"field": "foreigner", "op": "eq", "value": True}},
            ]},
            {"key": "stay", "label": "Stay", "fields": [
                {"name": "nights", "type": "integer", "label": "Nights", "required": True,
                 "validators": [{"rule": "min", "value": 1}]},
                {"name": "rate", "type": "decimal", "label": "Rate"},
                {"name": "total", "type": "decimal", "label": "Total", "calculate": {"op": "product", "of": ["nights", "rate"]}},
                {"name": "companions", "type": "repeater", "label": "Companions", "max_items": 3,
                 "fields": [{"name": "name", "type": "text", "required": True}]},
            ]},
        ],
    }
    base.update(extra)
    return base


# ------------------------------------------------------------------ DSL

def test_conditions_combine_and_never_run_code():
    data = {"age": 17, "country": "MZ", "tags": ["vip"], "guest": {"kind": "adult"}}
    assert evaluate({"field": "age", "op": "lt", "value": 18}, data)
    assert evaluate({"all": [{"field": "country", "op": "in", "value": ["MZ", "ZA"]},
                             {"not": {"field": "tags", "op": "empty"}}]}, data)
    assert evaluate({"field": "guest.kind", "op": "eq", "value": "adult"}, data)
    assert evaluate({"field": "tags", "op": "contains", "value": "vip"}, data)
    assert not evaluate({"any": [{"field": "age", "op": "gte", "value": 18},
                                 {"field": "missing", "op": "not_empty"}]}, data)
    assert evaluate(None, data)


@pytest.mark.parametrize("bad", [
    {"field": "x", "op": "eval", "value": "__import__('os')"},
    {"field": "x", "op": "eq"},
    {"field": "x", "op": "in", "value": "a"},
    {"js": "return true"},
    {"all": []},
    "x > 1",
])
def test_invalid_conditions_are_refused(bad):
    with pytest.raises(ConditionError):
        validate_condition(bad)


# ------------------------------------------------------------------ definitions

def test_a_valid_definition_passes():
    assert validate_definition(_definition())["key"] == "hotel.check_in"


@pytest.mark.parametrize("change, path", [
    ({"schema_version": "2.0"}, "schema_version"),
    ({"mode": "workflow"}, "submit"),
    ({"mode": "workflow", "submit": {"endpoint": "https://evil.example/steal/"}}, "submit"),
    ({"mode": "hybrid"}, "source"),
    ({"layout": "carousel"}, "layout"),
    ({"script": "alert(1)"}, ""),
])
def test_invalid_definitions_are_refused(change, path):
    with pytest.raises(FormDefinitionError) as error:
        validate_definition(_definition(**change))
    assert error.value.path == path


def test_invalid_fields_are_refused():
    definition = _definition()
    definition["sections"][0]["fields"].append({"name": "full_name", "type": "text"})   # repeated
    with pytest.raises(FormDefinitionError):
        validate_definition(definition)
    definition = _definition()
    definition["sections"][0]["fields"][0]["validators"] = [{"rule": "pattern", "value": "(" }]
    with pytest.raises(FormDefinitionError):
        validate_definition(definition)
    definition = _definition()
    definition["sections"][0]["fields"].append({"name": "widget", "type": "custom", "component": "<script>"})
    with pytest.raises(FormDefinitionError):
        validate_definition(definition)


def test_a_workflow_submits_to_a_relative_endpoint():
    definition = _definition(mode="workflow", submit={"endpoint": "hotel/stays/{id}/check_in/", "method": "post"})
    assert validate_definition(definition)["submit"]["endpoint"] == "hotel/stays/{id}/check_in/"


# ------------------------------------------------------------------ layers

def test_a_lower_layer_customises_but_never_weakens():
    platform = _definition(mode="workflow", submit={"endpoint": "hotel/stays/{id}/check_in/"})
    entity = {
        "schema_version": "1.0", "key": "hotel.check_in", "title": "Check-in (our hotel)",
        "submit": {"endpoint": "evil/steal/"},                                   # ignored
        "sections": [
            {"key": "guest", "fields": [
                {"name": "full_name", "required": False, "visible_if": {"field": "x", "op": "empty"},
                 "label": "Name"},                                               # relabelled only
                {"name": "phone", "type": "phone", "label": "Phone"},            # added
            ]},
            {"key": "stay", "fields": [
                {"name": "nights", "validators": [{"rule": "max", "value": 30}]},  # added rule
            ]},
            {"key": "extras", "label": "Extras", "fields": [{"name": "breakfast", "type": "boolean"}]},
        ],
    }
    merged = merge([platform, None, entity])
    guest = merged["sections"][0]["fields"]
    assert merged["submit"]["endpoint"] == "hotel/stays/{id}/check_in/"
    assert merged["title"] == "Check-in (our hotel)"
    assert guest[0]["label"] == "Name" and guest[0]["required"] is True and "visible_if" not in guest[0]
    assert [f["name"] for f in guest] == ["full_name", "foreigner", "passport", "phone"]
    nights = merged["sections"][1]["fields"][0]
    assert [r["value"] for r in nights["validators"]] == [1, 30]
    assert [s["key"] for s in merged["sections"]] == ["guest", "stay", "extras"]
    validate_definition(merged)


# ------------------------------------------------------------------ submissions

def test_submissions_are_validated_by_the_server():
    definition = _definition()
    clean, errors = validate_submission(definition, {
        "full_name": "Ana", "foreigner": True, "nights": "0", "rate": "100", "total": "999999",
        "is_admin": True, "companions": [{"name": ""}, {"name": "Rui"}],
    })
    assert errors == {"passport": ["This field is required."], "nights": ["Too small."],
                      "companions.0.name": ["This field is required."]}
    assert "is_admin" not in clean

    clean, errors = validate_submission(definition, {
        "full_name": "Ana", "foreigner": False, "passport": "ignored", "nights": 2, "rate": "150.50", "total": "1",
    })
    assert errors == {}
    assert "passport" not in clean                          # hidden: dropped
    assert clean["total"] == Decimal("301.00")              # calculated by the server


def test_a_repeater_is_bounded():
    _, errors = validate_submission(_definition(), {
        "full_name": "Ana", "nights": 1, "companions": [{"name": str(i)} for i in range(5)],
    })
    assert errors == {"companions": ["Too many items."]}
