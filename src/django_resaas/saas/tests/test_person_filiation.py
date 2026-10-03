"""Person filiation: the father's and mother's names, as on identity
documents (free text - a parent need not be a Person in the system)."""
import pytest

from django_resaas.saas.models.person import Person

pytestmark = pytest.mark.django_db

URL = "/api/django_resaas/persons/"


def test_create_and_read_back_the_parents_names(bootstrap_tenant):
    tenant = bootstrap_tenant("person-filiation")

    created = tenant["client"].post(URL, {
        "name": "Joao", "surname": "Alberto",
        "father_name": "Alberto Machava", "mother_name": "Maria Cossa",
    }, format="json")

    assert created.status_code == 201, created.data
    person = Person.objects.get(id=created.data["id"])
    assert (person.father_name, person.mother_name) == ("Alberto Machava", "Maria Cossa")

    detail = tenant["client"].get(f"{URL}{person.id}/")
    assert detail.data["father_name"] == "Alberto Machava"
    assert detail.data["mother_name"] == "Maria Cossa"


def test_they_are_optional_and_can_be_corrected(bootstrap_tenant):
    tenant = bootstrap_tenant("person-filiation-edit")
    created = tenant["client"].post(URL, {"name": "Ana", "surname": "Cossa"}, format="json")
    assert created.status_code == 201, created.data
    assert created.data["father_name"] is None and created.data["mother_name"] is None

    changed = tenant["client"].patch(f"{URL}{created.data['id']}/", {"mother_name": "Rosa Cossa"}, format="json")

    assert changed.status_code == 200, changed.data
    assert Person.objects.get(id=created.data["id"]).mother_name == "Rosa Cossa"


def test_the_schema_describes_them(bootstrap_tenant):
    tenant = bootstrap_tenant("person-filiation-schema")

    schema = tenant["client"].get("/api/django_resaas/resaasapps/django_resaas/person/schema/")

    assert schema.status_code == 200, schema.data
    names = {field["name"] for field in schema.data["fields"]}
    assert {"father_name", "mother_name"} <= names
