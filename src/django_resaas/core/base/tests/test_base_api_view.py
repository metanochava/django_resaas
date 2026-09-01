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


def test_soft_delete_preserves_the_tenant(bootstrap_tenant):
    tenant = bootstrap_tenant("soft-delete-tenant", modules=("demo",))
    product_id = _create_product(tenant["client"])

    response = tenant["client"].delete(f"/api/demo/products/{product_id}/")
    assert response.status_code == 204

    product = Product.all_objects.get(id=product_id)
    assert product.deleted_at is not None
    assert product.entity_id == tenant["entity"].id
    assert product.branch_id == tenant["branch"].id


def test_objects_all_stays_tenant_scoped(bootstrap_tenant):
    tenant_a = bootstrap_tenant("all-scope-tenant-a", modules=("demo",))
    tenant_b = bootstrap_tenant("all-scope-tenant-b", modules=("demo",))

    product_id = _create_product(tenant_a["client"])
    tenant_a["client"].delete(f"/api/demo/products/{product_id}/")

    # tenant B must see nothing, even when asking for "all" objects
    response = tenant_b["client"].get("/api/demo/products/?objects=all")
    assert response.data["count"] == 0

    # tenant A does see its own soft-deleted row via "all"
    response = tenant_a["client"].get("/api/demo/products/?objects=all")
    assert response.data["count"] == 1


def test_objects_deleted_stays_tenant_scoped(bootstrap_tenant):
    tenant_a = bootstrap_tenant("deleted-scope-tenant-a", modules=("demo",))
    tenant_b = bootstrap_tenant("deleted-scope-tenant-b", modules=("demo",))

    product_id = _create_product(tenant_a["client"])
    tenant_a["client"].delete(f"/api/demo/products/{product_id}/")

    # tenant B must not see tenant A's soft-deleted row
    response = tenant_b["client"].get("/api/demo/products/?objects=deleted")
    assert response.data["count"] == 0

    # tenant A does see its own soft-deleted row
    response = tenant_a["client"].get("/api/demo/products/?objects=deleted")
    assert response.data["count"] == 1


def test_branch_isolation_within_the_same_entity(bootstrap_tenant):
    """
    Two branches under the SAME entity - not just two different entities -
    must not see each other's data either. Grants the same user access to
    a second branch (mirroring what onboarding a user into a new branch
    actually does) and issues a second signed context for it.
    """
    from django_resaas.core.tenant.context import ResaasContextService
    from django_resaas.models.branch import Branch
    from django_resaas.models.branch_user_group import BranchUserGroup
    from rest_framework.test import APIClient

    tenant = bootstrap_tenant("branch-isolation-tenant", modules=("demo",))

    branch_b = Branch.objects.create(name="Branch B", entity=tenant["entity"])
    BranchUserGroup.objects.get_or_create(
        user=tenant["user"],
        branch=branch_b,
        group=tenant["root_group"],
        defaults={"state": 1},
    )

    _create_product(tenant["client"], name="Branch A's Widget")

    context_b = ResaasContextService.issue(
        user=tenant["user"],
        entity_id=tenant["entity"].id,
        branch_id=branch_b.id,
        group_id=tenant["root_group"].id,
    )
    client_b = APIClient()
    client_b.force_authenticate(user=tenant["user"])
    client_b.credentials(HTTP_X_RESAAS_CONTEXT=context_b["token"], HTTP_L="1")

    response = client_b.get("/api/demo/products/")
    assert response.data["count"] == 0

    assert Product.objects.filter(branch=tenant["branch"]).count() == 1
    assert Product.objects.filter(branch=branch_b).count() == 0


def test_restore_is_blocked_across_tenants(bootstrap_tenant):
    tenant_a = bootstrap_tenant("restore-tenant-a", modules=("demo",))
    tenant_b = bootstrap_tenant("restore-tenant-b", modules=("demo",))

    product_id = _create_product(tenant_a["client"])
    tenant_a["client"].delete(f"/api/demo/products/{product_id}/")

    response = tenant_b["client"].post(
        f"/api/demo/products/{product_id}/restore/"
    )
    assert response.status_code == 404

    # still soft-deleted - tenant B's blocked attempt changed nothing
    assert Product.all_objects.get(id=product_id).deleted_at is not None


def test_restore_works_within_the_same_tenant(bootstrap_tenant):
    tenant = bootstrap_tenant("restore-same-tenant", modules=("demo",))

    product_id = _create_product(tenant["client"])
    tenant["client"].delete(f"/api/demo/products/{product_id}/")

    response = tenant["client"].post(f"/api/demo/products/{product_id}/restore/")
    assert response.status_code == 200

    product = Product.objects.get(id=product_id)  # default manager = alive only
    assert product.deleted_at is None


def test_hard_delete_is_blocked_across_tenants(bootstrap_tenant):
    tenant_a = bootstrap_tenant("hard-delete-cross-tenant-a", modules=("demo",))
    tenant_b = bootstrap_tenant("hard-delete-cross-tenant-b", modules=("demo",))

    product_id = _create_product(tenant_a["client"])
    tenant_a["client"].delete(f"/api/demo/products/{product_id}/")

    response = tenant_b["client"].delete(
        f"/api/demo/products/{product_id}/hard_delete/"
    )
    assert response.status_code == 404

    # untouched - still there (soft-deleted) for tenant A
    assert Product.all_objects.filter(id=product_id).exists()


def test_register_view_and_registerView_are_the_same_decorator():
    """registerView (camelCase) is the original name every existing
    @registerView(...) call site uses; register_view is the PEP 8-consistent
    alias for new code - they must be the exact same object."""
    from django_resaas.core.base.views import register_view, registerView

    assert registerView is register_view
