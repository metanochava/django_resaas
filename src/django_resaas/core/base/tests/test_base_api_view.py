"""
Tests the shared BaseAPIView/BaseModel plumbing that every REST resource in
django_resaas and hr goes through - multi-tenant isolation, permission
enforcement, module activation, and hard delete - via `dev.demo.Product`
(already proven to work end-to-end in src/dev/demo/tests/test_flow.py,
which covers list/create/retrieve/update/soft-delete/restore/search).

This file covers what that one doesn't: isolation BETWEEN two different
tenants, the permission-denied path, the module-not-active path, and
hard_delete.
"""
import pytest

from dev.demo.models import Product

pytestmark = pytest.mark.django_db


def _create_product(client, name="Widget", sku="WID-1", price="9.99"):
    response = client.post(
        "/api/demo/products/", {"name": name, "sku": sku, "price": price}
    )
    assert response.status_code == 201, response.data
    return response.data["id"]


def test_tenants_are_isolated_from_each_other(bootstrap_tenant):
    tenant_a = bootstrap_tenant("tenant-a", modules=("demo",))
    tenant_b = bootstrap_tenant("tenant-b", modules=("demo",))

    _create_product(tenant_a["client"], name="A's Widget")

    # tenant B's list must not include tenant A's product
    response = tenant_b["client"].get("/api/demo/products/")
    assert response.data["count"] == 0

    # confirmed at the DB level too: both products exist, scoped to different entities
    assert Product.objects.filter(entity=tenant_a["entity"]).count() == 1
    assert Product.objects.filter(entity=tenant_b["entity"]).count() == 0


def test_request_denied_without_permission(bootstrap_tenant):
    tenant = bootstrap_tenant("no-perms", modules=("demo",))

    # Guest group has no CRUD permissions granted to it (only Root does -
    # see core/signals/permissions.py's create_model_permissions)
    from django_resaas.core.tenant.context import ResaasContextService
    from django_resaas.models.group import Group

    guest_group = Group.objects.get(name="Guest")
    context = ResaasContextService.issue(
        user=tenant["user"],
        entity_id=tenant["entity"].id,
        branch_id=tenant["branch"].id,
        group_id=guest_group.id,
    )
    tenant["client"].credentials(
        HTTP_X_RESAAS_CONTEXT=context["token"], HTTP_L="1"
    )

    response = tenant["client"].get("/api/demo/products/")
    assert response.status_code == 400
    assert response.data["detail"] == "Unauthorized"


def test_request_denied_when_module_not_active(bootstrap_tenant):
    # deliberately no modules=("demo",) - the "demo" module was never
    # activated for this tenant
    tenant = bootstrap_tenant("no-module")

    response = tenant["client"].get("/api/demo/products/")
    assert response.status_code == 403


def test_hard_delete_permanently_removes_the_row(bootstrap_tenant):
    tenant = bootstrap_tenant("hard-delete-tenant", modules=("demo",))
    product_id = _create_product(tenant["client"])

    response = tenant["client"].delete(f"/api/demo/products/{product_id}/")
    assert response.status_code == 204

    response = tenant["client"].delete(
        f"/api/demo/products/{product_id}/hard_delete/"
    )
    assert response.status_code == 200

    # gone even from all_objects (soft-deleted rows would still show up there)
    assert not Product.all_objects.filter(id=product_id).exists()
