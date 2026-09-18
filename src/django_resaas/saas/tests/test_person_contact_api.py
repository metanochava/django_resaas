"""PersonContact had a model (models/person_contact.py) but no serializer/
view/URL at all - saas/data/person_contact/ mirrors saas/data/person/
exactly (same BaseSerializer/BaseAPIView pattern), registered on
routerdjango_resaas in urls.py the same way persons/ is."""
import pytest

from django_resaas.saas.models.person import Person

pytestmark = pytest.mark.django_db


def _make_person(**kwargs):
    return Person.objects.create(name="Joao", surname="Alberto", **kwargs)


def test_create_and_list_person_contacts(bootstrap_tenant):
    tenant = bootstrap_tenant("person-contact-crud")
    person = _make_person()

    response = tenant["client"].post(
        "/api/django_resaas/personcontacts/",
        {
            "person": str(person.id),
            "name": "Maria Alberto",
            "relationship": "Spouse",
            "phone": "+258840000000",
            "is_emergency": True,
        },
        content_type="application/json",
    )

    assert response.status_code == 201, response.data
    assert response.data["name"] == "Maria Alberto"
    assert response.data["is_emergency"] is True

    listed = tenant["client"].get(
        "/api/django_resaas/personcontacts/", {"person": str(person.id)},
    )
    assert listed.status_code == 200, listed.data
    results = listed.data.get("results", listed.data)
    assert len(results) == 1
    assert results[0]["name"] == "Maria Alberto"


def test_only_one_primary_contact_per_person_via_the_api(bootstrap_tenant):
    """PersonContact.save() demotes any other primary contact for the same
    person - confirms that server-side invariant still holds when going
    through the new API, not just direct ORM usage."""
    tenant = bootstrap_tenant("person-contact-primary")
    person = _make_person()
    client = tenant["client"]

    first = client.post(
        "/api/django_resaas/personcontacts/",
        {"person": str(person.id), "name": "Ana", "is_primary": True},
        content_type="application/json",
    )
    assert first.status_code == 201, first.data

    second = client.post(
        "/api/django_resaas/personcontacts/",
        {"person": str(person.id), "name": "Bruno", "is_primary": True},
        content_type="application/json",
    )
    assert second.status_code == 201, second.data

    first_refreshed = client.get(f"/api/django_resaas/personcontacts/{first.data['id']}/")
    assert first_refreshed.data["is_primary"] is False

    second_refreshed = client.get(f"/api/django_resaas/personcontacts/{second.data['id']}/")
    assert second_refreshed.data["is_primary"] is True
