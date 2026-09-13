"""
Entity's storage-usage reporting (DiskManegarService.get_entity_usage,
EntityAPIView.storage) and the Branch list action it's shown alongside
on the Entity edit page - File previously had no entity/branch fields
at all, so none of this was even possible before.
"""
import pytest

from django_resaas.saas.models.branch import Branch
from django_resaas.saas.models.file import File
from django_resaas.saas.core.services.disc_manager import DiskManegarService

pytestmark = pytest.mark.django_db


def test_get_entity_usage_aggregates_by_category(bootstrap_tenant):
    tenant = bootstrap_tenant("storage-agg")
    entity = tenant["entity"]

    File.objects.create(entity=entity, size=2 * 1024 * 1024, funcionalidade="Logo")
    File.objects.create(entity=entity, size=5 * 1024 * 1024, funcionalidade="Photo")
    File.objects.create(entity=entity, size=1 * 1024 * 1024, funcionalidade="Photo")

    usage = DiskManegarService.get_entity_usage(entity.id)

    assert usage["total_bytes"] == 8 * 1024 * 1024
    by_category = {row["category"]: row["bytes"] for row in usage["breakdown"]}
    assert by_category["Logo"] == 2 * 1024 * 1024
    assert by_category["Photo"] == 6 * 1024 * 1024


def test_get_entity_usage_ignores_other_entities_files(bootstrap_tenant):
    tenant_a = bootstrap_tenant("storage-a")
    tenant_b = bootstrap_tenant("storage-b")

    File.objects.create(entity=tenant_a["entity"], size=10 * 1024 * 1024, funcionalidade="File")
    File.objects.create(entity=tenant_b["entity"], size=999 * 1024 * 1024, funcionalidade="File")

    usage = DiskManegarService.get_entity_usage(tenant_a["entity"].id)

    assert usage["total_bytes"] == 10 * 1024 * 1024


def test_get_entity_usage_with_no_files_is_zero(bootstrap_tenant):
    tenant = bootstrap_tenant("storage-empty")

    usage = DiskManegarService.get_entity_usage(tenant["entity"].id)

    assert usage["total_bytes"] == 0
    assert usage["breakdown"] == []


def test_storage_action_via_api(bootstrap_tenant):
    tenant = bootstrap_tenant("storage-api")
    entity = tenant["entity"]

    File.objects.create(entity=entity, size=3 * 1024 * 1024, funcionalidade="Cover")

    response = tenant["client"].get(f"/api/django_resaas/entitys/{entity.id}/storage/")

    assert response.status_code == 200, response.data
    assert response.data["total_bytes"] == 3 * 1024 * 1024
    assert response.data["breakdown"] == [{"category": "Cover", "bytes": 3 * 1024 * 1024}]


def test_branchs_action_lists_all_branches_of_the_entity(bootstrap_tenant):
    tenant = bootstrap_tenant("branchs-api")
    entity = tenant["entity"]

    Branch.objects.create(name="Second Branch", entity=entity, state="Active")

    response = tenant["client"].get(f"/api/django_resaas/entitys/{entity.id}/branchs/")

    assert response.status_code == 200, response.data
    names = {b["name"] for b in response.data}
    assert {"Main", "Second Branch"} <= names
