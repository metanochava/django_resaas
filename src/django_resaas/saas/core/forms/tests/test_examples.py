"""The documented examples (clinic, hotel, school) are valid definitions and
the server enforces their rules."""
from django_resaas.saas.core.forms.definition import validate_definition
from django_resaas.saas.core.forms.examples import CLINIC_TRIAGE, EXAMPLES, HOTEL_CHECK_IN, SCHOOL_ENROLMENT
from django_resaas.saas.core.forms.merge import merge
from django_resaas.saas.core.forms.validation import validate_submission


def test_every_example_is_valid():
    for example in EXAMPLES:
        assert validate_definition(example) is example


def test_clinic_triage_requires_a_reason_when_urgent():
    _, errors = validate_submission(CLINIC_TRIAGE, {"temperature": "39.5", "priority": "urgent"})
    assert errors == {"reason": ["This field is required."]}
    _, errors = validate_submission(CLINIC_TRIAGE, {"temperature": "50", "priority": "normal"})
    assert errors == {"temperature": ["Too large."]}


def test_hotel_check_in_computes_the_total_and_checks_the_passport():
    clean, errors = validate_submission(HOTEL_CHECK_IN, {
        "full_name": "Ana", "foreigner": True, "passport": "ab-12", "nights": 3, "rate": "2500",
        "companions": [{"name": "Rui", "age": 8}],
    })
    assert errors == {"passport": ["Invalid format."]}
    assert str(clean["total"]) == "7500"


def test_a_hotel_may_customise_check_in_but_not_unlock_the_guest_name():
    ours = {"schema_version": "1.0", "key": "hotel.check_in", "sections": [
        {"key": "guest", "fields": [{"name": "full_name", "required": False,
                                     "visible_if": {"field": "x", "op": "empty"}},
                                    {"name": "vehicle_plate", "type": "text", "label": "Vehicle plate"}]}]}
    merged = validate_definition(merge([HOTEL_CHECK_IN, ours]))
    guest = merged["sections"][0]["fields"]
    assert guest[0]["required"] is True and "visible_if" not in guest[0]
    assert guest[-1]["name"] == "vehicle_plate"


def test_school_enrolment_needs_the_guardian_and_the_scholarship_document():
    _, errors = validate_submission(SCHOOL_ENROLMENT, {
        "name": "Rui", "surname": "Cossa", "date_of_birth": "2015-02-01", "course": "c1",
        "guardian": {"name": "Ana"}, "scholarship": True,
    })
    assert errors == {"guardian.phone": ["This field is required."],
                      "scholarship_document": ["This field is required."]}
