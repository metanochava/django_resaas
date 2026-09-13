"""
Branch's geolocation/address support (AddressMixin + nested
BranchSerializer.address) - covers the full API create/update/read
round-trip a real frontend does, the migration's data model, and the
schema-builder regression where AddressMixin's `addresses`
GenericRelation used to leak into Branch's auto-generated form fields.
"""
import pytest

from django_resaas.saas.management.apicommands.view.app_schema import _schema_fields
from django_resaas.saas.models.branch import Branch

pytestmark = pytest.mark.django_db


def test_addresses_generic_relation_is_excluded_from_schema_fields():
    """Regression: AddressMixin's `addresses` GenericRelation used to
    slip through _schema_fields()'s reverse-relation filter (auto_created
    is False for an explicitly declared GenericRelation), producing a
    bogus auto-form field with no sensible widget."""
    names = [f["name"] for f in _schema_fields(Branch)]

    assert "addresses" not in names
    assert "name" in names  # sanity: real fields still come through


def test_create_branch_with_address_via_api(bootstrap_tenant):
    tenant = bootstrap_tenant("geo-create")

    response = tenant["client"].post(
        "/api/django_resaas/branchs/",
        {
            "name": "Maputo HQ",
            "address": {
                "formatted_address": "Av. Julius Nyerere, Maputo, Mozambique",
                "latitude": -25.965245,
                "longitude": 32.589180,
                "locality": "Maputo",
                "country": "Mozambique",
                "country_code": "MZ",
            },
        },
        format="json",
    )

    assert response.status_code == 201, response.data
    assert response.data["entity"]["id"] == tenant["entity"].id

    branch = Branch.objects.get(id=response.data["id"])
    assert branch.address is not None
    assert branch.address.coordinates == {"lat": -25.965245, "lng": 32.58918}
    assert branch.addresses.count() == 1


def test_update_branch_address_does_not_duplicate_row(bootstrap_tenant):
    tenant = bootstrap_tenant("geo-update")

    branch = Branch.objects.create(name="Branch A", entity=tenant["entity"])

    response1 = tenant["client"].patch(
        f"/api/django_resaas/branchs/{branch.id}/",
        {"address": {"latitude": -25.9, "longitude": 32.6}},
        format="json",
    )
    assert response1.status_code == 200, response1.data

    response2 = tenant["client"].patch(
        f"/api/django_resaas/branchs/{branch.id}/",
        {"address": {"latitude": -25.8, "longitude": 32.5}},
        format="json",
    )
    assert response2.status_code == 200, response2.data

    branch.refresh_from_db()
    assert branch.addresses.count() == 1
    assert float(branch.address.latitude) == -25.8
    assert float(branch.address.longitude) == 32.5


def test_retrieve_branch_includes_computed_address_fields(bootstrap_tenant):
    tenant = bootstrap_tenant("geo-retrieve")

    branch = Branch.objects.create(name="Branch B", entity=tenant["entity"])
    branch.set_address(latitude=1.5, longitude=2.5, formatted_address="Somewhere")

    response = tenant["client"].get(f"/api/django_resaas/branchs/{branch.id}/")

    assert response.status_code == 200, response.data
    assert response.data["address"]["coordinates"] == {"lat": 1.5, "lng": 2.5}
    assert response.data["address"]["full_address"] == "Somewhere"


def test_branch_without_address_serializes_null(bootstrap_tenant):
    tenant = bootstrap_tenant("geo-null")

    branch = Branch.objects.create(name="Branch C", entity=tenant["entity"])

    response = tenant["client"].get(f"/api/django_resaas/branchs/{branch.id}/")

    assert response.status_code == 200, response.data
    assert response.data["address"] is None


def test_other_tenants_branch_is_not_visible(bootstrap_tenant):
    owner = bootstrap_tenant("geo-owner")
    other = bootstrap_tenant("geo-other")

    branch = Branch.objects.create(name="Private Branch", entity=owner["entity"])

    response = other["client"].get(f"/api/django_resaas/branchs/{branch.id}/")

    assert response.status_code == 404
