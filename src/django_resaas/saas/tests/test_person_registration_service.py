"""person_registration_service: the Person / Document / PersonContact part
every intake flow shares (a module's add_employee, add_paciente, ...). These
tests were only exercised through HR before HR became an application's
module; the framework now tests its own service directly."""
from types import SimpleNamespace

import pytest

from django_resaas.saas.core.services.person_registration_service import (
    PersonRegistrationError,
    create_contacts,
    create_documents,
    resolve_person,
)
from django_resaas.saas.models.document import DocumentType
from django_resaas.saas.models.person import Person

pytestmark = pytest.mark.django_db


def _request(tenant):
    return SimpleNamespace(
        user=tenant["user"], entity_id=tenant["entity"].id, branch_id=tenant["branch"].id,
        lang_id=None, META={}, query_params={}, data={},
    )


def test_a_new_person_is_created_with_the_caller_as_author(bootstrap_tenant):
    tenant = bootstrap_tenant("preg-new")

    person = resolve_person(request=_request(tenant), person_data={"name": "Ana", "surname": "Muianga"})

    assert Person.objects.filter(pk=person.pk, name="Ana", surname="Muianga").exists()
    assert person.created_by == tenant["user"]


def test_an_existing_person_is_reused_not_duplicated(bootstrap_tenant):
    tenant = bootstrap_tenant("preg-reuse")
    existing = Person.objects.create(name="Carlos", surname="Bila")
    before = Person.objects.count()

    person = resolve_person(request=_request(tenant), person_id=existing.id)

    assert person.pk == existing.pk
    assert Person.objects.count() == before


def test_an_unknown_person_id_is_a_field_error(bootstrap_tenant):
    tenant = bootstrap_tenant("preg-unknown")

    with pytest.raises(PersonRegistrationError) as raised:
        resolve_person(request=_request(tenant), person_id="00000000-0000-0000-0000-000000000000")

    assert "person_id" in raised.value.errors


def test_invalid_person_data_is_reported_under_person(bootstrap_tenant):
    tenant = bootstrap_tenant("preg-invalid")

    with pytest.raises(PersonRegistrationError) as raised:
        resolve_person(request=_request(tenant), person_data={"email": "not-an-email"})

    assert "person" in raised.value.errors


def test_documents_and_contacts_are_created_for_the_person(bootstrap_tenant):
    tenant = bootstrap_tenant("preg-docs")
    request = _request(tenant)
    person = resolve_person(request=request, person_data={"name": "Luisa", "surname": "Chissano"})
    bi = DocumentType.objects.create(name="BI", detalhes="Bilhete de identidade")

    create_documents(request=request, person=person, documents=[{"tipo": bi.id, "numero": "110100000001A"}])
    create_contacts(request=request, person=person, contacts=[{"name": "Jaime", "relationship": "Brother", "phone": "841234567"}])

    assert list(person.documents.values_list("numero", flat=True)) == ["110100000001A"]
    assert list(person.contacts.values_list("name", flat=True)) == ["Jaime"]


def test_an_invalid_contact_is_reported_under_contacts(bootstrap_tenant):
    tenant = bootstrap_tenant("preg-contact")
    request = _request(tenant)
    person = Person.objects.create(name="Esperança", surname="Zucula")

    with pytest.raises(PersonRegistrationError) as raised:
        create_contacts(request=request, person=person, contacts=[{"email": "nope"}])

    assert "contacts" in raised.value.errors
