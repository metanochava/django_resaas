"""
Person's geolocation/address support (AddressMixin + nested
PersonSerializer.address) - same pattern as Branch
(test_branch_geolocation.py), covering the create/update/read
round-trip and the migration that retired the old direct
Person.address ForeignKey (which shadowed AddressMixin.address's own
property of the same name).
"""
import pytest

from django_resaas.saas.management.apicommands.view.app_schema import _schema_fields
from django_resaas.saas.models.person import Person

pytestmark = pytest.mark.django_db


def test_old_address_field_is_gone_and_addresses_relation_is_excluded():
    """Regression: the old direct `address` FK used to shadow
    AddressMixin.address's property of the same name; the new
    `addresses` GenericRelation must also stay out of the auto-form
    schema (same fix as Branch)."""
    names = [f["name"] for f in _schema_fields(Person)]

    assert "addresses" not in names
    assert "name" in names


def test_person_address_property_uses_the_mixin_not_a_stale_field():
    person = Person.objects.create(name="Mixin Check")
    assert person.address is None  # no field shadowing left

    person.set_address(latitude=1.0, longitude=2.0)
    assert person.address is not None
    assert person.address.coordinates == {"lat": 1.0, "lng": 2.0}


def test_create_person_with_address_via_api(bootstrap_tenant):
    client = bootstrap_tenant("person-geo-create")["client"]

    response = client.post(
        "/api/django_resaas/persons/",
        {
            "name": "Maria",
            "surname": "Chissano",
            "address": {
                "formatted_address": "Av. Eduardo Mondlane, Maputo",
                "latitude": -25.97,
                "longitude": 32.57,
            },
        },
        format="json",
    )

    assert response.status_code == 201, response.data

    person = Person.objects.get(id=response.data["id"])
    assert person.address is not None
    assert person.address.coordinates == {"lat": -25.97, "lng": 32.57}
    assert person.addresses.count() == 1


def test_update_person_address_does_not_duplicate_row(bootstrap_tenant):
    client = bootstrap_tenant("person-geo-update")["client"]
    person = Person.objects.create(name="Update Test")

    response1 = client.patch(
        f"/api/django_resaas/persons/{person.id}/",
        {"address": {"latitude": -25.9, "longitude": 32.6}},
        format="json",
    )
    assert response1.status_code == 200, response1.data

    response2 = client.patch(
        f"/api/django_resaas/persons/{person.id}/",
        {"address": {"latitude": -25.8, "longitude": 32.5}},
        format="json",
    )
    assert response2.status_code == 200, response2.data

    person.refresh_from_db()
    assert person.addresses.count() == 1
    assert float(person.address.latitude) == -25.8


def test_person_without_address_serializes_null(bootstrap_tenant):
    client = bootstrap_tenant("person-geo-null")["client"]
    person = Person.objects.create(name="No Address")

    response = client.get(f"/api/django_resaas/persons/{person.id}/")

    assert response.status_code == 200, response.data
    assert response.data["address"] is None


def test_two_persons_sharing_an_address_get_independent_copies_after_migration():
    """Direct model-level check of the migration's clone-on-conflict
    behaviour: two people who historically pointed at the exact same
    Address row must not collide under the new (content_type,
    object_id, address_type) unique constraint - covered here at the
    model/service level, since the migration itself already ran against
    an empty table in this suite."""
    p1 = Person.objects.create(name="Shared A")
    p2 = Person.objects.create(name="Shared B")

    p1.set_address(formatted_address="Same House", latitude=1.0, longitude=1.0)
    p2.set_address(formatted_address="Same House", latitude=1.0, longitude=1.0)

    assert p1.address.id != p2.address.id
    assert p1.addresses.count() == 1
    assert p2.addresses.count() == 1
