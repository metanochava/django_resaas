"""GET auth/permissions/ (PermissionAPIView) must return the full
permission list by default, and only apply the EntityTypeModel allowlist
filter when explicitly requested via ?entitytype= - mirroring
ModelAPIView.get_queryset()'s opt-in pattern. Applying it automatically
from request.entity_type_id silently returned zero permissions for any
EntityType without a fully curated EntityTypeModel allowlist.
"""
import pytest
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType

pytestmark = pytest.mark.django_db


def test_list_returns_all_permissions_by_default(bootstrap_tenant):
    tenant = bootstrap_tenant("perm-list")

    response = tenant["client"].get("/api/auth/permissions/")

    assert response.status_code == 200
    assert len(response.data) == Permission.objects.count() > 0


def test_list_filters_by_entitytype_when_explicitly_requested(bootstrap_tenant):
    from django_resaas.saas.models.entity_type_model import EntityTypeModel

    tenant = bootstrap_tenant("perm-list-filtered")
    entity_type_id = tenant["entity"].entity_type_id

    content_type = ContentType.objects.get_for_model(Permission)
    EntityTypeModel.objects.create(
        entity_type_id=entity_type_id, model=content_type
    )

    response = tenant["client"].get(
        "/api/auth/permissions/", {"entitytype": entity_type_id}
    )

    assert response.status_code == 200
    assert response.data
    assert all(
        row["content_type_app"] == content_type.app_label
        and row["content_type_model"] == content_type.model
        for row in response.data
    )
