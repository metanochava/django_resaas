"""GET auth/permissions/ (PermissionAPIView) is paginated (ResaasPagination,
same as every other proper RESAAS CRUD endpoint - see
saas/core/utils/pagination.py), never filters by EntityType unless
?entitytype= is explicitly passed (mirroring ModelAPIView.get_queryset()'s
opt-in pattern - applying it automatically from request.entity_type_id
silently returned zero permissions for any EntityType without a fully
curated EntityTypeModel allowlist), and still supports ?page_size=0 for
callers that genuinely need the full list in one go (e.g. GroupSEPage.vue's
permission picker).
"""
import pytest
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType

pytestmark = pytest.mark.django_db


def test_list_is_paginated_by_default(bootstrap_tenant):
    tenant = bootstrap_tenant("perm-list")

    response = tenant["client"].get("/api/auth/permissions/")

    assert response.status_code == 200
    assert response.data["count"] == Permission.objects.count() > 10
    assert len(response.data["results"]) == 10


def test_page_size_zero_returns_everything(bootstrap_tenant):
    tenant = bootstrap_tenant("perm-list-all")

    response = tenant["client"].get("/api/auth/permissions/", {"page_size": 0})

    assert response.status_code == 200
    assert len(response.data["results"]) == response.data["count"] == Permission.objects.count()


def test_list_filters_by_entitytype_when_explicitly_requested(bootstrap_tenant):
    from django_resaas.saas.models.entity_type_model import EntityTypeModel

    tenant = bootstrap_tenant("perm-list-filtered")
    entity_type_id = tenant["entity"].entity_type_id

    content_type = ContentType.objects.get_for_model(Permission)
    EntityTypeModel.objects.create(
        entity_type_id=entity_type_id, model=content_type
    )

    response = tenant["client"].get(
        "/api/auth/permissions/", {"entitytype": entity_type_id, "page_size": 0}
    )

    assert response.status_code == 200
    assert response.data["results"]
    assert all(
        row["content_type_id"] == content_type.id
        for row in response.data["results"]
    )
